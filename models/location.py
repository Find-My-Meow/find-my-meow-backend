from pydantic import BaseModel


class Location(BaseModel):
    province: str
    district: str
    sub_district: str
