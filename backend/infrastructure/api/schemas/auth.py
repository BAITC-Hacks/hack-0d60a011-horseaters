from uuid import UUID

from pydantic import BaseModel, Field

from backend.domain.enums import UserRole


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class StaffResponse(BaseModel):
    id: UUID
    username: str
    display_name: str
    role: UserRole


class CreateBuyerRequest(BaseModel):
    username: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._@+-]*$")
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=256)
