from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OrganizationDTO(BaseModel):
    """DTO для вывода информации об организации"""
    id: int
    name: str
    short_name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrganizationCreateDTO(BaseModel):
    """DTO для создания организации"""
    name: str = Field(..., min_length=1, max_length=200)
    short_name: Optional[str] = Field(None, max_length=50)
    inn: Optional[str] = Field(None, max_length=12)
    ogrn: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=300)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=200)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Металлургический институт",
                "short_name": "МИСиС",
                "inn": "1234567890",
                "ogrn": "1123456789012",
                "address": "г. Москва, ул. Металлургов, д. 1",
                "phone": "+7 (495) 123-45-67",
                "email": "info@misis.ru",
                "website": "https://misis.ru"
            }
        }


class OrganizationUpdateDTO(BaseModel):
    """DTO для обновления организации"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    short_name: Optional[str] = Field(None, max_length=50)
    inn: Optional[str] = Field(None, max_length=12)
    ogrn: Optional[str] = Field(None, max_length=15)
    address: Optional[str] = Field(None, max_length=300)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=200)