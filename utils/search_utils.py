from typing import Dict, List, Tuple
import bson
import numpy as np
from core.database import db
from models.post import Post
from geopy.distance import geodesic

from utils.faiss_utils import load_faiss_index

faiss_index = load_faiss_index()


async def find_similar_posts_by_post_id(
    post_id: str,
    radius_km: int = 1,
    num_results: int = 5,
    similarity_threshold: float = 200.0, # small = more similar, large = less similar
) -> Tuple[List[Dict], bool]:
    """
    Given a post ID, find other posts that:
    - Are a different post type (lost -> found/adoption, found -> lost)
    - Have similar cat features (search by image)
    - Are within the same location radius (default 1km)
    - Return default top 5 most similar posts
    """
    # Find post
    post = await db.database["posts_v2"].find_one({
        "post_id": post_id,
        "status": "active"
    })

    if not post:
        return [], False

    print(f"Post {post_id}: ", post)

    # Get post type
    source_post_type = post.get("post_type")
    if source_post_type not in ["lost", "found"]:
        return [], False

    if source_post_type == "lost":
        target_post_types = ["found", "adoption"]
    else:  # "found"
        target_post_types = ["lost"]

    # Get location
    location = post.get("location")
    if not location or "latitude" not in location or "longitude" not in location:
        return [], False

    search_coords = (location["latitude"], location["longitude"])

    # Get image
    image_info = post.get("cat_image")
    if not image_info or not image_info.get("image_id"):
        return [], False
    
    # Fetch full image data from images_v2
    image = await db.database["images_v2"].find_one({"image_id": image_info["image_id"]})
    if not image or "cat_features" not in image or "faiss_ids" not in image:
        return [], False

    source_image_id = image["image_id"]

    # Find similar cat
    # Decode the stored cat features
    try:
        raw_features_doc = bson.BSON(image["cat_features"]).decode()
        features_np = np.array(
            raw_features_doc["features"], dtype=np.float32).squeeze()
        if len(features_np.shape) == 1:
            features_np = np.expand_dims(features_np, axis=0)
    except Exception:
        raise RuntimeError("Failed to decode stored features")

    # Run FAISS search
    distances, faiss_ids = faiss_index.search(features_np, k=100)

    # Matched image_id → best distance map
    matched_image_ids: Dict[str, float] = {}
    source_image_id = image["image_id"]
    for i, faiss_id_list in enumerate(faiss_ids):
        for j, faiss_id in enumerate(faiss_id_list):
            if faiss_id == -1:
                continue
            distance = float(distances[i][j])
            if distance > similarity_threshold:
                continue
            image_id = str(faiss_id // 100)
            
            if image_id == str(source_image_id):
                continue  # Skip matching with itself

            if image_id not in matched_image_ids or distance < matched_image_ids[image_id]:
                matched_image_ids[image_id] = distance

    if not matched_image_ids:
        return [], False

    # Query all candidate posts (cross post-type with matched image_id)
    query = {
        "status": "active",
        "post_type": {"$in": target_post_types},
        "cat_image.image_id": {"$in": list(matched_image_ids)}
    }

    posts_cursor = db.database["posts_v2"].find(query)
    all_posts = [Post(**p) async for p in posts_cursor]

    # Filter by location
    filtered_posts = []
    for post in all_posts:
        if post.location and hasattr(post.location, "latitude") and hasattr(post.location, "longitude"):
            post_coords = (post.location.latitude, post.location.longitude)
            distance_km = geodesic(post_coords, search_coords).km
            if distance_km <= radius_km:
                filtered_posts.append(post)

    # Add similarity score
    enriched_posts = []
    for post in filtered_posts:
        post_data = post.model_dump()
        match_id = post.cat_image.image_id
        similarity = matched_image_ids.get(match_id)
        if similarity is not None:
            similarity_score = max(
                0.0, 1.0 - (similarity / similarity_threshold))
            post_data["faiss_distance"] = similarity
            post_data["similarity_percent"] = round(similarity_score * 100, 1)
        enriched_posts.append(post_data)

    enriched_posts.sort(key=lambda x: x.get(
        "similarity_percent", 0), reverse=True)
    return enriched_posts[:num_results], False
