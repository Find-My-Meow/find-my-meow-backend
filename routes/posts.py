import datetime
import json
import os
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from database import db
from bson import ObjectId
from typing import List, Optional
from models.post import Post


post_router = APIRouter()

# Create new post
@post_router.post("/", response_model=Post)
async def create_post(post: Post):
    post_dict = post.model_dump()

    # Generate a unique ObjectId and set as post_id
    post_id = ObjectId()
    post_dict["_id"] = post_id
    post_dict["post_id"] = str(post_id)  # Store as string for response

    # generate image_id
    if not post_dict["cat_image"].get("image_id"):
        post_dict["cat_image"]["image_id"] = str(ObjectId())

    # Insert into database
    result = await db.database["posts"].insert_one(post_dict)

    if result.inserted_id:
        # Retrieve the inserted document and return it
        created_post = await db.database["posts"].find_one({"_id": result.inserted_id})
        created_post["_id"] = str(created_post["_id"])
        return created_post

    raise HTTPException(status_code=500, detail="Failed to create post")

# Get all posts, filter by post_type
@post_router.get("/", response_model=List[Post])
async def list_posts(post_type: Optional[str] = None):
    query = {}
    if post_type:
        query["post_type"] = post_type

    posts = await db.database["posts"].find(query).to_list(length=100)

    for post in posts:
        post["_id"] = str(post["_id"])

    return posts

# Get post by ID
@post_router.get("/{post_id}", response_model=Post)
async def get_post(post_id: str):
    try:
        post = await db.database["posts"].find_one({"_id": ObjectId(post_id)})
    except:
        raise HTTPException(
            status_code=400, detail="Invalid post ID format")  # invalid ID

    if post:
        post["_id"] = str(post["_id"])
        return post

    raise HTTPException(status_code=404, detail="Post not found")

# Update post by ID
@post_router.put("/{post_id}", response_model=Post)
async def edit_post(post_id: str, post_data: Post):
    try:
        post_object_id = ObjectId(post_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid post ID")

    # Convert the update model to a dictionary and remove `None` values
    update_data = {k: v for k, v in post_data.model_dump().items()
                   if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=400, detail="No data provided to update the post.")

    result = await db.database["posts"].update_one({"_id": post_object_id}, {"$set": update_data})

    if result.modified_count == 1:
        # Retrieve the updated post
        updated_post = await db.database["posts"].find_one({"_id": post_object_id})
        updated_post["_id"] = str(updated_post["_id"])
        return updated_post

    raise HTTPException(
        status_code=404, detail="Post not found or no changes made.")

# Delete post by ID
@post_router.delete("/{post_id}", response_model=dict)
async def delete_post(post_id: str):
    try:
        post_object_id = ObjectId(post_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid post ID format")

    result = await db.database["posts"].delete_one({"_id": post_object_id})
    if result.deleted_count == 1:
        return {"message": "Post deleted successfully"}

    raise HTTPException(status_code=404, detail="Post not found")
