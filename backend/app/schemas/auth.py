from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from ..models.models import RoleEnum

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
    org_id: Optional[int] = None
    roles: List[RoleEnum] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    organization_name: str
    organization_slug: str
