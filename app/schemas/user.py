from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    # Enforce the password policy in the backend, not only in the frontend.
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str