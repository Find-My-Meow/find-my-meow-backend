import torch
from ultralytics import YOLO
import numpy as np
from transformers import AutoImageProcessor, AutoModel
from utils.utils import get_device


# Load YOLOv8 model
yolo = YOLO("yolov8n.pt").to(get_device())

# Load DINO ViT model
processor = AutoImageProcessor.from_pretrained(
    "facebook/dino-vitb16", use_fast=True)
dino = AutoModel.from_pretrained("facebook/dino-vitb16").to(get_device())


def detect_cats(image):
    """Detects multiple cats in an image and returns bounding boxes."""
    results = yolo(image, classes=[15])  # Class 15 = Cat in COCO dataset
    detections = results[0].boxes.xyxy.cpu().numpy()  # Extract bounding boxes
    return detections


def crop_cats(image, detections):
    """Crops detected cats and returns as PIL images."""
    cat_crops = []
    for box in detections:
        x1, y1, x2, y2 = map(int, box[:4])  # Convert coordinates to integers
        cropped_cat = image.crop((x1, y1, x2, y2))  # Crop the detected cat
        cat_crops.append(cropped_cat)
    return cat_crops


def extract_cat_features(images):
    """Extracts features from cropped cat images using DINO ViT."""
    features = []

    for img in images:
        # Preprocess image
        inputs = processor(img, return_tensors="pt").to(get_device())

        # Extract feature embeddings
        with torch.no_grad():
            outputs = dino(**inputs)

        # Use mean pooling over all tokens (global average pooling)
        embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
        features.append(embedding)

    return np.array(features)
