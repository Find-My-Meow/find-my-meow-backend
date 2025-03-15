import base64
import json
import os
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse
from database import db
from bson import ObjectId
from typing import List, Optional
from models.post import Post


post_router = APIRouter()
@post_router.post("/", response_model=Post)
async def create_post(
    user_id: str = Form(...),
    cat_name: str = Form(None),
    gender: str = Form(...),
    color: str = Form(...),
    breed: str = Form(...),
    cat_marking: str = Form(None),
    location: str = Form(...), 
    lost_date: str = Form(None),
    other_information: str = Form(None),
    email_notification: bool = Form(...),
    post_type: str = Form(...),
    cat_image: str = Form(...) 
):
    post_id = ObjectId()
    image_id = str(ObjectId())  

    try:
        location_data = json.loads(location)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid location format")

    post_dict = {
        "post_id": str(post_id),
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
        "cat_image": {  
            "image_id": image_id,
            "image_path": f"{cat_image}"  
        },
    }

    # Insert into MongoDB
    result = await db.database["posts"].insert_one(post_dict)

    if result.inserted_id:
        return post_dict 

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
        post = await db.database["posts"].find_one({"post_id": str(post_id)})
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
    post = await db.database["posts"].find_one({"post_id": post_id})

    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")
    
    # Convert the update model to a dictionary and remove None values
    update_data = {k: v for k, v in post_data.model_dump().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update the post.")
    
    # Perform the update operation
    result = await db.database["posts"].update_one({"post_id": post_id}, {"$set": update_data})

    # If no post is modified, raise an error
    if result.matched_count == 1:
        # Retrieve the updated post from the database
        updated_post = await db.database["posts"].find_one({"post_id": post_id})
        updated_post["_id"] = str(updated_post["_id"])  # Convert ObjectId to string for the response
        return updated_post

    raise HTTPException(status_code=400, detail="Failed to update the post.")


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

@post_router.post("/upload_image", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    image_id = str(ObjectId())  # Generate a unique image ID
    image_filename = file.filename

    file_content = await file.read()
    base64_encoded = base64.b64encode(file_content).decode("utf-8")

    image_doc = {
        "_id": image_id,
        "filename": image_filename, 
        "image_data": base64_encoded, 
    }

    await db.database["images"].insert_one(image_doc)

    return {"filename": image_filename}



@post_router.get("/image/{filename}")
async def get_image_by_filename(filename: str):
    image = await db.database["images"].find_one({"filename": filename})

    if not image:
        return JSONResponse(content={"error": "Image not found"}, status_code=404)

    base64_data = image.get("image_data")
    if base64_data:
        try:
            image_bytes = base64.b64decode(base64_data)
            return Response(content=image_bytes, media_type="image/jpeg")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error decoding image: {e}")

    return JSONResponse(content={"error": "No image data found"}, status_code=404)

@post_router.put("/upload_image/{filename}", response_model=dict)
async def update_image(filename: str, file: UploadFile = File(...)):
    image_doc = await db.database["images"].find_one({"filename": filename})
    
    if not image_doc:
        raise HTTPException(status_code=404, detail="Image not found.")

    file_content = await file.read()
    base64_encoded = base64.b64encode(file_content).decode("utf-8")

    updated_image_data = {
        "filename": file.filename,  
        "image_data": base64_encoded, 
    }

    result = await db.database["images"].update_one(
        {"filename": filename},
        {"$set": updated_image_data},
    )

    if result.modified_count == 1:
        updated_posts = await db.database["posts"].update_many(
            {"cat_image.image_path": {"$regex": filename}}, 
            {
                "$set": {
                    "cat_image.filename": file.filename,
                    "cat_image.image_data": base64_encoded 
                }
            }
        )

        if updated_posts.modified_count > 0:
            return {"message": "Image and post(s) updated successfully", "filename": file.filename}

        return {"message": "Image updated successfully, but no posts were found to update"}

    raise HTTPException(status_code=400, detail="Failed to update the image.")
