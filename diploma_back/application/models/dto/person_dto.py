from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from .device_dto import DeviceDTO


class PersonDTO(BaseModel):
    """DTO для вывода пользователя"""
    id: int
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: str
    role_id: int
    role_name: Optional[str] = None
    organization_id: Optional[int] = None
    organization_name: Optional[str] = None
    login: str
    avatar_url: Optional[str] = None
    avatar_filename: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class PersonDetailDTO(PersonDTO):
    """Расширенный DTO для пользователя с устройствами и токенами"""
    devices: List[DeviceDTO] = Field(default_factory=list, description="Устройства пользователя")
    active_sessions_count: int = Field(0, description="Количество активных сессий")


class PersonCreateDTO(BaseModel):
    """DTO для создания пользователя"""
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    email: str = Field(..., max_length=100)
    role_id: int = Field(..., gt=0)
    organization_id: Optional[int] = Field(None, gt=0)
    organization: Optional[str] = Field(None, max_length=200)  # новое поле
    login: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Неверный формат email')
        return v.lower()

    @validator('login')
    def validate_login(cls, v):
        if not v.replace('_', '').replace('.', '').isalnum():
            raise ValueError('Логин может содержать только буквы, цифры, _ и .')
        return v


class PersonUpdateDTO(BaseModel):
    """DTO для обновления пользователя"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    middle_name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    login: Optional[str] = Field(None, min_length=3, max_length=20)
    role_id: Optional[int] = Field(None, gt=0)
    organization_id: Optional[int] = Field(None, gt=0)
    organization: Optional[str] = Field(None, max_length=200)  # строка → ищем/создаём
    is_active: Optional[bool] = None
    avatar_filename: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    password_hash: Optional[str] = Field(None, max_length=255)


class ChangePasswordDTO(BaseModel):
    """DTO для смены пароля"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


class LoginRequestDTO(BaseModel):
    """DTO для входа в систему"""
    login: str = Field(..., description="Логин или email")
    password: str = Field(..., min_length=1)
    device_name: Optional[str] = Field(None, description="Название устройства")


class LoginResponseDTO(BaseModel):
    """DTO для ответа при входе"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: PersonDTO

class PersonDetailDTO(PersonDTO):
    """Расширенный DTO для пользователя с устройствами и токенами"""
    devices: List[DeviceDTO] = Field(default_factory=list, description="Устройства пользователя")
    active_sessions_count: int = Field(0, description="Количество активных сессий")