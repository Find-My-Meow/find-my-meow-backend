import torch
from ultralytics import YOLO
import numpy as np
from utils.utils import get_device
from transformers import CLIPProcessor, CLIPModel


_device = get_device()

# Lazy singletons
_yolo = None
_clip = None
_processor = None

# Load YOLOv8 model
def get_yolo():
    global _yolo
    if _yolo is None:
        _yolo = YOLO("yolov8n.pt").to(_device)
    return _yolo

# Load CLIP ViT model
def get_clip():
    global _clip, _processor
    if _clip is None:
        _processor = CLIPProcessor.from_pretrained(
            "openai/clip-vit-base-patch32")
        _clip = CLIPModel.from_pretrained(
            "openai/clip-vit-base-patch32").to(_device)
    return _processor, _clip


def detect_cats(image):
    """Detects multiple cats in an image and returns bounding boxes."""
    yolo = get_yolo()
    results = yolo(image, classes=[15])  # Class 15 = Cat in COCO dataset
    detections = results[0].boxes.xyxy.cpu().numpy()  # Extract bounding boxes
    return detections


def crop_cats(image, detections, padding=15):
    """
    Crops detected cats and returns sorted PIL images (largest to smallest).
    Sorting helps maintain consistency across indexing and search.
    """
    width, height = image.size
    crops_with_area = []

    for box in detections:
        x1, y1, x2, y2 = map(int, box[:4])
        # Add padding and clamp
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(width, x2 + padding)
        y2 = min(height, y2 + padding)

        area = (x2 - x1) * (y2 - y1)
        crop = image.crop((x1, y1, x2, y2))
        crops_with_area.append((area, crop))

    # Sort by area (largest first)
    crops_with_area.sort(key=lambda x: x[0], reverse=True)

    # Return only the cropped images
    return [crop for _, crop in crops_with_area]


def extract_cat_features(images):
    """Extracts features from cropped cat images using CLIP ViT."""
    processor, clip = get_clip()
    features = []

    for img in images:
        # Preprocess image
        inputs = processor(images=img, text=[
                           "a photo of a cat"], return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(
            get_device())  # Only image part

        # Extract feature embeddings
        with torch.no_grad():
            embeddings = clip.get_image_features(pixel_values)  # CLIP-specific
        features.append(embeddings.cpu().numpy())

    return np.squeeze(np.array(features), axis=1)
