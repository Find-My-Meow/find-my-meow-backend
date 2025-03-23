from pydantic import BaseModel
from typing import List


class Image(BaseModel):
    image_id: str
    stored_filename: str
    image_path: str
    faiss_ids: List[int]