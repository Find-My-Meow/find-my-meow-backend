from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional
from models.location import Location


class Post(BaseModel):
    user_id: str
    cat_name: str
    gender: Literal["male", "female"]
    color: str
    breed: str
    cat_marking: str
    location: Location
    lost_date: datetime = None
    other_information: str
    email_notification: bool
    cat_image: str = None
    post_type: Literal["lost", "found", "adoption"]

class UpdatePost(BaseModel):
    cat_name: Optional[str] = None
    cat_marking: Optional[str] = None
    gender: Optional[Literal["male", "female"]] = None
    color: Optional[str] = None
    breed: Optional[str] = None
    cat_info: Optional[str] = None
    location: Optional[Location] = None
    lost_date: Optional[datetime] = None
    other_information: Optional[str] = None
    email_notification: Optional[bool] = None
    cat_image: Optional[str] = None
    post_type: Optional[Literal["lost", "found", "adoption"]] = None
