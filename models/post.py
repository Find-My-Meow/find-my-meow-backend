from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional
from models.location import Location
from models.image import Image


class Post(BaseModel):
    post_id: str
    user_id: str
    cat_name: Optional[str] = None
    gender: Literal["male", "female"]
    color: str
    breed: str
    cat_marking: Optional[str] = None
    location: Location
    lost_date: Optional[datetime] = None
    other_information: Optional[str] = None
    email_notification: bool
    cat_image: Image
    post_type: Literal["lost", "found", "adoption"]
    status: Literal["active", "close"]
