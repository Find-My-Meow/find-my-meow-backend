from pydantic import BaseModel


class Image(BaseModel):
    image_id: str
    image_path: str
