from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# ========== АУТЕНТИФИКАЦИЯ ==========

class LoginRequestDTO(BaseModel):
    """DTO для входа в систему"""
    login: str = Field(..., description="Логин или email")
    password: str = Field(..., min_length=1, description="Пароль")
    device_name: Optional[str] = Field(None, description="Название устройства")

    class Config:
        json_schema_extra = {
            "example": {
                "login": "ivan.petrov",
                "password": "securePass123",
                "device_name": "Chrome на Windows"
            }
        }


class LoginResponseDTO(BaseModel):
    """DTO для ответа при успешном входе"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(900, description="Время жизни access токена (секунды)")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIs...",
                "refresh_token": "550e8400-e29b-41d4-a716-446655440000",
                "token_type": "bearer",
                "expires_in": 900
            }
        }


# ========== ОБНОВЛЕНИЕ ТОКЕНА ==========

class RefreshRequestDTO(BaseModel):
    """DTO для обновления access токена"""
    refresh_token: str = Field(..., min_length=1, description="Refresh токен")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class RefreshResponseDTO(BaseModel):
    """DTO для ответа при обновлении токена (с ротацией)"""
    access_token: str
    refresh_token: str  # новый refresh token — старый уже отозван
    token_type: str = "bearer"
    expires_in: int = Field(900, description="Время жизни нового access токена (секунды)")


# ========== ВЫХОД ИЗ СИСТЕМЫ ==========

class LogoutRequestDTO(BaseModel):
    """DTO для выхода из системы (отзыв refresh токена)"""
    refresh_token: str = Field(..., min_length=1, description="Refresh токен для отзыва")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class LogoutResponseDTO(BaseModel):
    """DTO для ответа при выходе"""
    message: str = "Успешный выход"
    revoked_sessions: int = Field(1, description="Количество отозванных сессий")


# ========== УПРАВЛЕНИЕ СЕССИЯМИ ==========

class SessionInfoDTO(BaseModel):
    """DTO для информации о сессии (refresh токене)"""
    session_id: int
    device_name: Optional[str] = Field(None, description="Название устройства")
    device_ip: Optional[str] = Field(None, description="IP адрес")
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: datetime
    is_current: bool = Field(False, description="Является ли эта сессия текущей")

    class Config:
        from_attributes = True


class SessionsListDTO(BaseModel):
    """DTO для списка активных сессий пользователя"""
    sessions: List[SessionInfoDTO]
    total: int


class RevokeSessionRequestDTO(BaseModel):
    """DTO для отзыва конкретной сессии"""
    session_id: int = Field(..., gt=0, description="ID сессии для отзыва")


class RevokeAllSessionsRequestDTO(BaseModel):
    """DTO для отзыва всех сессий (кроме текущей)"""
    keep_current: bool = Field(True, description="Оставить текущую сессию?")


# ========== СМЕНА ПАРОЛЯ ==========

class ChangePasswordDTO(BaseModel):
    """DTO для смены пароля"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Пароль должен содержать минимум 6 символов')
        return v

class GrantRoleToOrganizationDTO(BaseModel):
    """DTO для выдачи роли организации"""
    organization_id: int = Field(..., gt=0, description="ID организации")
    role_id: int = Field(..., gt=0, description="ID роли")

    class Config:
        json_schema_extra = {
            "example": {
                "organization_id": 1,
                "role_id": 3
            }
        }