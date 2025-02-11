from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from database import db
from models.post import Post

search_router = APIRouter()

# Search posts by location
@search_router.get("/location", response_model=List[Post])
async def search_posts(
    province: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    sub_district: Optional[str] = Query(None),
):
    query = {}

    if province:
        query["location.province"] = province
    if district:
        query["location.district"] = district
    if sub_district:
        query["location.sub_district"] = sub_district

    # Limit to 100 results
    posts = await db.database["posts"].find(query).to_list(100)
    if not posts:
        raise HTTPException(
            status_code=404, detail="No posts found matching the location")

    # Convert ObjectId to string
    for post in posts:
        post["_id"] = str(post["_id"])

    return posts
