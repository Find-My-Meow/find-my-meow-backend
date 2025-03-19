import traceback
import uuid
import httpx
import boto3
from fastapi import HTTPException, UploadFile
from core.config import settings


# Initialize S3 client
s3_client = boto3.client(
    service_name='s3',
    region_name=settings.AWS_REGION,
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY
)


def upload_to_s3(file, file_ext):
    """
    Uploads an image to S3 and returns the image URL.
    """
    file_name = f"findmymeow_{uuid.uuid4()}.{file_ext}"

    file.seek(0)
    s3_client.upload_fileobj(file, settings.AWS_S3_BUCKET_NAME, file_name)

    image_path = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{file_name}"
    return image_path, file_name


async def upload_cat_image(cat_image: UploadFile) -> dict:
    """
    Uploads a cat image via the API and returns the uploaded image data.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (cat_image.filename,
                              cat_image.file, cat_image.content_type)}
            response = await client.post(f"{settings.BACKEND_URL}/api/v1/image/", files=files)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500, detail="Failed to upload image")

        return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail="Image upload error")


async def delete_image_service(image_id: str):
    """
    Deletes an image using the DELETE API endpoint.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{settings.BACKEND_URL}/api/v1/image/{image_id}")

        if response.status_code == 200:
            print(
                f"Successfully deleted image {image_id} from S3 & database.")
        else:
            print(
                f"Failed to delete image {image_id}. API Response: {response.text}")

    except Exception as rollback_error:
        error_message = traceback.format_exc()
        print(f"Rollback failed: {rollback_error}")
        print(f"Error Traceback:\n{error_message}")
