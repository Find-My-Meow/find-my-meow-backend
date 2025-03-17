import traceback
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from core.database import db
from typing import List, Optional
from models.image import Image
from models.post import Post
from services.image_service import delete_image_service, upload_cat_image
from services.post_service import parse_location, parse_lost_date
from utils.utils import get_next_post_id


post_router = APIRouter()

# TODO: add post status


@post_router.post("/", response_model=Post)
async def create_post(
    user_id: str = Form(...),
    cat_name: Optional[str] = Form(None),
    gender: str = Form(...),
    color: str = Form(...),
    breed: str = Form(...),
    cat_marking: Optional[str] = Form(None),
    location: str = Form(...),
    lost_date: Optional[str] = Form(None),
    other_information: Optional[str] = Form(None),
    email_notification: bool = Form(...),
    post_type: str = Form(...),
    cat_image: UploadFile = File(...),
):
    """
    Creates a new post with a cat image.
    """
    uploaded_image = None
    try:
        # Parse Location JSON String
        location_obj = parse_location(location)

        # Upload image
        uploaded_image = await upload_cat_image(cat_image)

        # Generate Post ID
        post_id = await get_next_post_id()

        # Convert string to datetime
        lost_date_parsed = parse_lost_date(
            lost_date) if lost_date else None

        # Insert new post to database
        post_obj = Post(
            post_id=post_id,
            user_id=user_id,
            cat_name=cat_name,
            gender=gender,
            color=color,
            breed=breed,
            cat_marking=cat_marking,
            location=location_obj,
            lost_date=lost_date_parsed,
            other_information=other_information,
            email_notification=email_notification,
            post_type=post_type,
            cat_image=Image(**uploaded_image),
        )
        result = await db.database["posts_v2"].insert_one(post_obj.model_dump(by_alias=True))

        if result.inserted_id:
            # Return Post response
            return post_obj

        raise HTTPException(status_code=500, detail="Failed to create post")

    except Exception as e:
        # Delete uploaded image if fail to create post.
        if uploaded_image:
            await delete_image_service(uploaded_image["image_id"])

        # debug
        # error_message = traceback.format_exc()
        # print("Error Traceback:\n", error_message)
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}")


# Get all posts, filter by post_type
@post_router.get("/", response_model=List[Post])
async def list_posts(post_type: Optional[str] = None):
    """
    Get all posts, filter by post_type.
    Return list of Post
    """
    query = {}
    if post_type:
        query["post_type"] = post_type

    posts = await db.database["posts_v2"].find(query).to_list(length=100)

    if not posts:
        raise HTTPException(status_code=404, detail="No posts found.")

    return posts


@post_router.get("/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """
    Get a post by post_id.
    """
    try:
        post = await db.database["posts_v2"].find_one({"post_id": str(post_id)})
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid post ID: {str(e)}")

    if post:
        return post

    raise HTTPException(status_code=404, detail="Post not found")

# Get post by user ID


@post_router.get("/user/{user_id}", response_model=List[Post])
async def get_posts_by_user(user_id: str):
    """
    Get all posts created by a specific user.
    """
    posts = await db.database["posts_v2"].find({"user_id": user_id}).to_list()

    if not posts:
        raise HTTPException(
            status_code=404, detail="No posts found for this user")

    return posts


# TODO: Check update post
# Update post by ID
@post_router.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: str,
    user_id: str = Form(...),
    cat_name: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    breed: Optional[str] = Form(None),
    cat_marking: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    lost_date: Optional[str] = Form(None),
    other_information: Optional[str] = Form(None),
    email_notification: Optional[bool] = Form(None),
    post_type: Optional[str] = Form(None),
    image_id: Optional[str] = Form(None),
    cat_image: Optional[UploadFile] = File(None),
):
    """
    Updates an existing post.
    Detects if an image is new or unchanged.
    Skips update if no changes are detected.
    """
    existing_post = await db.database["posts_v2"].find_one({"post_id": post_id})
    if not existing_post:
        raise HTTPException(status_code=404, detail="Post not found")

    updated_fields = {}

    old_image_id = existing_post.get("cat_image", {}).get(
        "image_id") if existing_post.get("cat_image") else None

    # Handle Location update
    if location:
        location_obj = parse_location(location)
        if location_obj != existing_post["location"]:
            updated_fields["location"] = location_obj.model_dump()

    # Compare and detect changes
    fields_to_check = {
        "cat_name": cat_name,
        "gender": gender,
        "color": color,
        "breed": breed,
        "cat_marking": cat_marking,
        "other_information": other_information,
        "email_notification": email_notification,
        "post_type": post_type,
    }

    for field, value in fields_to_check.items():
        if value is not None and value != existing_post.get(field):
            updated_fields[field] = value

    # Convert lost date
    if lost_date:
        lost_date_parsed = parse_lost_date(lost_date)
        if lost_date_parsed != existing_post.get("lost_date"):
            updated_fields["lost_date"] = lost_date_parsed

    # Handle Image update
    new_uploaded_image = None
    if image_id and image_id == old_image_id:
        print("Using existing image, no change.")

    elif cat_image:
        print("Uploading new cat image")
        new_uploaded_image = await upload_cat_image(cat_image)
        updated_fields["cat_image"] = new_uploaded_image

    elif not image_id and not cat_image:
        updated_fields["cat_image"] = None

    #  No Changes
    if not updated_fields:
        return {"message": "No changes detected, post remains the same.", "post_id": post_id}

    # Update post to database
    await db.database["posts_v2"].update_one(
        {"post_id": post_id}, {"$set": updated_fields}
    )

    # Delete old image if replaced
    if new_uploaded_image and old_image_id:
        await delete_image_service(old_image_id)

    #  Return updated post
    updated_post = await db.database["posts_v2"].find_one({"post_id": post_id})
    return updated_post


@post_router.delete("/{post_id}")
async def delete_post(post_id: str):
    """
    Deletes a post by post_id and removes its associated image.
    """
    try:
        post_data = await db.database["posts_v2"].find_one({"post_id": post_id})
        if not post_data:
            raise HTTPException(status_code=404, detail="Post not found")

        image_id = post_data.get("cat_image", {}).get("image_id")

        # Delete the post from database
        await db.database["posts_v2"].delete_one({"post_id": post_id})

        # Delete the post image
        if image_id:
            await delete_image_service(image_id)

        return {"message": "Post deleted successfully", "post_id": post_id}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete post: {str(e)}")
