from pydantic import BaseModel


class Image(BaseModel):
    image_id: str
    stored_filename: str
    image_path: str
