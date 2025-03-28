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
    # [0, 1]: 0 less similar -> 1 most similar
    similarity_threshold: float = 0.75,
) -> Tuple[List[Dict], bool]:
    """
    Given a post ID, find other posts that:
    - Are a different post type (lost -> found/adoption, found -> lost)
    - Have similar cat features (search by image)
    - Are within the same location radius (default 1km)
    - Return default top 5 most similar posts
    """
    # Find post
    # print(f"Finding similar posts for post_id={post_id}...")

    query_post = await db.database["posts_v2"].find_one({"post_id": post_id, "status": "active"})

    if not query_post:
        return [], False

    # print(f"Post {post_id}: ", query_post)

    # Get post type
    query_post_type = query_post.get("post_type")
    if query_post_type not in ["lost", "found"]:
        return [], False

    if query_post_type == "lost":
        target_post_types = ["found", "adoption"]
    else:  # "found"
        target_post_types = ["lost"]

    # Get location
    query_location = query_post.get("location")
    if not query_location or "latitude" not in query_location or "longitude" not in query_location:
        return [], False

    search_coords = (query_location["latitude"], query_location["longitude"])

    # Get image
    query_image_info = query_post.get("cat_image")
    if not query_image_info or not query_image_info.get("image_id"):
        return [], False

    # Fetch full image data from images_v2
    query_image = await db.database["images_v2"].find_one({"image_id": query_image_info["image_id"]})
    if not query_image or "cat_features" not in query_image or "faiss_ids" not in query_image:
        return [], False

    # Find similar cat
    # Decode the stored cat features
    try:
        raw_features_doc = bson.BSON(query_image["cat_features"]).decode()
        cat_features_np = np.array(
            # np array (N, D): N: num cat crops, D: feature dimension (512)
            raw_features_doc["features"], dtype=np.float32).squeeze()
        if len(cat_features_np.shape) == 1:
            cat_features_np = np.expand_dims(cat_features_np, axis=0)
    except Exception:
        raise RuntimeError("Failed to decode stored features")

    # Run FAISS search
    distances, faiss_ids = faiss_index.search(cat_features_np, k=100)

    # find best similarity match per image
    matched_image_ids: Dict[str, float] = {}
    source_image_id = query_image["image_id"]
    # Loop through each cat crop (query vector)
    for i, faiss_id_list in enumerate(faiss_ids):
        # Loop through each of the top 100 matches for that crop
        for j, faiss_id in enumerate(faiss_id_list):
            # skip if not return valid match
            if faiss_id == -1:
                continue
            # cosine similarity distance: (0-1)
            distance = float(distances[i][j])
            # skip if below threshold
            if distance < similarity_threshold:
                continue
            image_id = str(faiss_id // 100)
            # print(f"  • FAISS ID: {faiss_id}, Image ID: {image_id}, Similarity: {distance:.4f}")
            if image_id == str(source_image_id):
                # print("    🔁 Skipping self-match")
                continue  # Skip matching with itself
            # keep only the best similarity score for each image_id
            if image_id not in matched_image_ids or distance > matched_image_ids[image_id]:
                matched_image_ids[image_id] = distance
                # print("    ✅ Added/Updated matched_image_ids")

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

    # print(f"Found {len(all_posts)} posts by image ID and type")

    # Filter by location
    filtered_posts = []
    for query_post in all_posts:
        if query_post.location and hasattr(query_post.location, "latitude") and hasattr(query_post.location, "longitude"):
            post_coords = (query_post.location.latitude,
                           query_post.location.longitude)
            distance_km = geodesic(post_coords, search_coords).km
            if distance_km <= radius_km:
                filtered_posts.append(query_post)

    # print(f"{len(filtered_posts)} posts passed location filtering.")

    # Add similarity score
    enriched_posts = []
    for query_post in filtered_posts:
        post_data = query_post.model_dump()
        match_id = query_post.cat_image.image_id
        similarity = matched_image_ids.get(match_id)
        if similarity is not None:
            post_data["faiss_similarity"] = round(similarity, 4)
            post_data["similarity_percent"] = round(similarity * 100, 1)
        enriched_posts.append(post_data)

    enriched_posts.sort(key=lambda x: x.get(
        "faiss_similarity", 0), reverse=True)
    return enriched_posts[:num_results], False
