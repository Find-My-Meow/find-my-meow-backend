from pydantic import BaseModel, EmailStr

class User(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str
