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
from utils.search_utils import find_similar_posts_by_post_id


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
    # For CLIP, raw IP score (0–1), e.g. 0.2
    # IndexFlatIP (for CLIP), which returns cosine similarity values in the range [0, 1]
    similarity_threshold: float = Form(0.75)
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
            # crop cat in query image
            cat_crops = crop_cats(image, detections)
            # Extracting cat features
            cat_features = extract_cat_features(cat_crops)
            cat_features_np = np.array(cat_features, dtype=np.float32)
            # Normalize each vector for cosine similarity
            cat_features_np = cat_features_np / \
                np.linalg.norm(cat_features_np, axis=1, keepdims=True)

            # debug
            print("Search vector norm:", np.linalg.norm(cat_features_np[0]))
            print("Current FAISS index total vectors:", faiss_index.ntotal)

            distances, faiss_ids = faiss_index.search(cat_features_np, top_k)
            print("\n🔎 FAISS Search Results:")
            # Each cat crop (multiple cats in one image)
            for i in range(cat_features_np.shape[0]):
                print(f"  Crop {i+1}/{cat_features_np.shape[0]}")
                # loop each FAISS match for this crop
                for j, faiss_id in enumerate(faiss_ids[i]):
                    # return -1: missing results -> skip
                    if faiss_id == -1:
                        continue
                    # cosine similarity: 0-1 (1 = perfect match)
                    distance = float(distances[i][j])
                    # get image id from faiss id: faiss_id = 6400 -> image_id = 64
                    image_id = str(faiss_id // 100)
                    print(
                        f"FAISS ID: {faiss_id}, Mapped image_id: {image_id}, Distance: {distance:.4f}")

                    if distance < similarity_threshold:
                        print("      ✖️ Skipped (below threshold)")
                        continue

                    # Store only best match per image_id
                    # Add new image id / replace existing distance if current vector is more similar
                    if image_id not in matched_image_ids or distance > matched_image_ids[image_id]:
                        matched_image_ids[image_id] = distance
                        print("      ✅ Added/Updated in matched_image_ids")
                    else:
                        print("      🔁 Already matched with better distance")

        # Primary query — filter by status and image_ids if provided
        query = {"status": "active"}
        if matched_image_ids:
            query["cat_image.image_id"] = {"$in": list(matched_image_ids)}

        posts_cursor = db.database["posts_v2"].find(query)
        all_posts = [Post(**post) async for post in posts_cursor]

        # Location filtering based on geographic distance
        filtered_posts = []
        if latitude is not None and longitude is not None:
            search_coords = (latitude, longitude)
            for post in all_posts:
                if post.location and hasattr(post.location, "latitude") and hasattr(post.location, "longitude"):
                    post_coords = (post.location.latitude,
                                   post.location.longitude)
                    # calculate geodesic (real-world) distance in km between the post and the search location
                    distance_km = geodesic(post_coords, search_coords).km
                    # filter only post within the radius
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
                post_data["faiss_similarity"] = round(similarity, 4)
                post_data["similarity_percent"] = round(similarity * 100, 1)
            enriched_posts.append(post_data)

        if matched_image_ids:
            enriched_posts.sort(key=lambda x: x.get(
                "faiss_similarity", 0), reverse=True)

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


# for test find_similar_posts_by_post_id(post_id)
@search_router.get("/match/{post_id}")
async def match_similar(post_id: str):
    results, _ = await find_similar_posts_by_post_id(post_id)
    return {"count": len(results), "results": results}
