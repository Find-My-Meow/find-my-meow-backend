from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import numpy as np
from core.database import db
from PIL import Image as PILImage
from utils.cat_detection import crop_cats, detect_cats, extract_cat_features
from utils.faiss_utils import load_faiss_index

search_router = APIRouter()

# Load FAISS index
search_router.faiss_index = load_faiss_index()


@search_router.post("/search", response_model=dict)
async def search_posts(
    file: Optional[UploadFile] = File(None),
    province: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    sub_district: Optional[str] = Form(None),
    top_k: int = 100
):
    """
    Searches for posts based on an uploaded cat image, location, or both.
    - If an image is uploaded, it performs FAISS similarity search.
    - If a location is provided, it filters posts by province, district, or sub-district.
    - If both image and location are provided, it applies both filters first.
    """
    try:
        if file and file.filename == "":
            file = None
        
        if not file and not any([province, district, sub_district]):
            raise HTTPException(
                status_code=400, detail="Please provide at least one search parameter (image or location).")

        # Ensure FAISS Index is Loaded
        faiss_index = search_router.faiss_index
        if faiss_index is None or faiss_index.ntotal == 0:
            faiss_index = load_faiss_index()  # Reload FAISS from S3
            search_router.faiss_index = faiss_index

        # database query for location
        query = {}
        if province:
            query["location.province"] = province
        if district:
            query["location.district"] = district
        if sub_district:
            query["location.sub_district"] = sub_district

        # If Image is provided do FAISS Search
        matching_image_ids = []
        search_by = "location" if query else None

        if file:
            search_by = "image" if not query else "image and location"

            file.file.seek(0)
            image = PILImage.open(file.file)

            # Detect cats
            detections = detect_cats(image)
            if len(detections) == 0:
                raise HTTPException(
                    status_code=400, detail="No cat detected in the uploaded image.")

            # Crop cats
            cat_crops = crop_cats(image, detections)

            # Extract features
            cat_features = extract_cat_features(cat_crops)

            # Convert to NumPy array
            cat_features_np = np.array(
                cat_features, dtype=np.float32).squeeze()
            if len(cat_features_np.shape) == 1:
                cat_features_np = np.expand_dims(cat_features_np, axis=0)

            # Search in FAISS (if not empty)
            if faiss_index and faiss_index.ntotal > 0:
                distances, indices = faiss_index.search(
                    cat_features_np, top_k * 3)
                matching_image_ids = [str(idx)
                                      for idx in indices[0] if idx >= 0]
                print(
                    f"Found {len(matching_image_ids)} similar images in FAISS")
            else:
                print("FAISS Index is empty. Skipping image search.")

        # Search Image and Location
        if matching_image_ids:
            query["cat_image.image_id"] = {"$in": matching_image_ids}

        posts = await db.database["posts_v2"].find(query).to_list(100)

        # If No Results Found, Try Image-Only Search
        if not posts and matching_image_ids:
            # print("No posts found with image & location. Trying image-only search.")
            search_by = "image"
            # Search only by image
            query = {"cat_image.image_id": {"$in": matching_image_ids}}
            posts = await db.database["posts_v2"].find(query).to_list(100)
            message = "No similar cat found at this location. Showing results based on image only."
        else:
            message = f"Search by {search_by}"

        # No Posts found
        if not posts:
            raise HTTPException(status_code=404, detail="No posts found.")

        for post in posts:
            post["_id"] = str(post["_id"])

        print(f"Returning {len(posts)} posts")
        return {
            "message": message,  # search type
            "posts": posts[:top_k]  # Limit results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")
