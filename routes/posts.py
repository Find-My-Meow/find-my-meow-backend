import datetime
import json
import os
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from database import db
from bson import ObjectId
from typing import List, Optional

from models.post import Post, UpdatePost

post_router = APIRouter()

os.makedirs("images", exist_ok=True)

@post_router.post("/")
async def create_post(
    user_id: str = Form(...),
    cat_name: Optional[str] = Form(None),
    gender: str = Form(...),
    color: str = Form(...),
    breed: str = Form(...),
    cat_marking: str = Form(...),
    location: str = Form(...),
    lost_date: str = Form(...),
    other_information: Optional[str] = Form(None),
    email_notification: bool = Form(...),
    post_type: str = Form(...),
    cat_image: UploadFile = File(...)
):
    try:
        location_data = json.loads(location)

        post_dict = {
            "user_id": user_id,
            "cat_name": cat_name,
            "gender": gender,
            "color": color,
            "breed": breed,
            "cat_marking": cat_marking,
            "location": location_data,
            "lost_date": lost_date,
            "other_information": other_information,
            "email_notification": email_notification,
            "post_type": post_type,
            "cat_image_filename": cat_image.filename,
        }

        print("Received Data:", post_dict)  # Debugging
        print(f"DB Type: {type(db)}")

        # Directly use db["posts"]
        result = await db.database["posts"].insert_one(post_dict)

        print("Inserted ID:", result.inserted_id)  # Debugging

        return {"message": "Post created successfully", "post_id": str(result.inserted_id)}

    except Exception as e:
        print("Error:", str(e))
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


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
