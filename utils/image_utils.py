from io import BytesIO
from fastapi import UploadFile, HTTPException
from PIL import Image, UnidentifiedImageError
from uuid import uuid4
from PIL import Image
import numpy as np
import cv2

# HEIC support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


def is_too_small(image: Image.Image, min_width: int = 200, min_height: int = 200) -> bool:
    """
    Checks if image dimensions are below the minimum threshold (too small).
    """
    width, height = image.size
    return width < min_width or height < min_height


def is_blurry(image: Image.Image, threshold: float = 100.0) -> bool:
    """
    Uses Laplacian variance to check for image blurriness.
    """
    # Convert to grayscale
    image_gray = image.convert("L")
    img_np = np.array(image_gray)
    laplacian_var = cv2.Laplacian(img_np, cv2.CV_64F).var()
    # print("Laplacian Variance:", laplacian_var)
    return laplacian_var < threshold


def sanitize_image(upload_file: UploadFile, allowed_formats=("jpg", "jpeg", "png", "heic", "webp")) -> BytesIO:
    """
    Validates and sanitizes an uploaded image.
    Converts to RGB and re-encodes to clean JPEG.
    Returns a BytesIO buffer of the sanitized image.
    """
    try:
        # Validate extension
        file_ext = upload_file.filename.split(".")[-1].lower()
        if file_ext not in allowed_formats:
            raise HTTPException(
                status_code=400, detail="Unsupported file format")

        # Load and convert to RGB to remove metadata and alpha channels
        image = Image.open(upload_file.file).convert("RGB")

        # Re-encode to JPEG in memory
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)

        return buffer

    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400, detail="Invalid or unsupported image format.")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Image sanitization failed: {str(e)}")
