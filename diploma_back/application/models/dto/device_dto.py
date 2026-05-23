# device_dto.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeviceDTO(BaseModel):
    """
    DTO для вывода информации об устройстве.
    person_id убран — устройство не принадлежит конкретному пользователю.
    Связь device→person только через RefreshToken.
    """
    id: int
    device_name: str
    device_fingerprint: str
    is_trusted: bool
    first_seen: datetime
    last_seen: datetime

    class Config:
        from_attributes = True


class DeviceCreateDTO(BaseModel):
    """DTO для создания устройства (без person_id)"""
    device_name: str = Field(..., min_length=1, max_length=100)
    device_fingerprint: str = Field(..., min_length=1, max_length=255)
    is_trusted: bool = False


class DeviceUpdateDTO(BaseModel):
    """DTO для обновления устройства"""
    device_name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_trusted: Optional[bool] = None


class DeviceWithTokensDTO(DeviceDTO):
    """DTO для устройства со счётчиком активных токенов"""
    active_tokens_count: int = Field(0, description="Количество активных refresh токенов")
