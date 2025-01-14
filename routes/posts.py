from fastapi import APIRouter, HTTPException
from database import db
from bson import ObjectId
from typing import List, Optional

from models.post import Post, UpdatePost

post_router = APIRouter()

# Create new post
@post_router.post("/", response_model=Post)
async def create_post(post: Post):
    post_dict = post.model_dump()
    post_dict["_id"] = str(ObjectId())  # Add unique ID
    result = await db.database["posts"].insert_one(post_dict)
    if result.inserted_id:
        return post
    raise HTTPException(status_code=500, detail="Failed to create post")

# Get all posts, can filter by post_type
@post_router.get("/", response_model=List[Post])
async def list_posts(post_type: Optional[str] = None):
    query = {}
    if post_type:
        query["post_type"] = post_type
    posts = await db.database["posts"].find(query).to_list(length=100)
    return posts

# Get post by ID
@post_router.get("/{post_id}", response_model=Post)
async def get_post(post_id: str):
    post = await db.database["posts"].find_one({"_id": post_id})
    if post:
        return post
    raise HTTPException(status_code=404, detail="Post not found")

# Update post by ID
@post_router.put("/{post_id}", response_model=Post)
async def edit_post(post_id: str, post_data: UpdatePost):
    # Convert the update model to a dictionary and remove `None` values
    update_data = {k: v for k, v in post_data.model_dump().items()
                   if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=400, detail="No data provided to update the post.")

    result = await db.database["posts"].update_one({"_id": post_id}, {"$set": update_data})
    if result.modified_count == 1:
        updated_post = await db.database["posts"].find_one({"_id": post_id})
        return updated_post
    raise HTTPException(
        status_code=404, detail="Post not found or no changes made.")

# Delete post by ID
@post_router.delete("/{post_id}", response_model=dict)
async def delete_post(post_id: str):
    result = await db.database["posts"].delete_one({"_id": post_id})
    if result.deleted_count == 1:
        return {"message": "Post deleted successfully"}
    raise HTTPException(status_code=404, detail="Post not found")
