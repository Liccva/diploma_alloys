"""
Тесты API

Запуск: pytest test_routes.py -v
"""

import sys
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, Body
from fastapi.responses import RedirectResponse
from fastapi.testclient import TestClient
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime,
    Numeric, Text, ForeignKey, Table, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.pool import StaticPool
import jwt

# =========================================================
#  МОДЕЛИ БД (упрощённая копия alloys.py / dao)
# =========================================================

Base = declarative_base()

alloy_element_association = Table(
    'alloy_element_association', Base.metadata,
    Column('alloy_id', Integer, ForeignKey('alloy.id'), primary_key=True),
    Column('element_id', Integer, ForeignKey('chemical_element.id'), primary_key=True),
    Column('percentage', Numeric(5, 3), nullable=False),
)

prediction_element_association = Table(
    'prediction_element_association', Base.metadata,
    Column('prediction_id', Integer, ForeignKey('prediction.id'), primary_key=True),
    Column('element_id', Integer, ForeignKey('chemical_element.id'), primary_key=True),
    Column('percentage', Numeric(5, 3), nullable=False),
)


class Role(Base):
    __tablename__ = "role"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
    description = Column(String(100))
    persons = relationship('Person', back_populates='role')


class Organization(Base):
    __tablename__ = "organization"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    short_name = Column(String(50))
    inn = Column(String(12))
    ogrn = Column(String(15))
    address = Column(String(300))
    phone = Column(String(20))
    email = Column(String(100))
    website = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    persons = relationship('Person', back_populates='organization_rel')


class Person(Base):
    __tablename__ = "person"
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    email = Column(String(100), nullable=False, unique=True)
    role_id = Column(Integer, ForeignKey('role.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organization.id'))
    login = Column(String(20), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    avatar_filename = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    role = relationship('Role', back_populates='persons')
    organization_rel = relationship('Organization', back_populates='persons')
    predictions = relationship('Prediction', back_populates='person')
    refresh_tokens = relationship('RefreshToken', back_populates='person')
    devices = relationship('Device', back_populates='person')
    patents_authored = relationship('PatentAuthor', back_populates='person')


class Device(Base):
    __tablename__ = "device"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    device_name = Column(String(100), nullable=False)
    device_fingerprint = Column(String(255), nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_trusted = Column(Boolean, default=True)
    person = relationship('Person', back_populates='devices')
    refresh_tokens = relationship('RefreshToken', back_populates='device')


class RefreshToken(Base):
    __tablename__ = "refresh_token"
    id = Column(Integer, primary_key=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('device.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    person = relationship('Person', back_populates='refresh_tokens')
    device = relationship('Device', back_populates='refresh_tokens')


class Patent(Base):
    __tablename__ = "patent"
    id = Column(Integer, primary_key=True)
    patent_number = Column(String(50), nullable=False, unique=True)
    country = Column(String(10))
    patent_name = Column(String(500), nullable=False)
    filing_date = Column(DateTime)
    issue_date = Column(DateTime)
    assignee = Column(String(300))
    ipc_code = Column(String(50))
    description = Column(Text)
    pdf_url = Column(String(500))
    pdf_filename = Column(String(255))
    category = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    alloys = relationship('Alloy', back_populates='patent')
    authors = relationship('PatentAuthor', back_populates='patent', cascade='all, delete-orphan')


class PatentAuthor(Base):
    __tablename__ = "patent_author"
    id = Column(Integer, primary_key=True)
    patent_id = Column(Integer, ForeignKey('patent.id'), nullable=False)
    person_id = Column(Integer, ForeignKey('person.id'))
    author_name = Column(String(200), nullable=False)
    author_order = Column(Integer, default=0)
    patent = relationship('Patent', back_populates='authors')
    person = relationship('Person', back_populates='patents_authored')
    __table_args__ = (
        UniqueConstraint('patent_id', 'author_order', name='uq_patent_author_order'),
    )


class ChemicalElement(Base):
    __tablename__ = "chemical_element"
    id = Column(Integer, primary_key=True)
    name = Column(String(12), nullable=False, unique=True)
    atomic_number = Column(Integer, nullable=False, unique=True)
    symbol = Column(String(2), nullable=False, unique=True)
    alloys = relationship('Alloy', secondary=alloy_element_association, back_populates="elements")
    predictions = relationship('Prediction', secondary=prediction_element_association, back_populates="elements")


class Alloy(Base):
    __tablename__ = "alloy"
    id = Column(Integer, primary_key=True)
    _prop_value = Column('prop_value', Numeric, nullable=True)
    temperature = Column(Numeric(10, 3))
    category = Column(String(100))
    rolling_type = Column(String(50))
    patent_id = Column(Integer, ForeignKey('patent.id'), nullable=False)
    patent = relationship('Patent', back_populates="alloys")
    elements = relationship('ChemicalElement', secondary=alloy_element_association, back_populates="alloys")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('person.id'))

    @hybrid_property
    def prop_value(self):
        return self._prop_value

    @prop_value.setter
    def prop_value(self, value):
        self._prop_value = 0 if (value is not None and value < 0) else value

    @prop_value.expression
    def prop_value(cls):
        return cls._prop_value


class Model(Base):
    __tablename__ = "model"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200))
    predictions = relationship('Prediction', back_populates='model')


class Prediction(Base):
    __tablename__ = "prediction"
    id = Column(Integer, primary_key=True)
    temperature = Column(Numeric(10, 3))
    category = Column(String(100))
    ml_model_id = Column(Integer, ForeignKey('model.id'), nullable=False)
    model = relationship('Model', back_populates="predictions")
    rolling_type = Column(String(50))
    _prop_value = Column('prop_value', Numeric, nullable=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    person = relationship('Person', back_populates="predictions")
    elements = relationship('ChemicalElement', secondary=prediction_element_association, back_populates="predictions")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @hybrid_property
    def prop_value(self):
        return self._prop_value

    @prop_value.setter
    def prop_value(self, value):
        self._prop_value = 0 if (value is not None and value < 0) else value

    @prop_value.expression
    def prop_value(cls):
        return cls._prop_value


# =========================================================
#  AUTH UTILS
# =========================================================

SECRET_KEY = "test-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer(auto_error=False)


def get_password_hash(password: str) -> str:
    return "sha256:" + hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("sha256:"):
        return hashed == get_password_hash(plain)
    return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(person_id: int, login: str, role_name: str = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "person_id": person_id,
        "login": login,
        "role": role_name,
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def create_refresh_token_value() -> str:
    return str(uuid.uuid4())


def create_device_fingerprint(user_agent: str, ip: Optional[str] = None) -> str:
    data = f"{user_agent}|{ip or ''}"
    return hashlib.sha256(data.encode()).hexdigest()


def is_admin(user: Person) -> bool:
    return user.role and user.role.name == 'admin'


def is_researcher(user: Person) -> bool:
    return user.role and user.role.name == 'researcher'


# =========================================================
#  IN-MEMORY SQLite ENGINE
# =========================================================

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================================================
#  AUTH DEPENDENCIES
# =========================================================

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Person:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    token = credentials.credentials
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверный или истекший токен",
                            headers={"WWW-Authenticate": "Bearer"})
    person_id = payload.get("person_id")
    if not person_id:
        raise HTTPException(status_code=401, detail="Неверный токен")
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    if not person.is_active:
        raise HTTPException(status_code=401, detail="Пользователь заблокирован")
    return person


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[Person]:
    if not credentials:
        return None
    payload = verify_access_token(credentials.credentials)
    if not payload:
        return None
    person_id = payload.get("person_id")
    if not person_id:
        return None
    return db.query(Person).filter(Person.id == person_id).first()


def require_admin(current_user: Person = Depends(get_current_user)) -> Person:
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin rights required")
    return current_user


def require_researcher(current_user: Person = Depends(get_current_user)) -> Person:
    if not (is_admin(current_user) or is_researcher(current_user)):
        raise HTTPException(status_code=403, detail="Researcher rights required")
    return current_user


def can_edit_alloy_dep(alloy_id: int):
    def _check(db: Session = Depends(get_db),
               current_user: Person = Depends(get_current_user)) -> Person:
        if is_admin(current_user):
            return current_user
        alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
        if not alloy or alloy.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not creator of this alloy")
        return current_user
    return _check


def can_edit_patent_dep(patent_id: int):
    def _check(db: Session = Depends(get_db),
               current_user: Person = Depends(get_current_user)) -> Person:
        if is_admin(current_user):
            return current_user
        if is_researcher(current_user):
            author = db.query(PatentAuthor).filter(
                PatentAuthor.patent_id == patent_id,
                PatentAuthor.person_id == current_user.id
            ).first()
            if author:
                return current_user
        raise HTTPException(status_code=403, detail="You are not author of this patent")
    return _check


def can_view_prediction_dep(prediction_id: int):
    def _check(db: Session = Depends(get_db),
               current_user: Person = Depends(get_current_user)) -> Person:
        if is_admin(current_user):
            return current_user
        pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not pred:
            raise HTTPException(status_code=404, detail="Prediction not found")
        if pred.person_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only view your own predictions")
        return current_user
    return _check


# =========================================================
#  PYDANTIC SCHEMAS
# =========================================================

class PersonCreateSchema(BaseModel):
    first_name: str
    last_name: str
    email: str
    role_id: int
    login: str
    password: str
    middle_name: Optional[str] = None
    organization_id: Optional[int] = None


class PersonUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    login: str
    password: str
    device_name: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class PatentCreateSchema(BaseModel):
    patent_number: str
    patent_name: str
    country: Optional[str] = None
    ipc_code: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None


class PatentUpdateSchema(BaseModel):
    patent_name: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None


class PatentAuthorSchema(BaseModel):
    author_name: str
    author_order: int


class PatentCreateWithAuthorsSchema(BaseModel):
    patent_number: str
    patent_name: str
    country: Optional[str] = None
    ipc_code: Optional[str] = None
    authors: List[PatentAuthorSchema] = []


class AlloyCreateSchema(BaseModel):
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None
    rolling_type: Optional[str] = None
    patent_id: int


class AlloyUpdateSchema(BaseModel):
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None
    rolling_type: Optional[str] = None


class PredictionCreateSchema(BaseModel):
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None
    ml_model_id: int
    rolling_type: Optional[str] = None


class PredictionUpdateSchema(BaseModel):
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None


class ElementCreateSchema(BaseModel):
    name: str
    atomic_number: int
    symbol: str


class RoleCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None


class ModelCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationCreateSchema(BaseModel):
    name: str
    short_name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class OrganizationUpdateSchema(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None


class GrantRoleSchema(BaseModel):
    organization_id: int
    role_id: int


class MLPredictElementSchema(BaseModel):
    element_id: int
    percentage: float


class MLPredictRequestSchema(BaseModel):
    ml_model_id: int
    category: str
    rolling_type: str
    temperature: Optional[float] = None
    elements: List[MLPredictElementSchema] = []


class FindSimilarRequestSchema(BaseModel):
    composition: Dict[str, float]
    limit: int = 10


# =========================================================
#  FASTAPI APP + ROUTES
# =========================================================

app = FastAPI(title="Test App")
router = APIRouter(prefix='/api')


@router.get('/')
async def root():
    return RedirectResponse(url='/docs', status_code=307)


# --- AUTH ---

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, req_obj: Request, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.login == request.login).first()
    if not person:
        person = db.query(Person).filter(Person.email == request.login).first()
    if not person or not verify_password(request.password, person.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not person.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    user_agent = req_obj.headers.get("user-agent", "Unknown")
    fingerprint = create_device_fingerprint(user_agent)

    device = db.query(Device).filter(Device.device_fingerprint == fingerprint).first()
    if not device:
        device = Device(
            person_id=person.id,
            device_name=request.device_name or user_agent[:100],
            device_fingerprint=fingerprint,
            is_trusted=False,
        )
        db.add(device)
        db.flush()

    access_token = create_access_token(person.id, person.login,
                                       person.role.name if person.role else None)
    refresh_val = create_refresh_token_value()
    token_hash = hash_token(refresh_val)
    db_token = RefreshToken(
        token_hash=token_hash,
        person_id=person.id,
        device_id=device.id,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(db_token)
    person.last_login = datetime.utcnow()
    db.commit()
    return LoginResponse(access_token=access_token, refresh_token=refresh_val)


@router.post("/auth/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(request.refresh_token)
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow(),
    ).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    person = db.query(Person).filter(Person.id == db_token.person_id).first()
    if not person:
        raise HTTPException(status_code=401, detail="User not found")
    db_token.last_used_at = datetime.utcnow()
    db.commit()
    access_token = create_access_token(person.id, person.login,
                                       person.role.name if person.role else None)
    return RefreshResponse(access_token=access_token)


@router.post("/auth/logout")
async def logout(request: LogoutRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(request.refresh_token)
    db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not db_token:
        raise HTTPException(status_code=404, detail="Token not found")
    db_token.revoked = True
    db.commit()
    return {"message": "Logged out successfully"}


# --- PERSONS ---

@router.post("/persons/", status_code=201)
async def create_person(person: PersonCreateSchema, db: Session = Depends(get_db)):
    if db.query(Person).filter(Person.login == person.login).first():
        raise HTTPException(status_code=409, detail="Login already taken")
    if db.query(Person).filter(Person.email == person.email).first():
        raise HTTPException(status_code=409, detail="Email already taken")
    role = db.query(Role).filter(Role.id == person.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    p = Person(
        first_name=person.first_name,
        last_name=person.last_name,
        middle_name=person.middle_name,
        email=person.email,
        role_id=person.role_id,
        organization_id=person.organization_id,
        login=person.login,
        password_hash=get_password_hash(person.password),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "login": p.login, "email": p.email}


@router.get("/persons/")
async def get_persons(_: Person = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(Person).all()


@router.get("/persons/login/{login}")
async def get_person_by_login(login: str, _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    p = db.query(Person).filter(Person.login == login).first()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    return p


@router.get("/persons/email/{email}")
async def get_person_by_email(email: str, _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    p = db.query(Person).filter(Person.email == email).first()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    return p


@router.get("/persons/role/{role_id}")
async def get_persons_by_role(role_id: int, _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    return db.query(Person).filter(Person.role_id == role_id).all()


@router.get("/persons/{person_id}")
async def get_person_by_id(person_id: int, _: Person = Depends(require_admin),
                            db: Session = Depends(get_db)):
    p = db.query(Person).filter(Person.id == person_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    return p


@router.put("/persons/{person_id}")
async def update_person(person_id: int, data: PersonUpdateSchema,
                         _: Person = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Person).filter(Person.id == person_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/persons/{person_id}")
async def delete_person(person_id: int, _: Person = Depends(require_admin),
                         db: Session = Depends(get_db)):
    p = db.query(Person).filter(Person.id == person_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Person not found")
    db.delete(p)
    db.commit()
    return {"message": "Person deleted"}


@router.get("/persons/{person_id}/devices")
async def get_person_devices(person_id: int, _: Person = Depends(require_admin),
                              db: Session = Depends(get_db)):
    return db.query(Device).filter(Device.person_id == person_id).all()


# --- ELEMENTS ---

@router.get("/elements/")
async def get_all_elements(db: Session = Depends(get_db)):
    elements = db.query(ChemicalElement).all()
    if not elements:
        raise HTTPException(status_code=404, detail="No elements found")
    return elements


@router.get("/elements/symbol/{symbol}")
async def get_element_by_symbol(symbol: str, db: Session = Depends(get_db)):
    el = db.query(ChemicalElement).filter(ChemicalElement.symbol == symbol).first()
    if not el:
        raise HTTPException(status_code=404, detail="Element not found")
    return el


@router.get("/elements/{element_id}")
async def get_element_by_id(element_id: int, db: Session = Depends(get_db)):
    el = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not el:
        raise HTTPException(status_code=404, detail="Element not found")
    return el


@router.post("/elements/", status_code=201)
async def create_element(element: ElementCreateSchema,
                          _: Person = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(ChemicalElement).filter(ChemicalElement.symbol == element.symbol).first():
        raise HTTPException(status_code=409, detail="Symbol already exists")
    el = ChemicalElement(name=element.name, atomic_number=element.atomic_number, symbol=element.symbol)
    db.add(el)
    db.commit()
    db.refresh(el)
    return {"id": el.id, "symbol": el.symbol, "message": "Chemical element created successfully"}


# --- PATENTS ---

@router.get("/patents/")
async def get_all_patents(db: Session = Depends(get_db)):
    return db.query(Patent).all()


@router.get("/patents/number/{patent_number}")
async def get_patent_by_number(patent_number: str, db: Session = Depends(get_db)):
    p = db.query(Patent).filter(Patent.patent_number == patent_number).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patent not found")
    return p


@router.get("/patents/{patent_id}/authors")
async def get_patent_authors(patent_id: int, db: Session = Depends(get_db)):
    return db.query(PatentAuthor).filter(PatentAuthor.patent_id == patent_id).all()


@router.get("/patents/{patent_id}")
async def get_patent_by_id(patent_id: int, db: Session = Depends(get_db)):
    p = db.query(Patent).filter(Patent.id == patent_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patent not found")
    return p


@router.post("/patents/", status_code=201)
async def create_patent(patent: PatentCreateSchema,
                         current_user: Person = Depends(require_researcher),
                         db: Session = Depends(get_db)):
    if db.query(Patent).filter(Patent.patent_number == patent.patent_number).first():
        raise HTTPException(status_code=409, detail="Patent number already exists")
    category = None
    if patent.ipc_code:
        prefix = patent.ipc_code[:3].upper()
        category = "steel" if prefix.startswith("C22") else "other"
    p = Patent(
        patent_number=patent.patent_number,
        patent_name=patent.patent_name,
        country=patent.country,
        ipc_code=patent.ipc_code,
        description=patent.description,
        assignee=patent.assignee,
        category=category,
    )
    db.add(p)
    db.flush()
    # Добавляем автора (текущего исследователя)
    author = PatentAuthor(patent_id=p.id, person_id=current_user.id,
                          author_name=f"{current_user.first_name} {current_user.last_name}",
                          author_order=1)
    db.add(author)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "patent_number": p.patent_number, "message": "Patent created"}


@router.post("/patents/with-authors/", status_code=201)
async def create_patent_with_authors(patent: PatentCreateWithAuthorsSchema,
                                      _: Person = Depends(require_researcher),
                                      db: Session = Depends(get_db)):
    if db.query(Patent).filter(Patent.patent_number == patent.patent_number).first():
        raise HTTPException(status_code=409, detail="Patent number already exists")
    p = Patent(
        patent_number=patent.patent_number,
        patent_name=patent.patent_name,
        country=patent.country,
        ipc_code=patent.ipc_code,
    )
    db.add(p)
    db.flush()
    for author_data in patent.authors:
        author = PatentAuthor(patent_id=p.id, author_name=author_data.author_name,
                              author_order=author_data.author_order)
        db.add(author)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "message": "Patent with authors created"}


@router.post("/patents/{patent_id}/authors", status_code=201)
async def add_patent_author(patent_id: int, author_name: str, author_order: int = 0,
                             _: Person = Depends(require_researcher),
                             db: Session = Depends(get_db)):
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    author = PatentAuthor(patent_id=patent_id, author_name=author_name, author_order=author_order)
    db.add(author)
    db.commit()
    return {"message": "Author added"}


@router.put("/patents/{patent_id}")
async def update_patent(patent_id: int, data: PatentUpdateSchema,
                         current_user: Person = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    if not is_admin(current_user):
        author = db.query(PatentAuthor).filter(
            PatentAuthor.patent_id == patent_id,
            PatentAuthor.person_id == current_user.id
        ).first()
        if not author:
            raise HTTPException(status_code=403, detail="You are not author of this patent")
    # NOTE: can_edit_patent_dep(0) means admin-only in practice for simplicity
    p = db.query(Patent).filter(Patent.id == patent_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patent not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/patents/{patent_id}")
async def delete_patent(patent_id: int, _: Person = Depends(require_admin),
                         db: Session = Depends(get_db)):
    p = db.query(Patent).filter(Patent.id == patent_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patent not found")
    db.delete(p)
    db.commit()
    return {"message": "Patent deleted"}


# --- ALLOYS ---

@router.get("/alloys/")
async def get_all_alloys(skip: int = 0, limit: int = 100,
                          db: Session = Depends(get_db),
                          _: Optional[Person] = Depends(get_current_user_optional)):
    return db.query(Alloy).offset(skip).limit(limit).all()


@router.get("/alloys/patent/{patent_id}")
async def get_alloys_by_patent(patent_id: int, db: Session = Depends(get_db)):
    return db.query(Alloy).filter(Alloy.patent_id == patent_id).all()


@router.get("/alloys/category/{category}")
async def search_alloys_by_category(category: str, db: Session = Depends(get_db)):
    return db.query(Alloy).filter(Alloy.category.ilike(f"%{category}%")).all()


@router.get("/alloys/{alloy_id}/elements")
async def get_alloy_elements(alloy_id: int, db: Session = Depends(get_db)):
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        raise HTTPException(status_code=404, detail="Alloy not found")
    result = []
    for el in alloy.elements:
        row = db.execute(
            alloy_element_association.select().where(
                alloy_element_association.c.alloy_id == alloy_id,
                alloy_element_association.c.element_id == el.id,
            )
        ).first()
        if row:
            result.append({"element_id": el.id, "symbol": el.symbol,
                           "percentage": float(row.percentage)})
    return result


@router.get("/alloys/{alloy_id}")
async def get_alloy_by_id(alloy_id: int, db: Session = Depends(get_db),
                           _: Optional[Person] = Depends(get_current_user_optional)):
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        raise HTTPException(status_code=404, detail="Alloy not found")
    return alloy


@router.post("/alloys/", status_code=201)
async def create_alloy(alloy: AlloyCreateSchema,
                        current_user: Person = Depends(require_researcher),
                        db: Session = Depends(get_db)):
    a = Alloy(
        _prop_value=alloy.prop_value,
        temperature=alloy.temperature,
        category=alloy.category,
        rolling_type=alloy.rolling_type,
        patent_id=alloy.patent_id,
        created_by_id=current_user.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "category": a.category}


@router.put("/alloys/{alloy_id}")
async def update_alloy(alloy_id: int, data: AlloyUpdateSchema,
                        current_user: Person = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    a = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alloy not found")
    if not is_admin(current_user) and a.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not creator of this alloy")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/alloys/{alloy_id}")
async def delete_alloy(alloy_id: int,
                        current_user: Person = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    a = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alloy not found")
    if not is_admin(current_user) and a.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not creator of this alloy")
    db.delete(a)
    db.commit()
    return {"message": "Alloy deleted"}


@router.post("/alloys/{alloy_id}/elements/{element_id}", status_code=201)
async def add_element_to_alloy(alloy_id: int, element_id: int, percentage: float,
                                _: Person = Depends(require_researcher),
                                db: Session = Depends(get_db)):
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        raise HTTPException(status_code=404, detail="Alloy not found")
    el = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not el:
        raise HTTPException(status_code=404, detail="Element not found")
    existing = db.execute(
        alloy_element_association.select().where(
            alloy_element_association.c.alloy_id == alloy_id,
            alloy_element_association.c.element_id == element_id,
        )
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Element already in alloy")
    db.execute(alloy_element_association.insert().values(
        alloy_id=alloy_id, element_id=element_id, percentage=percentage))
    db.commit()
    return {"message": "Element added"}


@router.delete("/alloys/{alloy_id}/elements/{element_id}")
async def remove_element_from_alloy(alloy_id: int, element_id: int,
                                     _: Person = Depends(require_researcher),
                                     db: Session = Depends(get_db)):
    existing = db.execute(
        alloy_element_association.select().where(
            alloy_element_association.c.alloy_id == alloy_id,
            alloy_element_association.c.element_id == element_id,
        )
    ).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Association not found")
    db.execute(alloy_element_association.delete().where(
        alloy_element_association.c.alloy_id == alloy_id,
        alloy_element_association.c.element_id == element_id,
    ))
    db.commit()
    return {"message": "Element removed"}


# --- PREDICTIONS ---

@router.get("/predictions/")
async def get_predictions(current_user: Person = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    if is_admin(current_user):
        return db.query(Prediction).all()
    return db.query(Prediction).filter(Prediction.person_id == current_user.id).all()


@router.get("/predictions/person/{person_id}")
async def get_predictions_by_person(person_id: int,
                                     current_user: Person = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(Prediction).filter(Prediction.person_id == person_id).all()


@router.get("/predictions/element/{element_id}")
async def get_predictions_by_element(element_id: int,
                                      current_user: Person = Depends(get_current_user),
                                      db: Session = Depends(get_db)):
    return db.query(Prediction).join(
        prediction_element_association,
        Prediction.id == prediction_element_association.c.prediction_id
    ).filter(prediction_element_association.c.element_id == element_id).all()


@router.get("/predictions/model/{model_id}")
async def get_predictions_by_model(model_id: int,
                                    current_user: Person = Depends(get_current_user),
                                    db: Session = Depends(get_db)):
    return db.query(Prediction).filter(Prediction.ml_model_id == model_id).all()


@router.get("/predictions/{prediction_id}/elements")
async def get_prediction_elements(prediction_id: int,
                                   current_user: Person = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    result = []
    for el in pred.elements:
        row = db.execute(
            prediction_element_association.select().where(
                prediction_element_association.c.prediction_id == prediction_id,
                prediction_element_association.c.element_id == el.id,
            )
        ).first()
        if row:
            result.append({"element_id": el.id, "symbol": el.symbol,
                           "percentage": float(row.percentage)})
    return result


@router.get("/predictions/{prediction_id}")
async def get_prediction_by_id(prediction_id: int,
                                current_user: Person = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not is_admin(current_user) and pred.person_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own predictions")
    return pred


@router.post("/predictions/", status_code=201)
async def create_prediction(data: PredictionCreateSchema,
                             current_user: Person = Depends(require_researcher),
                             db: Session = Depends(get_db)):
    p = Prediction(
        _prop_value=data.prop_value,
        temperature=data.temperature,
        category=data.category,
        ml_model_id=data.ml_model_id,
        rolling_type=data.rolling_type,
        person_id=current_user.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "category": p.category}


@router.put("/predictions/{prediction_id}")
async def update_prediction(prediction_id: int, data: PredictionUpdateSchema,
                             current_user: Person = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not is_admin(current_user) and pred.person_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(pred, k, v)
    db.commit()
    db.refresh(pred)
    return pred


@router.delete("/predictions/{prediction_id}")
async def delete_prediction(prediction_id: int,
                             current_user: Person = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not is_admin(current_user) and pred.person_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.delete(pred)
    db.commit()
    return {"message": "Prediction deleted"}


@router.post("/predictions/{prediction_id}/elements/{element_id}", status_code=201)
async def add_element_to_prediction(prediction_id: int, element_id: int, percentage: float,
                                     current_user: Person = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not is_admin(current_user) and pred.person_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    el = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not el:
        raise HTTPException(status_code=404, detail="Element not found")
    db.execute(prediction_element_association.insert().values(
        prediction_id=prediction_id, element_id=element_id, percentage=percentage))
    db.commit()
    return {"message": "Element added to prediction"}


@router.delete("/predictions/{prediction_id}/elements/{element_id}")
async def remove_element_from_prediction(prediction_id: int, element_id: int,
                                          current_user: Person = Depends(get_current_user),
                                          db: Session = Depends(get_db)):
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not is_admin(current_user) and pred.person_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    db.execute(prediction_element_association.delete().where(
        prediction_element_association.c.prediction_id == prediction_id,
        prediction_element_association.c.element_id == element_id,
    ))
    db.commit()
    return {"message": "Element removed from prediction"}


# --- ORGANIZATIONS ---

@router.get("/organizations/")
async def get_organizations(_: Person = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    return db.query(Organization).all()


@router.get("/organizations/{org_id}")
async def get_organization_by_id(org_id: int, _: Person = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/organizations/", status_code=201)
async def create_organization(org: OrganizationCreateSchema,
                               _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    o = Organization(**org.dict())
    db.add(o)
    db.commit()
    db.refresh(o)
    return {"id": o.id, "message": "Organization created successfully"}


@router.put("/organizations/{org_id}")
async def update_organization(org_id: int, data: OrganizationUpdateSchema,
                               _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(org, k, v)
    db.commit()
    db.refresh(org)
    return org


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: int, _: Person = Depends(require_admin),
                               db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    db.delete(org)
    db.commit()
    return {"message": "Organization deleted successfully"}


# --- ROLES ---

@router.get("/roles/")
async def get_roles(_: Person = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Role).all()


@router.get("/roles/{role_id}")
async def get_role_by_id(role_id: int, _: Person = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post("/roles/", status_code=201)
async def create_role(role: RoleCreateSchema, _: Person = Depends(require_admin),
                       db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.name == role.name).first():
        raise HTTPException(status_code=409, detail="Role already exists")
    r = Role(name=role.name, description=role.description)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"id": r.id, "name": r.name}


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, _: Person = Depends(require_admin),
                       db: Session = Depends(get_db)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(role)
    db.commit()
    return {"message": "Role deleted"}


# --- MODELS ---

@router.get("/models/")
async def get_models(_: Person = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Model).all()


@router.get("/models/{model_id}")
async def get_model_by_id(model_id: int, _: Person = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return m


@router.post("/models/", status_code=201)
async def create_model(model: ModelCreateSchema, _: Person = Depends(require_admin),
                        db: Session = Depends(get_db)):
    if db.query(Model).filter(Model.name == model.name).first():
        raise HTTPException(status_code=409, detail="Model already exists")
    m = Model(name=model.name, description=model.description)
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"id": m.id, "name": m.name}


@router.delete("/models/{model_id}")
async def delete_model(model_id: int, _: Person = Depends(require_admin),
                        db: Session = Depends(get_db)):
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    db.delete(m)
    db.commit()
    return {"message": "Model deleted"}


# --- ADMIN ---

@router.post("/admin/grant_role", status_code=200)
async def grant_role_to_organization(payload: GrantRoleSchema = Body(...),
                                      _: Person = Depends(require_admin),
                                      db: Session = Depends(get_db)):
    persons = db.query(Person).filter(Person.organization_id == payload.organization_id).all()
    if not persons:
        raise HTTPException(status_code=404, detail="No persons found for this organization")
    updated = 0
    for p in persons:
        if p.role_id != payload.role_id:
            p.role_id = payload.role_id
            updated += 1
    db.commit()
    return {"message": "Role granted successfully", "updated": updated,
            "organization_id": payload.organization_id, "role_id": payload.role_id}


# --- ML ---

@router.post("/ml/predict", status_code=200)
async def ml_predict(payload: MLPredictRequestSchema,
                      db: Session = Depends(get_db),
                      _: Optional[Person] = Depends(get_current_user_optional)):
    """Заглушка ML-предсказания для тестов"""
    all_elements = db.query(ChemicalElement).all()
    id_to_symbol = {e.id: e.symbol.lower() for e in all_elements}
    composition = {}
    for item in payload.elements:
        sym = id_to_symbol.get(item.element_id)
        if sym:
            composition[sym] = item.percentage
    # Простая заглушка вместо реальной ML-модели
    prop_value = sum(composition.values()) * 10.0 if composition else 0.0
    return {"prop_value": prop_value}


@router.post("/ml/find-similar", status_code=200)
async def find_similar_alloys(payload: FindSimilarRequestSchema,
                               db: Session = Depends(get_db),
                               _: Optional[Person] = Depends(get_current_user_optional)):
    from math import sqrt
    alloys = db.query(Alloy).limit(1000).all()
    results = []
    for alloy in alloys:
        alloy_comp = {}
        for el in alloy.elements:
            row = db.execute(
                alloy_element_association.select().where(
                    alloy_element_association.c.alloy_id == alloy.id,
                    alloy_element_association.c.element_id == el.id,
                )
            ).first()
            if row:
                alloy_comp[el.symbol] = float(row.percentage)
        all_symbols = set(payload.composition.keys()) | set(alloy_comp.keys())
        dist = sqrt(sum((payload.composition.get(s, 0) - alloy_comp.get(s, 0)) ** 2
                        for s in all_symbols))
        results.append({
            "alloy_id": alloy.id,
            "patent_name": alloy.patent.patent_name if alloy.patent else None,
            "similarity": round(max(0, 100 - dist), 2),
            "composition": alloy_comp,
        })
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return {"similar_alloys": results[:payload.limit]}


app.include_router(router)


# =========================================================
#  TEST STATE & FIXTURES
# =========================================================

class TestData:
    admin_token: Optional[str] = None
    admin_id: Optional[int] = None
    admin_refresh_token: Optional[str] = None
    researcher_token: Optional[str] = None
    researcher_id: Optional[int] = None
    researcher_refresh_token: Optional[str] = None
    user_token: Optional[str] = None
    user_id: Optional[int] = None
    user_refresh_token: Optional[str] = None
    patent_id: Optional[int] = None
    alloy_id: Optional[int] = None
    prediction_id: Optional[int] = None
    element_id: Optional[int] = None
    organization_id: Optional[int] = None


test_data = TestData()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Роли
        admin_role = Role(name="admin", description="Администратор")
        researcher_role = Role(name="researcher", description="Исследователь")
        db.add_all([admin_role, researcher_role])
        db.flush()

        # Организация
        org = Organization(name="Тестовая организация")
        db.add(org)
        db.flush()
        test_data.organization_id = org.id

        # Элементы
        fe = ChemicalElement(name="Железо", atomic_number=26, symbol="Fe")
        db.add_all([
            fe,
            ChemicalElement(name="Углерод", atomic_number=6, symbol="C"),
            ChemicalElement(name="Хром", atomic_number=24, symbol="Cr"),
            ChemicalElement(name="Никель", atomic_number=28, symbol="Ni"),
            ChemicalElement(name="Молибден", atomic_number=42, symbol="Mo"),
        ])
        db.flush()
        test_data.element_id = fe.id

        # ML-модели
        db.add_all([
            Model(name="Random Forest", description="RF model"),
            Model(name="Gradient Boosting", description="GB model"),
        ])
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================
#  TESTS
# =========================================================

class TestAuthRoutes:

    def test_root_redirect(self, client):
        response = client.get("/api/", follow_redirects=False)
        assert response.status_code == 307

    def test_register_user(self, client):
        response = client.post("/api/persons/", json={
            "first_name": "Обычный", "last_name": "Пользователь",
            "email": "user@test.com", "role_id": 2,
            "login": "testuser", "password": "user123",
        })
        assert response.status_code == 201
        test_data.user_id = response.json()["id"]

    def test_register_researcher(self, client):
        response = client.post("/api/persons/", json={
            "first_name": "Исследователь", "last_name": "Тестов",
            "email": "res@test.com", "role_id": 2,
            "login": "researcher", "password": "res123",
        })
        assert response.status_code == 201
        test_data.researcher_id = response.json()["id"]

    def test_register_admin(self, client):
        response = client.post("/api/persons/", json={
            "first_name": "Администратор", "last_name": "Системы",
            "email": "admin@test.com", "role_id": 1,
            "login": "admin", "password": "admin123",
        })
        assert response.status_code == 201
        test_data.admin_id = response.json()["id"]

    def test_register_duplicate_login(self, client):
        response = client.post("/api/persons/", json={
            "first_name": "X", "last_name": "Y", "email": "x@test.com",
            "role_id": 2, "login": "testuser", "password": "pass",
        })
        assert response.status_code == 409

    def test_login_user(self, client):
        response = client.post("/api/auth/login", json={
            "login": "testuser", "password": "user123", "device_name": "Test Browser",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
        test_data.user_token = response.json()["access_token"]
        test_data.user_refresh_token = response.json()["refresh_token"]

    def test_login_researcher(self, client):
        response = client.post("/api/auth/login", json={
            "login": "researcher", "password": "res123", "device_name": "Test Browser",
        })
        assert response.status_code == 200
        test_data.researcher_token = response.json()["access_token"]
        test_data.researcher_refresh_token = response.json()["refresh_token"]

    def test_login_admin(self, client):
        response = client.post("/api/auth/login", json={
            "login": "admin", "password": "admin123", "device_name": "Test Browser",
        })
        assert response.status_code == 200
        test_data.admin_token = response.json()["access_token"]
        test_data.admin_refresh_token = response.json()["refresh_token"]

    def test_login_invalid_credentials(self, client):
        response = client.post("/api/auth/login", json={
            "login": "wronguser", "password": "wrongpass",
        })
        assert response.status_code == 401

    def test_refresh_token(self, client):
        # Нужен свежий токен — логинимся ещё раз
        login_resp = client.post("/api/auth/login", json={
            "login": "researcher", "password": "res123",
        })
        fresh_refresh = login_resp.json()["refresh_token"]
        response = client.post("/api/auth/refresh", json={"refresh_token": fresh_refresh})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_invalid_token(self, client):
        response = client.post("/api/auth/refresh", json={"refresh_token": "not-a-valid-token"})
        assert response.status_code == 401

    def test_logout(self, client):
        response = client.post("/api/auth/logout", json={
            "refresh_token": test_data.user_refresh_token,
        })
        assert response.status_code == 200

    def test_logout_invalid_token(self, client):
        response = client.post("/api/auth/logout", json={"refresh_token": "invalid"})
        assert response.status_code == 404


class TestChemicalElementRoutes:

    def test_get_all_elements_public(self, client):
        response = client.get("/api/elements/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) >= 5

    def test_get_element_by_id(self, client):
        response = client.get(f"/api/elements/{test_data.element_id}")
        assert response.status_code == 200
        assert "symbol" in response.json()

    def test_get_element_by_id_not_found(self, client):
        response = client.get("/api/elements/99999")
        assert response.status_code == 404

    def test_get_element_by_symbol(self, client):
        response = client.get("/api/elements/symbol/Fe")
        assert response.status_code == 200
        assert response.json()["symbol"] == "Fe"

    def test_get_element_by_symbol_not_found(self, client):
        response = client.get("/api/elements/symbol/XX")
        assert response.status_code == 404

    def test_create_element_unauthorized(self, client):
        response = client.post("/api/elements/", json={
            "name": "Тест", "atomic_number": 999, "symbol": "Ts",
        })
        assert response.status_code == 401

    def test_create_element_admin_success(self, client):
        response = client.post(
            "/api/elements/",
            json={"name": "Тестиум", "atomic_number": 998, "symbol": "Tu"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 201

    def test_create_element_duplicate_symbol(self, client):
        response = client.post(
            "/api/elements/",
            json={"name": "ДублФе", "atomic_number": 997, "symbol": "Fe"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 409


class TestPatentRoutes:

    def test_get_all_patents_public(self, client):
        response = client.get("/api/patents/")
        assert response.status_code == 200

    def test_get_patent_by_id_not_found(self, client):
        response = client.get("/api/patents/99999")
        assert response.status_code == 404

    def test_get_patent_by_number_not_found(self, client):
        response = client.get("/api/patents/number/NONEXISTENT")
        assert response.status_code == 404

    def test_create_patent_unauthorized(self, client):
        response = client.post("/api/patents/", json={
            "patent_number": "TEST001", "patent_name": "Test Patent",
        })
        assert response.status_code == 401

    def test_create_patent_researcher_success(self, client):
        response = client.post(
            "/api/patents/",
            json={
                "patent_number": "RU2024001",
                "patent_name": "Test Patent Researcher",
                "country": "RU",
                "ipc_code": "C22C38/00",
            },
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201
        test_data.patent_id = response.json()["id"]

    def test_get_patent_by_id_after_create(self, client):
        response = client.get(f"/api/patents/{test_data.patent_id}")
        assert response.status_code == 200
        assert response.json()["patent_number"] == "RU2024001"

    def test_get_patent_by_number_after_create(self, client):
        response = client.get("/api/patents/number/RU2024001")
        assert response.status_code == 200

    def test_update_patent_unauthorized(self, client):
        response = client.put(f"/api/patents/{test_data.patent_id}",
                              json={"patent_name": "Updated"})
        assert response.status_code == 401

    def test_update_patent_admin_success(self, client):
        response = client.put(
            f"/api/patents/{test_data.patent_id}",
            json={"patent_name": "Updated By Admin"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_delete_patent_unauthorized(self, client):
        response = client.delete(f"/api/patents/{test_data.patent_id}")
        assert response.status_code == 401

    def test_delete_patent_admin_success(self, client):
        create_resp = client.post(
            "/api/patents/",
            json={"patent_number": "RU2024999", "patent_name": "ToDelete"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        patent_to_delete = create_resp.json()["id"]
        response = client.delete(
            f"/api/patents/{patent_to_delete}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestPatentWithAuthorsRoutes:

    def test_create_patent_with_authors(self, client):
        response = client.post(
            "/api/patents/with-authors/",
            json={
                "patent_number": "RU2024099",
                "patent_name": "Patent With Authors",
                "country": "RU",
                "ipc_code": "C22C38/00",
                "authors": [
                    {"author_name": "Автор1", "author_order": 1},
                    {"author_name": "Автор2", "author_order": 2},
                ],
            },
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201

    def test_get_patent_authors(self, client):
        response = client.get(f"/api/patents/{test_data.patent_id}/authors")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_patent_author(self, client):
        response = client.post(
            f"/api/patents/{test_data.patent_id}/authors?author_name=НовыйАвтор&author_order=99",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201


class TestAlloyRoutes:

    def test_get_all_alloys_public(self, client):
        response = client.get("/api/alloys/")
        assert response.status_code == 200

    def test_get_alloy_by_id_not_found(self, client):
        response = client.get("/api/alloys/99999")
        assert response.status_code == 404

    def test_create_alloy_unauthorized(self, client):
        response = client.post("/api/alloys/", json={
            "category": "steel", "rolling_type": "hot",
            "patent_id": test_data.patent_id,
        })
        assert response.status_code == 401

    def test_create_alloy_researcher_success(self, client):
        response = client.post(
            "/api/alloys/",
            json={
                "prop_value": 850.5, "temperature": 950.0,
                "category": "steel", "rolling_type": "hot",
                "patent_id": test_data.patent_id,
            },
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201
        test_data.alloy_id = response.json()["id"]

    def test_get_alloys_by_patent(self, client):
        response = client.get(f"/api/alloys/patent/{test_data.patent_id}")
        assert response.status_code == 200

    def test_search_alloys_by_category(self, client):
        response = client.get("/api/alloys/category/steel")
        assert response.status_code == 200

    def test_update_alloy_unauthorized(self, client):
        response = client.put(f"/api/alloys/{test_data.alloy_id}",
                              json={"prop_value": 900.0})
        assert response.status_code == 401

    def test_delete_alloy_unauthorized(self, client):
        response = client.delete(f"/api/alloys/{test_data.alloy_id}")
        assert response.status_code == 401


class TestAlloyElementRoutes:

    def test_get_alloy_elements(self, client):
        response = client.get(f"/api/alloys/{test_data.alloy_id}/elements")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_element_to_alloy_unauthorized(self, client):
        response = client.post(
            f"/api/alloys/{test_data.alloy_id}/elements/{test_data.element_id}?percentage=90.0"
        )
        assert response.status_code == 401

    def test_add_element_to_alloy_authorized(self, client):
        response = client.post(
            f"/api/alloys/{test_data.alloy_id}/elements/{test_data.element_id}?percentage=90.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201

    def test_add_element_to_alloy_duplicate(self, client):
        response = client.post(
            f"/api/alloys/{test_data.alloy_id}/elements/{test_data.element_id}?percentage=90.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 409

    def test_remove_element_from_alloy_authorized(self, client):
        response = client.delete(
            f"/api/alloys/{test_data.alloy_id}/elements/{test_data.element_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200


class TestPredictionRoutes:

    def test_get_predictions_unauthorized(self, client):
        response = client.get("/api/predictions/")
        assert response.status_code == 401

    def test_create_prediction_unauthorized(self, client):
        response = client.post("/api/predictions/", json={
            "prop_value": 850.5, "category": "steel",
            "ml_model_id": 1, "rolling_type": "hot",
        })
        assert response.status_code == 401

    def test_create_prediction_researcher_success(self, client):
        response = client.post(
            "/api/predictions/",
            json={
                "prop_value": 850.5, "temperature": 950.0,
                "category": "steel", "ml_model_id": 1, "rolling_type": "hot",
            },
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201
        test_data.prediction_id = response.json()["id"]

    def test_get_my_predictions(self, client):
        response = client.get(
            "/api/predictions/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_prediction_by_id(self, client):
        response = client.get(
            f"/api/predictions/{test_data.prediction_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_predictions_by_person(self, client):
        response = client.get(
            f"/api/predictions/person/{test_data.researcher_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_predictions_by_element(self, client):
        response = client.get(
            f"/api/predictions/element/{test_data.element_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_predictions_by_model(self, client):
        response = client.get(
            "/api/predictions/model/1",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_update_prediction_unauthorized(self, client):
        response = client.put(
            f"/api/predictions/{test_data.prediction_id}",
            json={"prop_value": 900.0},
        )
        assert response.status_code == 401

    def test_delete_prediction_unauthorized(self, client):
        response = client.delete(f"/api/predictions/{test_data.prediction_id}")
        assert response.status_code == 401


class TestPredictionElementRoutes:

    def test_get_prediction_elements(self, client):
        response = client.get(
            f"/api/predictions/{test_data.prediction_id}/elements",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_add_element_to_prediction(self, client):
        response = client.post(
            f"/api/predictions/{test_data.prediction_id}/elements/{test_data.element_id}?percentage=90.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 201

    def test_remove_element_from_prediction(self, client):
        response = client.delete(
            f"/api/predictions/{test_data.prediction_id}/elements/{test_data.element_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200


class TestOrganizationRoutes:

    def test_get_organizations_unauthorized(self, client):
        response = client.get("/api/organizations/")
        assert response.status_code == 401

    def test_get_organizations_authorized(self, client):
        response = client.get(
            "/api/organizations/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_organization_by_id(self, client):
        response = client.get(
            f"/api/organizations/{test_data.organization_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_create_organization_unauthorized(self, client):
        response = client.post("/api/organizations/", json={"name": "Новая организация"})
        assert response.status_code == 401

    def test_create_organization_admin_success(self, client):
        response = client.post(
            "/api/organizations/",
            json={"name": "Новая организация от админа"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 201

    def test_update_organization_admin_success(self, client):
        response = client.put(
            f"/api/organizations/{test_data.organization_id}",
            json={"name": "Обновленное название"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_delete_organization_admin_success(self, client):
        create_resp = client.post(
            "/api/organizations/",
            json={"name": "Организация для удаления"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        org_to_delete = create_resp.json()["id"]
        response = client.delete(
            f"/api/organizations/{org_to_delete}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestRoleRoutes:

    def test_get_roles_unauthorized(self, client):
        response = client.get("/api/roles/")
        assert response.status_code == 401

    def test_get_roles_authorized(self, client):
        response = client.get(
            "/api/roles/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_role_by_id(self, client):
        response = client.get(
            "/api/roles/1",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_create_role_unauthorized(self, client):
        response = client.post("/api/roles/", json={"name": "new_role"})
        assert response.status_code == 401

    def test_create_role_admin_success(self, client):
        response = client.post(
            "/api/roles/",
            json={"name": "new_role", "description": "Новая роль"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 201

    def test_delete_role_admin_success(self, client):
        create_resp = client.post(
            "/api/roles/",
            json={"name": "temp_role", "description": "Временная"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        role_to_delete = create_resp.json()["id"]
        response = client.delete(
            f"/api/roles/{role_to_delete}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestModelRoutes:

    def test_get_models_unauthorized(self, client):
        response = client.get("/api/models/")
        assert response.status_code == 401

    def test_get_models_authorized(self, client):
        response = client.get(
            "/api/models/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_get_model_by_id(self, client):
        response = client.get(
            "/api/models/1",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_create_model_unauthorized(self, client):
        response = client.post("/api/models/", json={"name": "New Model"})
        assert response.status_code == 401

    def test_create_model_admin_success(self, client):
        response = client.post(
            "/api/models/",
            json={"name": "New ML Model", "description": "Test"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 201

    def test_delete_model_admin_success(self, client):
        create_resp = client.post(
            "/api/models/",
            json={"name": "Temp Model", "description": "Temporary"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        model_to_delete = create_resp.json()["id"]
        response = client.delete(
            f"/api/models/{model_to_delete}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestPersonRoutes:

    def test_get_persons_unauthorized(self, client):
        response = client.get("/api/persons/")
        assert response.status_code == 401

    def test_get_persons_researcher_forbidden(self, client):
        response = client.get(
            "/api/persons/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_get_persons_admin_success(self, client):
        response = client.get(
            "/api/persons/",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_get_person_by_id_admin(self, client):
        response = client.get(
            f"/api/persons/{test_data.user_id}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_get_person_by_login_admin(self, client):
        response = client.get(
            "/api/persons/login/testuser",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_get_person_by_email_admin(self, client):
        response = client.get(
            "/api/persons/email/user@test.com",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_get_persons_by_role_admin(self, client):
        response = client.get(
            "/api/persons/role/2",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_update_person_admin(self, client):
        response = client.put(
            f"/api/persons/{test_data.user_id}",
            json={"first_name": "ОбновленноеИмя"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_delete_person_admin(self, client):
        create_resp = client.post("/api/persons/", json={
            "first_name": "Temp", "last_name": "User",
            "email": "temp@test.com", "role_id": 2,
            "login": "tempuser", "password": "pass123",
        })
        temp_user_id = create_resp.json()["id"]
        response = client.delete(
            f"/api/persons/{temp_user_id}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestDeviceRoutes:

    def test_get_user_devices_admin(self, client):
        response = client.get(
            f"/api/persons/{test_data.user_id}/devices",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestAdminRoutes:

    def test_grant_role_unauthorized(self, client):
        response = client.post("/api/admin/grant_role", json={
            "organization_id": test_data.organization_id, "role_id": 2,
        })
        assert response.status_code == 401

    def test_grant_role_researcher_forbidden(self, client):
        response = client.post(
            "/api/admin/grant_role",
            json={"organization_id": test_data.organization_id, "role_id": 2},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_grant_role_admin_no_persons_in_org(self, client):
        # Организация без пользователей → 404
        create_org = client.post(
            "/api/organizations/",
            json={"name": "Пустая организация"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        empty_org_id = create_org.json()["id"]
        response = client.post(
            "/api/admin/grant_role",
            json={"organization_id": empty_org_id, "role_id": 2},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_grant_role_admin_success(self, client):
        # Добавляем пользователя в организацию
        db = TestingSessionLocal()
        try:
            person = db.query(Person).filter(Person.login == "testuser").first()
            person.organization_id = test_data.organization_id
            db.commit()
        finally:
            db.close()

        response = client.post(
            "/api/admin/grant_role",
            json={"organization_id": test_data.organization_id, "role_id": 2},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200


class TestMLRoutes:

    def test_ml_predict_public(self, client):
        response = client.post("/api/ml/predict", json={
            "ml_model_id": 1,
            "category": "steel",
            "rolling_type": "hot",
            "elements": [{"element_id": test_data.element_id, "percentage": 100.0}],
        })
        assert response.status_code == 200
        assert "prop_value" in response.json()

    def test_ml_predict_empty_elements(self, client):
        response = client.post("/api/ml/predict", json={
            "ml_model_id": 1,
            "category": "steel",
            "rolling_type": "hot",
            "temperature": 950.0,
            "elements": [],
        })
        assert response.status_code == 200

    def test_find_similar_public(self, client):
        response = client.post("/api/ml/find-similar", json={
            "composition": {"Fe": 95.5, "C": 0.5, "Cr": 4.0},
            "limit": 5,
        })
        assert response.status_code == 200
        assert "similar_alloys" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# =========================================================
#  ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ — полное покрытие
# =========================================================


class TestAlloyOwnership:
    """Права доступа: чужой/свой сплав"""

    def test_update_own_alloy_researcher(self, client):
        """Исследователь может обновить СВОЙ сплав"""
        # Создаём сплав от имени исследователя
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 100.0, "category": "steel",
                  "rolling_type": "hot", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        alloy_id = create.json()["id"]

        response = client.put(
            f"/api/alloys/{alloy_id}",
            json={"category": "aluminium"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_delete_own_alloy_researcher(self, client):
        """Исследователь может удалить СВОЙ сплав"""
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 200.0, "category": "steel",
                  "rolling_type": "cold", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        alloy_id = create.json()["id"]

        response = client.delete(
            f"/api/alloys/{alloy_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_update_foreign_alloy_researcher_forbidden(self, client):
        """Исследователь НЕ может обновить ЧУЖОЙ сплав — 403"""
        # Создаём сплав от имени ДРУГОГО пользователя (admin)
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 300.0, "category": "steel",
                  "rolling_type": "hot", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        foreign_alloy_id = create.json()["id"]

        # Попытка обновления чужого сплава исследователем
        response = client.put(
            f"/api/alloys/{foreign_alloy_id}",
            json={"category": "titanium"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_delete_foreign_alloy_researcher_forbidden(self, client):
        """Исследователь НЕ может удалить ЧУЖОЙ сплав — 403"""
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 400.0, "category": "steel",
                  "rolling_type": "hot", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        foreign_alloy_id = create.json()["id"]

        response = client.delete(
            f"/api/alloys/{foreign_alloy_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_update_any_alloy(self, client):
        """Админ может обновить ЛЮБОЙ сплав"""
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 500.0, "category": "steel",
                  "rolling_type": "hot", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        alloy_id = create.json()["id"]

        response = client.put(
            f"/api/alloys/{alloy_id}",
            json={"category": "composite"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_admin_can_delete_any_alloy(self, client):
        """Админ может удалить ЛЮБОЙ сплав"""
        create = client.post(
            "/api/alloys/",
            json={"prop_value": 600.0, "category": "steel",
                  "rolling_type": "hot", "patent_id": test_data.patent_id},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        alloy_id = create.json()["id"]

        response = client.delete(
            f"/api/alloys/{alloy_id}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_update_nonexistent_alloy(self, client):
        """Обновление несуществующего сплава — 404"""
        response = client.put(
            "/api/alloys/99999",
            json={"category": "unknown"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_alloy(self, client):
        """Удаление несуществующего сплава — 404"""
        response = client.delete(
            "/api/alloys/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404


class TestPredictionOwnership:
    """Права доступа: чужой/свой прогноз"""

    def test_update_own_prediction_researcher(self, client):
        """Исследователь может обновить СВОЙ прогноз"""
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 111.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        pred_id = create.json()["id"]

        response = client.put(
            f"/api/predictions/{pred_id}",
            json={"category": "aluminium"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_delete_own_prediction_researcher(self, client):
        """Исследователь может удалить СВОЙ прогноз"""
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 222.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "cold"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        pred_id = create.json()["id"]

        response = client.delete(
            f"/api/predictions/{pred_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_update_foreign_prediction_forbidden(self, client):
        """Исследователь НЕ может обновить ЧУЖОЙ прогноз — 403"""
        # Создаём прогноз вторым исследователем (используем admin как другого юзера)
        # Сначала создадим нового пользователя-исследователя
        reg = client.post("/api/persons/", json={
            "first_name": "Второй", "last_name": "Исследователь",
            "email": "res2@test.com", "role_id": 2,
            "login": "researcher2", "password": "res2pass",
        })
        assert reg.status_code == 201

        login = client.post("/api/auth/login", json={
            "login": "researcher2", "password": "res2pass",
        })
        res2_token = login.json()["access_token"]

        # Создаём прогноз от второго исследователя
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 333.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {res2_token}"},
        )
        foreign_pred_id = create.json()["id"]

        # Первый исследователь пытается обновить чужой прогноз
        response = client.put(
            f"/api/predictions/{foreign_pred_id}",
            json={"category": "titanium"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_delete_foreign_prediction_forbidden(self, client):
        """Исследователь НЕ может удалить ЧУЖОЙ прогноз — 403"""
        # Используем прогноз, созданный researcher2 в предыдущем тесте
        # Создаём ещё один для надёжности
        login = client.post("/api/auth/login", json={
            "login": "researcher2", "password": "res2pass",
        })
        res2_token = login.json()["access_token"]

        create = client.post(
            "/api/predictions/",
            json={"prop_value": 444.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {res2_token}"},
        )
        foreign_pred_id = create.json()["id"]

        response = client.delete(
            f"/api/predictions/{foreign_pred_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_view_foreign_prediction_forbidden(self, client):
        """Исследователь НЕ может просмотреть ЧУЖОЙ прогноз — 403"""
        login = client.post("/api/auth/login", json={
            "login": "researcher2", "password": "res2pass",
        })
        res2_token = login.json()["access_token"]

        create = client.post(
            "/api/predictions/",
            json={"prop_value": 555.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {res2_token}"},
        )
        foreign_pred_id = create.json()["id"]

        response = client.get(
            f"/api/predictions/{foreign_pred_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_update_any_prediction(self, client):
        """Админ может обновить ЛЮБОЙ прогноз"""
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 666.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        pred_id = create.json()["id"]

        response = client.put(
            f"/api/predictions/{pred_id}",
            json={"category": "composite"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_admin_can_delete_any_prediction(self, client):
        """Админ может удалить ЛЮБОЙ прогноз"""
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 777.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        pred_id = create.json()["id"]

        response = client.delete(
            f"/api/predictions/{pred_id}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_admin_can_view_any_prediction(self, client):
        """Админ может просмотреть ЛЮБОЙ прогноз"""
        login = client.post("/api/auth/login", json={
            "login": "researcher2", "password": "res2pass",
        })
        res2_token = login.json()["access_token"]

        create = client.post(
            "/api/predictions/",
            json={"prop_value": 888.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {res2_token}"},
        )
        pred_id = create.json()["id"]

        response = client.get(
            f"/api/predictions/{pred_id}",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_update_nonexistent_prediction(self, client):
        """Обновление несуществующего прогноза — 404"""
        response = client.put(
            "/api/predictions/99999",
            json={"category": "unknown"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_prediction(self, client):
        """Удаление несуществующего прогноза — 404"""
        response = client.delete(
            "/api/predictions/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_get_nonexistent_prediction(self, client):
        """Получение несуществующего прогноза — 404"""
        response = client.get(
            "/api/predictions/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404


class TestPagination:
    """Тесты пагинации — skip и limit"""

    def test_alloys_skip(self, client):
        """GET /api/alloys/?skip=100 — пустой список при большом skip"""
        response = client.get("/api/alloys/?skip=100000&limit=10")
        assert response.status_code == 200
        assert response.json() == []

    def test_alloys_limit(self, client):
        """GET /api/alloys/?limit=1 — возвращает не больше одного"""
        # Создаём несколько сплавов
        for i in range(3):
            client.post(
                "/api/alloys/",
                json={"prop_value": float(i), "category": "pagtest",
                      "rolling_type": "hot", "patent_id": test_data.patent_id},
                headers={"Authorization": f"Bearer {test_data.researcher_token}"},
            )

        response = client.get("/api/alloys/?limit=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1

    def test_alloys_limit_zero(self, client):
        """GET /api/alloys/?limit=0 — пустой список"""
        response = client.get("/api/alloys/?limit=0")
        assert response.status_code == 200
        assert response.json() == []

    def test_predictions_admin_sees_all(self, client):
        """Админ получает все прогнозы, а не только свои"""
        response = client.get(
            "/api/predictions/",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200
        # Прогнозов должно быть больше одного (созданы разными пользователями)
        assert len(response.json()) >= 1

    def test_predictions_researcher_sees_only_own(self, client):
        """Исследователь видит только свои прогнозы"""
        response = client.get(
            "/api/predictions/",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        # Все прогнозы должны принадлежать этому исследователю
        for pred in data:
            assert pred["person_id"] == test_data.researcher_id


class TestPatentOwnership:
    """Права на редактирование патента: автор vs чужой"""

    def test_researcher_cannot_edit_others_patent(self, client):
        """Исследователь НЕ может редактировать патент, в котором он не автор"""
        # Создаём патент от admin (не добавляет researcher как автора)
        create = client.post(
            "/api/patents/",
            json={"patent_number": "OWN001", "patent_name": "Admins Patent"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        admin_patent_id = create.json()["id"]

        # researcher пытается обновить — должен получить 403
        response = client.put(
            f"/api/patents/{admin_patent_id}",
            json={"patent_name": "Hacked"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_admin_can_edit_any_patent(self, client):
        """Админ может редактировать любой патент"""
        create = client.post(
            "/api/patents/",
            json={"patent_number": "OWN002", "patent_name": "Researcher Patent"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        pat_id = create.json()["id"]

        response = client.put(
            f"/api/patents/{pat_id}",
            json={"patent_name": "Updated by Admin"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 200

    def test_update_nonexistent_patent(self, client):
        """Обновление несуществующего патента — 404"""
        response = client.put(
            "/api/patents/99999",
            json={"patent_name": "Ghost"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_patent(self, client):
        """Удаление несуществующего патента — 404"""
        response = client.delete(
            "/api/patents/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_create_duplicate_patent_number(self, client):
        """Создание патента с уже существующим номером — 409"""
        response = client.post(
            "/api/patents/",
            json={"patent_number": "RU2024001", "patent_name": "Дубль"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 409


class TestPersonEdgeCases:
    """Крайние случаи для пользователей"""

    def test_get_nonexistent_person_by_id(self, client):
        """Получение несуществующего пользователя — 404"""
        response = client.get(
            "/api/persons/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_get_nonexistent_person_by_login(self, client):
        """Получение по несуществующему логину — 404"""
        response = client.get(
            "/api/persons/login/nobody_exists",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_get_nonexistent_person_by_email(self, client):
        """Получение по несуществующему email — 404"""
        response = client.get(
            "/api/persons/email/nobody@nowhere.com",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_update_nonexistent_person(self, client):
        """Обновление несуществующего пользователя — 404"""
        response = client.put(
            "/api/persons/99999",
            json={"first_name": "Ghost"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_person(self, client):
        """Удаление несуществующего пользователя — 404"""
        response = client.delete(
            "/api/persons/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_register_with_invalid_role(self, client):
        """Регистрация с несуществующей ролью — 404"""
        response = client.post("/api/persons/", json={
            "first_name": "X", "last_name": "Y",
            "email": "invalid_role@test.com", "role_id": 9999,
            "login": "invalid_role_user", "password": "pass",
        })
        assert response.status_code == 404

    def test_deactivated_user_cannot_login(self, client):
        """Заблокированный пользователь не может войти"""
        # Создаём пользователя
        client.post("/api/persons/", json={
            "first_name": "Block", "last_name": "Me",
            "email": "blocked@test.com", "role_id": 2,
            "login": "blockeduser", "password": "pass123",
        })
        # Блокируем его через прямое изменение в БД
        db = TestingSessionLocal()
        try:
            from sqlalchemy import text
            db.execute(
                text("UPDATE person SET is_active = 0 WHERE login = 'blockeduser'")
            )
            db.commit()
        finally:
            db.close()

        # Попытка входа
        response = client.post("/api/auth/login", json={
            "login": "blockeduser", "password": "pass123",
        })
        assert response.status_code == 401


class TestOrganizationEdgeCases:
    """Крайние случаи для организаций"""

    def test_get_nonexistent_organization(self, client):
        """Получение несуществующей организации — 404"""
        response = client.get(
            "/api/organizations/99999",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_update_nonexistent_organization(self, client):
        """Обновление несуществующей организации — 404"""
        response = client.put(
            "/api/organizations/99999",
            json={"name": "Ghost Org"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_delete_nonexistent_organization(self, client):
        """Удаление несуществующей организации — 404"""
        response = client.delete(
            "/api/organizations/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_researcher_cannot_create_organization(self, client):
        """Исследователь не может создать организацию — 403"""
        response = client.post(
            "/api/organizations/",
            json={"name": "Researcher Org"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_researcher_cannot_update_organization(self, client):
        """Исследователь не может обновить организацию — 403"""
        response = client.put(
            f"/api/organizations/{test_data.organization_id}",
            json={"name": "Hacked Org"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_researcher_cannot_delete_organization(self, client):
        """Исследователь не может удалить организацию — 403"""
        response = client.delete(
            f"/api/organizations/{test_data.organization_id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403


class TestRoleEdgeCases:
    """Крайние случаи для ролей"""

    def test_get_nonexistent_role(self, client):
        """Получение несуществующей роли — 404"""
        response = client.get(
            "/api/roles/99999",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_create_duplicate_role(self, client):
        """Создание дублирующей роли — 409"""
        response = client.post(
            "/api/roles/",
            json={"name": "admin", "description": "Дубль"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 409

    def test_delete_nonexistent_role(self, client):
        """Удаление несуществующей роли — 404"""
        response = client.delete(
            "/api/roles/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_researcher_cannot_create_role(self, client):
        """Исследователь не может создать роль — 403"""
        response = client.post(
            "/api/roles/",
            json={"name": "superuser"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_researcher_cannot_delete_role(self, client):
        """Исследователь не может удалить роль — 403"""
        response = client.delete(
            "/api/roles/1",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403


class TestModelEdgeCases:
    """Крайние случаи для ML-моделей"""

    def test_get_nonexistent_model(self, client):
        """Получение несуществующей модели — 404"""
        response = client.get(
            "/api/models/99999",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_create_duplicate_model(self, client):
        """Создание модели с существующим именем — 409"""
        response = client.post(
            "/api/models/",
            json={"name": "Random Forest"},
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 409

    def test_delete_nonexistent_model(self, client):
        """Удаление несуществующей модели — 404"""
        response = client.delete(
            "/api/models/99999",
            headers={"Authorization": f"Bearer {test_data.admin_token}"},
        )
        assert response.status_code == 404

    def test_researcher_cannot_create_model(self, client):
        """Исследователь не может создать ML-модель — 403"""
        response = client.post(
            "/api/models/",
            json={"name": "My Secret Model"},
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403

    def test_researcher_cannot_delete_model(self, client):
        """Исследователь не может удалить ML-модель — 403"""
        response = client.delete(
            "/api/models/1",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403


class TestAlloyElementEdgeCases:
    """Крайние случаи для связей сплав-элемент"""

    def test_add_element_to_nonexistent_alloy(self, client):
        """Добавление элемента к несуществующему сплаву — 404"""
        response = client.post(
            f"/api/alloys/99999/elements/{test_data.element_id}?percentage=50.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_add_nonexistent_element_to_alloy(self, client):
        """Добавление несуществующего элемента к сплаву — 404"""
        response = client.post(
            f"/api/alloys/{test_data.alloy_id}/elements/99999?percentage=50.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_remove_nonexistent_element_from_alloy(self, client):
        """Удаление несвязанного элемента из сплава — 404"""
        # Берём элемент Cr (который не добавлен к alloy_id)
        cr = TestingSessionLocal().query(ChemicalElement).filter(
            ChemicalElement.symbol == "Cr"
        ).first()
        response = client.delete(
            f"/api/alloys/{test_data.alloy_id}/elements/{cr.id}",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_get_elements_of_nonexistent_alloy(self, client):
        """Получение элементов несуществующего сплава — 404"""
        response = client.get("/api/alloys/99999/elements")
        assert response.status_code == 404


class TestPredictionElementEdgeCases:
    """Крайние случаи для связей прогноз-элемент"""

    def test_add_element_to_nonexistent_prediction(self, client):
        """Добавление элемента к несуществующему прогнозу — 404"""
        response = client.post(
            f"/api/predictions/99999/elements/{test_data.element_id}?percentage=50.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_get_elements_of_nonexistent_prediction(self, client):
        """Получение элементов несуществующего прогноза — 404"""
        response = client.get(
            "/api/predictions/99999/elements",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 404

    def test_add_element_to_foreign_prediction_forbidden(self, client):
        """Добавление элемента к ЧУЖОМУ прогнозу — 403"""
        # Логинимся как researcher2
        login = client.post("/api/auth/login", json={
            "login": "researcher2", "password": "res2pass",
        })
        res2_token = login.json()["access_token"]

        # Создаём прогноз от researcher2
        create = client.post(
            "/api/predictions/",
            json={"prop_value": 999.0, "category": "steel",
                  "ml_model_id": 1, "rolling_type": "hot"},
            headers={"Authorization": f"Bearer {res2_token}"},
        )
        foreign_pred_id = create.json()["id"]

        # researcher1 пытается добавить элемент к чужому прогнозу
        response = client.post(
            f"/api/predictions/{foreign_pred_id}/elements/{test_data.element_id}?percentage=50.0",
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 403


class TestTokenEdgeCases:
    """Крайние случаи для токенов"""

    def test_expired_access_token_rejected(self, client):
        """Истёкший access токен — 401"""
        import jwt as _jwt
        from datetime import timedelta
        # Генерируем токен с истёкшим временем
        expired_payload = {
            "person_id": test_data.admin_id,
            "login": "admin",
            "exp": datetime.utcnow() - timedelta(minutes=1),
            "type": "access",
            "iat": datetime.utcnow() - timedelta(minutes=10),
        }
        expired_token = _jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = client.get(
            "/api/persons/",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_wrong_type_token_rejected(self, client):
        """Токен с type != access — 401"""
        import jwt as _jwt
        bad_payload = {
            "person_id": test_data.admin_id,
            "login": "admin",
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "type": "refresh",   # намеренно неверный тип
            "iat": datetime.utcnow(),
        }
        bad_token = _jwt.encode(bad_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = client.get(
            "/api/persons/",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert response.status_code == 401

    def test_malformed_token_rejected(self, client):
        """Мусор вместо токена — 401"""
        response = client.get(
            "/api/persons/",
            headers={"Authorization": "Bearer this.is.not.a.jwt"},
        )
        assert response.status_code == 401

    def test_used_refresh_token_after_logout_rejected(self, client):
        """Использование refresh-токена после logout — 401"""
        # Логинимся
        login_resp = client.post("/api/auth/login", json={
            "login": "researcher", "password": "res123",
        })
        rt = login_resp.json()["refresh_token"]

        # Выходим — токен отзывается
        client.post("/api/auth/logout", json={"refresh_token": rt})

        # Повторная попытка обновить токен
        response = client.post("/api/auth/refresh", json={"refresh_token": rt})
        assert response.status_code == 401


class TestMLEdgeCases:
    """Крайние случаи для ML-эндпоинтов"""

    def test_find_similar_empty_composition(self, client):
        """Поиск похожих с пустым составом"""
        response = client.post("/api/ml/find-similar", json={
            "composition": {},
            "limit": 5,
        })
        assert response.status_code == 200
        assert "similar_alloys" in response.json()

    def test_find_similar_limit_respected(self, client):
        """Результат не превышает limit"""
        response = client.post("/api/ml/find-similar", json={
            "composition": {"Fe": 100.0},
            "limit": 2,
        })
        assert response.status_code == 200
        assert len(response.json()["similar_alloys"]) <= 2

    def test_ml_predict_with_unknown_element_id(self, client):
        """ML-предсказание с несуществующим element_id — элемент игнорируется"""
        response = client.post("/api/ml/predict", json={
            "ml_model_id": 1,
            "category": "steel",
            "rolling_type": "hot",
            "elements": [{"element_id": 99999, "percentage": 100.0}],
        })
        # Несуществующий элемент просто пропускается, не 500
        assert response.status_code == 200
        assert response.json()["prop_value"] == 0.0

    def test_ml_predict_authorized_user(self, client):
        """ML-предсказание доступно авторизованному пользователю"""
        response = client.post(
            "/api/ml/predict",
            json={
                "ml_model_id": 1,
                "category": "steel",
                "rolling_type": "hot",
                "elements": [{"element_id": test_data.element_id, "percentage": 50.0}],
            },
            headers={"Authorization": f"Bearer {test_data.researcher_token}"},
        )
        assert response.status_code == 200

    def test_find_similar_sorted_by_similarity(self, client):
        """Похожие сплавы отсортированы по убыванию сходства"""
        response = client.post("/api/ml/find-similar", json={
            "composition": {"Fe": 90.0, "C": 10.0},
            "limit": 10,
        })
        assert response.status_code == 200
        results = response.json()["similar_alloys"]
        if len(results) > 1:
            similarities = [r["similarity"] for r in results]
            assert similarities == sorted(similarities, reverse=True)
