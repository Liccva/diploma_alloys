# application/utils/auth.py
from application.models.dao import Person, Alloy  # ← добавить
"""Утилиты для авторизации и работы с токенами"""

import jwt
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from passlib.context import CryptContext  # pip install passlib
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from application.config import SessionLocal
from application.services import repository_service as service

# ========== НАСТРОЙКИ ==========
SECRET_KEY = "your-super-secret-key-change-in-production"  # В .env файл!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Хэширование паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security для извлечения токена из заголовка
security = HTTPBearer(auto_error=False)


# ========== ПАРОЛИ ==========

def get_password_hash(password: str) -> str:
    """Хэширует пароль"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет пароль.
    Поддерживает bcrypt (новый формат) и md5 (устаревший формат для совместимости).
    При успешной проверке md5 автоматически рекомендуется перехэшировать через get_password_hash.
    """
    if not hashed_password:
        return False

    # Bcrypt хэши начинаются с $2b$ или $2a$
    if hashed_password.startswith(('$2b$', '$2a$', '$2y$')):
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False

    # Обратная совместимость: md5 хэш (32 символа hex)
    if len(hashed_password) == 32:
        import hashlib
        return hashlib.md5(plain_password.encode()).hexdigest() == hashed_password

    # Попытка через passlib на случай других форматов
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Хэширует refresh token для хранения в БД"""
    return hashlib.sha256(token.encode()).hexdigest()


# ========== ACCESS TOKEN (JWT) ==========

def create_access_token(person_id: int, login: str, role_name: str = None) -> str:
    """Создает access token (JWT)"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "person_id": person_id,
        "login": login,
        "role": role_name,
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Проверяет access token и возвращает payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ========== REFRESH TOKEN ==========

def create_refresh_token() -> str:
    """Создает случайный refresh token"""
    return str(uuid.uuid4())


# application/utils/auth.py - обновите функцию create_refresh_token_in_db

def create_refresh_token_in_db(
        db: Session,
        person_id: int,
        device_id: int  # ← изменили с device_name на device_id
) -> str:
    """Создает и сохраняет refresh token в БД"""
    from application.models.dao import RefreshToken
    from datetime import timedelta

    refresh_token = create_refresh_token()
    token_hash = hash_token(refresh_token)

    db_token = RefreshToken(
        token_hash=token_hash,
        person_id=person_id,
        device_id=device_id,  # ← теперь device_id
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
        created_at=datetime.utcnow()
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return refresh_token


def validate_refresh_token(db: Session, refresh_token: str) -> Optional[int]:
    """Проверяет refresh token и возвращает person_id если валиден"""
    from application.models.dao import RefreshToken

    token_hash = hash_token(refresh_token)

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()

    if db_token:
        # Обновляем время последнего использования
        db_token.last_used_at = datetime.utcnow()
        db.commit()
        return db_token.person_id
    return None


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    """Отзывает refresh token (при выходе)"""
    from application.models.dao import RefreshToken

    token_hash = hash_token(refresh_token)

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()

    if db_token:
        db_token.revoked = True
        db.commit()
        return True
    return False


def revoke_all_user_tokens(db: Session, person_id: int, exclude_token_hash: str = None) -> int:
    """Отзывает все refresh токены пользователя"""
    from application.models.dao import RefreshToken

    query = db.query(RefreshToken).filter(
        RefreshToken.person_id == person_id,
        RefreshToken.revoked == False
    )
    if exclude_token_hash:
        query = query.filter(RefreshToken.token_hash != exclude_token_hash)

    count = query.update({"revoked": True})
    db.commit()
    return count


# ========== DEPENDENCIES ДЛЯ FASTAPI ==========

def get_db():
    """Получение сессии БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
):
    """Получает текущего пользователя из access token"""
    token = credentials.credentials

    # Проверяем access token
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получаем пользователя из БД
    person_id = payload.get("person_id")
    if not person_id:
        raise HTTPException(status_code=401, detail="Неверный токен")

    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    if not person.is_active:
        raise HTTPException(status_code=401, detail="Пользователь заблокирован")

    return person


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Проверяет что пользователь активен"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь заблокирован")
    return current_user


def role_required(required_role: str):
    """Декоратор для проверки роли"""

    async def role_checker(current_user=Depends(get_current_user)):
        if not current_user.role or current_user.role.name != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Требуется роль: {required_role}"
            )
        return current_user

    return role_checker


# application/utils/auth.py - добавьте эту функцию в конец файла

def create_device_fingerprint(user_agent: str, ip: Optional[str] = None) -> str:
    """
    Создание уникального отпечатка устройства на основе User-Agent и IP

    Args:
        user_agent: Строка User-Agent из заголовка запроса
        ip: IP адрес (опционально)

    Returns:
        SHA256 хэш для идентификации устройства
    """
    import hashlib

    fingerprint_data = f"{user_agent}|{ip or ''}"
    fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()

    return fingerprint


# application/utils/auth.py

from functools import wraps
from fastapi import HTTPException, status, Depends
from typing import Optional, List
from sqlalchemy.orm import Session


# ... существующие импорты ...


# ========== ОСНОВНЫЕ ФУНКЦИИ ПРОВЕРКИ ПРАВ ==========

# Поддерживаем оба варианта названий ролей: английские и русские
ADMIN_ROLES      = {'admin', 'администратор'}
RESEARCHER_ROLES = {'researcher', 'исследователь'}


def is_admin(user: Person) -> bool:
    """Проверка, является ли пользователь администратором"""
    return bool(user.role and user.role.name.strip().lower() in ADMIN_ROLES)


def is_researcher(user: Person) -> bool:
    """Проверка, является ли пользователь исследователем"""
    return bool(user.role and user.role.name.strip().lower() in RESEARCHER_ROLES)


def is_author_of_patent(db: Session, user_id: int, patent_id: int) -> bool:
    """Проверка, является ли пользователь автором патента"""
    from application.services import repository_service as service

    authors = service.get_patent_authors(db, patent_id)
    return any(author.person_id == user_id for author in authors)


def is_creator_of_alloy(db: Session, user_id: int, alloy_id: int) -> bool:
    """Проверка, является ли пользователь создателем сплава"""
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        return False
    return alloy.created_by_id == user_id


def can_edit_patent(db: Session, user: Person, patent_id: int) -> bool:
    """Может ли пользователь редактировать патент"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return is_author_of_patent(db, user.id, patent_id)
    return False


def can_edit_alloy(db: Session, user: Person, alloy_id: int) -> bool:
    """Может ли пользователь редактировать сплав"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return is_creator_of_alloy(db, user.id, alloy_id)
    return False


def can_view_prediction(user: Person, prediction_person_id: int) -> bool:
    """Может ли пользователь просматривать прогноз"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return user.id == prediction_person_id
    return False


def can_edit_prediction(user: Person, prediction_person_id: int) -> bool:
    """Может ли пользователь редактировать прогноз"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return user.id == prediction_person_id
    return False


# ========== DEPENDENCIES ДЛЯ FASTAPI ==========

def get_current_user_optional(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security, use_cache=True),
        db: Session = Depends(get_db)
) -> Optional[Person]:
    """Получает текущего пользователя или None (для неавторизованных)"""
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        return None

    person_id = payload.get("person_id")
    if not person_id:
        return None

    from application.services import repository_service as service
    person = service.get_person_by_id(db, person_id)
    return person


def require_admin(current_user: Person = Depends(get_current_user)):
    """Требует права администратора (admin или администратор)"""
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin rights required"
        )
    return current_user


def require_researcher(current_user: Person = Depends(get_current_user)):
    """Требует права исследователя или администратора (researcher / исследователь / admin / администратор)"""
    if not is_researcher(current_user) and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researcher rights required"
        )
    return current_user


def can_edit_patent_dependency(patent_id: int):
    """Dependency для проверки прав на редактирование патента"""

    async def _check(
            db: Session = Depends(get_db),
            current_user: Person = Depends(get_current_user)
    ):
        if not can_edit_patent(db, current_user, patent_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not author of this patent"
            )
        return current_user

    return _check


def can_edit_alloy_dependency(alloy_id: int):
    """Dependency для проверки прав на редактирование сплава"""

    async def _check(
            db: Session = Depends(get_db),
            current_user: Person = Depends(get_current_user)
    ):
        if not can_edit_alloy(db, current_user, alloy_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not creator of this alloy"
            )
        return current_user

    return _check


def can_view_prediction_dependency(prediction_id: int):
    """Dependency для проверки прав на просмотр прогноза"""

    async def _check(
            db: Session = Depends(get_db),
            current_user: Person = Depends(get_current_user)
    ):
        from application.services import repository_service as service
        prediction = service.get_prediction_by_id(db, prediction_id)
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        if not can_view_prediction(current_user, prediction.person_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own predictions"
            )
        return current_user

    return _check

# application/utils/auth.py - добавьте недостающие функции

def can_edit_patent(db: Session, user: Person, patent_id: int) -> bool:
    """Может ли пользователь редактировать патент"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return is_author_of_patent(db, user.id, patent_id)
    return False


def can_edit_alloy(db: Session, user: Person, alloy_id: int) -> bool:
    """Может ли пользователь редактировать сплав"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return is_creator_of_alloy(db, user.id, alloy_id)
    return False


def can_view_prediction(user: Person, prediction_person_id: int) -> bool:
    """Может ли пользователь просматривать прогноз"""
    if is_admin(user):
        return True
    if is_researcher(user):
        return user.id == prediction_person_id
    return False