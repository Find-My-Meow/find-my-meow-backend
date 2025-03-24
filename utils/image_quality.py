from PIL import Image
import numpy as np
import cv2


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
