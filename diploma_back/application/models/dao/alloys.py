from sqlalchemy import Column, ForeignKey, Boolean, Integer, Numeric, String, Text, DateTime, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Ассоциативная таблица с процентным содержанием
alloy_element_association = Table(
    'alloy_element_association',
    Base.metadata,
    Column('alloy_id', Integer, ForeignKey('alloy.id'), primary_key=True),
    Column('element_id', Integer, ForeignKey('chemical_element.id'), primary_key=True),
    Column('percentage', Numeric(5, 3), nullable=False)
)

# Ассоциативная таблица для prediction-element
prediction_element_association = Table(
    'prediction_element_association',
    Base.metadata,
    Column('prediction_id', Integer, ForeignKey('prediction.id'), primary_key=True),
    Column('element_id', Integer, ForeignKey('chemical_element.id'), primary_key=True),
    Column('percentage', Numeric(5, 3), nullable=False)
)


class Alloy(Base):
    __tablename__ = "alloy"

    id = Column(Integer, primary_key=True)
    _prop_value = Column('prop_value', Numeric, nullable=True)
    temperature = Column(Numeric(10, 3), nullable=True)
    category = Column(String(100))
    rolling_type = Column(String(50))

    patent_id = Column(Integer, ForeignKey('patent.id'), nullable=False)
    patent = relationship('Patent', back_populates="alloys")

    elements = relationship('ChemicalElement',
                            secondary=alloy_element_association,
                            back_populates="alloys")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('person.id'), nullable=True)

    @hybrid_property
    def prop_value(self):
        return self._prop_value

    @prop_value.setter
    def prop_value(self, value):
        if value is not None and value < 0:
            self._prop_value = 0
        else:
            self._prop_value = value

    @prop_value.expression
    def prop_value(cls):
        return cls._prop_value

    def __repr__(self):
        return f"<Alloy(id={self.id}, prop_value={self.prop_value})>"


class PatentAuthor(Base):
    """Автор патента"""
    __tablename__ = "patent_author"

    id = Column(Integer, primary_key=True)
    patent_id = Column(Integer, ForeignKey('patent.id'), nullable=False)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=True)
    author_name = Column(String(200), nullable=False)
    author_order = Column(Integer, default=0)

    patent = relationship('Patent', back_populates='authors')
    person = relationship('Person', back_populates='patents_authored')

    __table_args__ = (
        UniqueConstraint('patent_id', 'author_order', name='uq_patent_author_order'),
    )


class Patent(Base):
    __tablename__ = "patent"

    id = Column(Integer, primary_key=True)

    # ОСНОВНАЯ ИНФОРМАЦИЯ
    patent_number = Column(String(50), nullable=False, unique=True)
    country = Column(String(10), nullable=True)
    patent_name = Column(String(500), nullable=False)
    filing_date = Column(DateTime, nullable=True)
    issue_date = Column(DateTime, nullable=True)
    assignee = Column(String(300), nullable=True)
    ipc_code = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    # ЛОКАЛЬНОЕ ХРАНЕНИЕ PDF
    pdf_filename = Column(String(255), nullable=True)
    pdf_file_path = Column(String(500), nullable=True)  # Полный путь к файлу на сервере

    category = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alloys = relationship('Alloy', back_populates='patent')
    authors = relationship('PatentAuthor', back_populates='patent', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Patent(id={self.id}, name='{self.patent_name}')>"


class ChemicalElement(Base):
    """Химический элемент"""
    __tablename__ = "chemical_element"

    id = Column(Integer, primary_key=True)
    name = Column(String(12), nullable=False, unique=True)
    atomic_number = Column(Integer, nullable=False, unique=True)
    symbol = Column(String(2), nullable=False, unique=True)

    alloys = relationship('Alloy',
                          secondary=alloy_element_association,
                          back_populates="elements")

    predictions = relationship('Prediction',
                               secondary=prediction_element_association,
                               back_populates="elements")

    def __repr__(self):
        return f"<ChemicalElement(id={self.id}, name='{self.name}', symbol='{self.symbol}')>"


class Role(Base):
    """Таблица ролей пользователей"""
    __tablename__ = "role"

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
    description = Column(String(100))

    persons = relationship('Person', back_populates='role')

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}')>"


class Model(Base):
    """Таблица ML моделей"""
    __tablename__ = "model"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200))

    predictions = relationship('Prediction', back_populates='model')

    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}')>"


class Organization(Base):
    """Организация пользователя"""
    __tablename__ = "organization"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    short_name = Column(String(50), nullable=True)
    inn = Column(String(12), nullable=True, unique=True)
    ogrn = Column(String(15), nullable=True, unique=True)
    address = Column(String(300), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    website = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    persons = relationship('Person', back_populates='organization_rel')

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}')>"


class Person(Base):
    """Пользователь"""
    __tablename__ = "person"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    email = Column(String(100), nullable=False, unique=True)
    role_id = Column(Integer, ForeignKey('role.id'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    login = Column(String(20), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    avatar_url = Column(String(500), nullable=True)
    avatar_filename = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    role = relationship('Role', back_populates='persons')
    organization_rel = relationship('Organization', back_populates='persons')
    predictions = relationship('Prediction', back_populates='person')
    refresh_tokens = relationship('RefreshToken', back_populates='person')
    patents_authored = relationship('PatentAuthor', back_populates='person')

    def __repr__(self):
        return f"<Person(id={self.id}, name='{self.first_name} {self.last_name}')>"


class Device(Base):
    """
    Устройство (браузер/клиент) — идентифицируется по fingerprint.
    НЕ привязано к конкретному пользователю: с одного устройства
    могут входить разные пользователи. Связь device->person
    осуществляется через RefreshToken.
    """
    __tablename__ = "device"

    id = Column(Integer, primary_key=True)
    device_name = Column(String(100), nullable=False)
    device_fingerprint = Column(String(255), nullable=False, unique=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_trusted = Column(Boolean, default=False)

    refresh_tokens = relationship('RefreshToken', back_populates='device')


class Prediction(Base):
    """Прогноз"""
    __tablename__ = "prediction"

    id = Column(Integer, primary_key=True)
    temperature = Column(Numeric(10, 3), nullable=True)
    category = Column(String(100))
    ml_model_id = Column(Integer, ForeignKey('model.id'), nullable=False)
    model = relationship('Model', back_populates="predictions")
    rolling_type = Column(String(50))
    _prop_value = Column('prop_value', Numeric, nullable=True)

    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    person = relationship('Person', back_populates="predictions")

    elements = relationship('ChemicalElement',
                            secondary=prediction_element_association,
                            back_populates="predictions")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @hybrid_property
    def prop_value(self):
        return self._prop_value

    @prop_value.setter
    def prop_value(self, value):
        if value is not None and value < 0:
            self._prop_value = 0
        else:
            self._prop_value = value

    @prop_value.expression
    def prop_value(cls):
        return cls._prop_value

    def __repr__(self):
        return f"<Prediction(id={self.id}, prop_value={self.prop_value})>"


class RefreshToken(Base):
    __tablename__ = "refresh_token"

    id = Column(Integer, primary_key=True)
    token_hash = Column(String(255), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey('person.id'), nullable=False)
    device_id = Column(Integer, ForeignKey('device.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    person = relationship('Person', back_populates='refresh_tokens')
    device = relationship('Device', back_populates='refresh_tokens')

    def __repr__(self):
        return f"<RefreshToken(user_id={self.person_id}, device_id={self.device_id}, revoked={self.revoked})>"