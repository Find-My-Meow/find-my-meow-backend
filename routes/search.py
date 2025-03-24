from typing import Dict, Optional
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
import numpy as np
from core.database import db
from PIL import Image as PILImage
from models.post import Post
from utils.cat_detection import crop_cats, detect_cats, extract_cat_features
from utils.faiss_utils import load_faiss_index
from geopy.distance import geodesic
from utils.image_utils import is_blurry, is_too_small


search_router = APIRouter()
faiss_index = load_faiss_index()


def refresh_faiss_index():
    global faiss_index
    faiss_index = load_faiss_index()


@search_router.post("/search", response_model=dict)
async def search_posts(
    file: Optional[UploadFile] = File(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    radius_km: int = Form(1),
    top_k: int = Form(100),
    similarity_threshold: float = Form(200.0)
):
    """
    Searches for posts based on an uploaded cat image, location, or both.
    - If an image is uploaded, it performs FAISS similarity search.
    - If a location is provided, it filters posts by latitude and longitude within the given radius.
    - If both image and location are provided, it applies both filter.
    """
    try:
        if not file and not any([latitude, longitude]):
            raise HTTPException(
                status_code=400,
                detail="Please provide at least one search parameter (image or location)."
            )

        print(f"Number of stored vectors: {faiss_index.ntotal}")

        matched_image_ids: Dict[str, float] = {}
        code = "NO_MATCH"
        message = "No matching posts found."
        image_is_blurry = False

        # Image-based FAISS search
        if file:
            image = PILImage.open(file.file).convert("RGB")

            # Resolution check
            if is_too_small(image):
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Low quality image: Image is too small."}
                )

            # Blur check
            image_is_blurry = is_blurry(image, threshold=100.0)

            detections = detect_cats(image)
            if len(detections) == 0:
                raise HTTPException(
                    status_code=400, detail="No cat detected in image.")

            cat_crops = crop_cats(image, detections)
            cat_features = extract_cat_features(cat_crops)
            features_np = np.array(cat_features, dtype=np.float32).squeeze()
            if len(features_np.shape) == 1:
                features_np = np.expand_dims(features_np, axis=0)

            distances, faiss_ids = faiss_index.search(features_np, top_k)
            for i, faiss_id_list in enumerate(faiss_ids):
                for j, faiss_id in enumerate(faiss_id_list):
                    if faiss_id == -1:
                        continue
                    # Euclidean distance: Lower is better
                    distance = float(distances[i][j])
                    if distance > similarity_threshold:
                        continue

                    image_id = str(faiss_id // 100)
                    print(
                        f"[DEBUG] Matched FAISS ID: {faiss_id}, base image_id: {image_id}, distance: {distance}")
                    if image_id not in matched_image_ids or distance < matched_image_ids[image_id]:
                        matched_image_ids[image_id] = distance

        # Primary query — filter by status and image_ids if provided
        query = {"status": "active"}
        if matched_image_ids:
            query["cat_image.image_id"] = {"$in": list(matched_image_ids)}

        posts_cursor = db.database["posts_v2"].find(query)
        all_posts = [Post(**post) async for post in posts_cursor]

        # Location filtering
        filtered_posts = []
        if latitude is not None and longitude is not None:
            search_coords = (latitude, longitude)
            for post in all_posts:
                if post.location and hasattr(post.location, "latitude") and hasattr(post.location, "longitude"):
                    post_coords = (post.location.latitude,
                                   post.location.longitude)
                    distance_km = geodesic(post_coords, search_coords).km
                    if distance_km <= radius_km:
                        filtered_posts.append(post)
        else:
            filtered_posts = all_posts

        # Set response code/message
        if filtered_posts:
            if file and latitude is not None and longitude is not None:
                code = "IMAGE_LOCATION"
                message = "Found results using both image and location."
            elif file:
                code = "IMAGE_ONLY"
                message = "Found results using image only."
            else:
                code = "LOCATION_ONLY"
                message = "Found results using location only."

        # Attach similarity scores and sort
        enriched_posts = []
        for post in filtered_posts:
            post_data = post.model_dump()
            image_id = post.cat_image.image_id
            similarity = matched_image_ids.get(image_id)
            if similarity is not None:
                # Convert FAISS L2 distance to similarity score (0–100%)
                max_possible_distance = 200.0  # adjust based on model scale
                similarity_score = max(
                    0.0, 1.0 - (similarity / max_possible_distance))
                post_data["faiss_distance"] = similarity
                post_data["similarity_percent"] = round(
                    similarity_score * 100, 1)  # e.g. 87.5%
            enriched_posts.append(post_data)

        if matched_image_ids:
            enriched_posts.sort(key=lambda x: x.get(
                "similarity_percent", 0), reverse=True)

        return {
            "code": code,
            "message": message,
            "results": enriched_posts,
            "count": len(enriched_posts),
            "image_blur_warning": bool(image_is_blurry),
        }

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")
