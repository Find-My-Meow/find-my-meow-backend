import traceback
import bson
from fastapi import APIRouter, File, HTTPException, UploadFile
import numpy as np
from core.database import db
from bson import Binary, ObjectId
import faiss
from PIL import Image as PILImage
from models.image import Image
from services.image_service import upload_to_s3, s3_client
from utils.cat_detection import crop_cats, detect_cats, extract_cat_features
from utils.utils import get_next_image_id, load_faiss_index
from core.config import settings


image_router = APIRouter()

faiss_index, FAISS_INDEX_FILE = load_faiss_index()


@image_router.post("/")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image to S3, database, and add cat feature to FAISS.
    """
    try:
        # Opening image file
        file_ext = file.filename.split(".")[-1]

        # Reset file pointer before processing
        file.file.seek(0)

        image = PILImage.open(file.file)

        # TODO: Check image quality
        # Detecting cats
        detections = detect_cats(image)
        if len(detections) == 0:
            raise HTTPException(
                status_code=400, detail="No cat detected. Please upload an image with a cat.")
        
        # Cropping cat images
        cat_crops = crop_cats(image, detections)
        # Extracting cat features
        cat_features = extract_cat_features(cat_crops)

        # Converting features to NumPy array
        cat_features_np = np.array(cat_features, dtype=np.float32).squeeze()
        if len(cat_features_np.shape) == 1:
            cat_features_np = np.expand_dims(cat_features_np, axis=0)

        image_id = await get_next_image_id()
        faiss_id = int(image_id)

        # Uploading image to S3
        file.file.seek(0)
        image_path, file_name = upload_to_s3(file.file, file_ext)

        # Insert image data into database
        image_data = {
            "_id": ObjectId(),
            "image_id": image_id,
            "stored_filename": file_name,
            "image_path": image_path,
            "cat_features": Binary(bson.BSON.encode({"features": cat_features_np.tolist()})),
        }

        await db.database["images_v2"].insert_one(image_data)

        # Add feature vector to FAISS
        faiss_index.add_with_ids(
            cat_features_np, np.array([faiss_id], dtype=np.int64))
        faiss.write_index(faiss_index, FAISS_INDEX_FILE)

        return {
            "image_id": image_id,
            "stored_filename": file_name,
            "image_path": image_path,
            "faiss_id": faiss_id
        }

    except Exception as e:
        # debug
        # error_message = traceback.format_exc()
        # print("Error Traceback:\n", error_message)
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")


@image_router.get("/{image_id}")
async def get_image(image_id: str):
    """
    Get an image from database by image_id.
    """
    try:
        # Fetch the image from database
        image_data = await db.database["images_v2"].find_one({"image_id": image_id})

        # If image not found, return error
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")

        return Image(
            image_id=image_data["image_id"],
            stored_filename=image_data["stored_filename"],
            image_path=image_data["image_path"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")


@image_router.delete("/{image_id}")
async def delete_image(image_id: str):
    """
    Deletes an image from S3, database, and FAISS by image_id.
    """
    try:
        # Find the image in database
        image_data = await db.database["images_v2"].find_one({"image_id": image_id})
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")

        # Delete from S3
        stored_filename = image_data["stored_filename"]
        try:
            s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET_NAME, Key=stored_filename)
        except Exception as s3_error:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete from S3: {str(s3_error)}")

        # Remove from FAISS
        try:
            faiss_id = np.array([int(image_id)], dtype=np.int64)

            if faiss_index is not None and faiss_index.ntotal > 0:
                stored_ids = np.array([faiss_index.id_map.at(i) for i in range(
                    faiss_index.id_map.size())], dtype=np.int64)

                if faiss_id[0] in stored_ids:
                    faiss_index.remove_ids(faiss_id)
                    faiss.write_index(faiss_index, FAISS_INDEX_FILE)
                else:
                    print(f"FAISS ID {faiss_id[0]} not found in FAISS index.")
            else:
                print("FAISS index is empty. Skipping FAISS deletion.")

        except Exception as faiss_error:
            raise HTTPException(
                status_code=500, detail=f"Failed to remove FAISS feature: {str(faiss_error)}")

        # Delete the image from database
        await db.database["images_v2"].delete_one({"image_id": image_id})
        return {"message": "Image deleted successfully", "image_id": image_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete image: {str(e)}")
