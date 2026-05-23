from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RefreshTokenDTO(BaseModel):
    """
    DTO для вывода информации о refresh токене.
    Именно здесь хранится связь (person_id, device_id) —
    а не в самой таблице device.
    """
    id: int
    person_id: int
    device_id: int
    expires_at: datetime
    revoked: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RefreshTokenCreateDTO(BaseModel):
    """DTO для создания refresh токена (person_id + device_id = сессия)"""
    person_id: int = Field(..., gt=0)
    device_id: int = Field(..., gt=0)
    expires_at: datetime
    token_hash: str = Field(..., min_length=1)


class RefreshTokenResponseDTO(BaseModel):
    """DTO для ответа при создании refresh токена"""
    refresh_token: str
    expires_in: int = Field(..., description="Время жизни в секундах")


class RevokeTokenDTO(BaseModel):
    """DTO для отзыва токена"""
    token_hash: str = Field(..., min_length=1)
