from sqlalchemy.orm import Session
from typing import List, Optional, Type, Dict, Any
from application.models.dao import *
import functools
import traceback
from typing import TypeVar, Any
from datetime import datetime

T = TypeVar('T')


def dbexception(db_func):
    """Функция-декоратор для перехвата исключений БД."""
    @functools.wraps(db_func)
    def decorated_func(db: Session, *args, **kwargs) -> Any:
        try:
            result = db_func(db, *args, **kwargs)
            if should_commit(db_func):
                db.commit()
            return result
        except Exception:
            print(f"Exception in {db_func.__name__}: {traceback.format_exc()}")
            db.rollback()
            return None

    def should_commit(func) -> bool:
        return func.__name__.startswith(("create", "update", "delete", "add", "revoke"))

    return decorated_func


# ========== ALLOY ==========

@dbexception
def create_alloy(
    db: Session,
    prop_value: Optional[float] = None,
    temperature: Optional[float] = None,
    category: Optional[str] = None,
    rolling_type: Optional[str] = None,
    patent_id: int = None,
    created_by_id: Optional[int] = None
) -> Optional[Alloy]:
    alloy = Alloy(
        _prop_value=prop_value,
        temperature=temperature,
        category=category,
        rolling_type=rolling_type,
        patent_id=patent_id,
        created_by_id=created_by_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(alloy)
    db.flush()
    db.refresh(alloy)
    return alloy


@dbexception
def get_alloy_by_id(db: Session, alloy_id: int) -> Optional[Alloy]:
    return db.query(Alloy).filter(Alloy.id == alloy_id).first()


@dbexception
def get_alloys_by_patent(db: Session, patent_id: int) -> List[Alloy]:
    return db.query(Alloy).filter(Alloy.patent_id == patent_id).all()


@dbexception
def get_all_alloys(db: Session, skip: int = 0, limit: int = 100) -> List[Alloy]:
    return db.query(Alloy).offset(skip).limit(limit).all()


@dbexception
def update_alloy(db: Session, alloy_id: int, **kwargs) -> Optional[Alloy]:
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if alloy:
        for key, value in kwargs.items():
            if hasattr(alloy, key):
                setattr(alloy, key, value)
        alloy.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(alloy)
    return alloy


@dbexception
def delete_alloy(db: Session, alloy_id: int) -> bool:
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if alloy:
        db.delete(alloy)
        db.commit()
        return True
    return False


@dbexception
def search_alloys_by_category(db: Session, category: str) -> List[Alloy]:
    return db.query(Alloy).filter(Alloy.category.ilike(f"%{category}%")).all()


def get_alloys_count(db: Session) -> int:
    return db.query(Alloy).count()


# ========== ALLOY-ELEMENT ASSOCIATION ==========

def add_element_to_alloy(db: Session, alloy_id: int, element_id: int, percentage: float):
    """Добавляет связь между сплавом и химическим элементом с указанием процентного содержания"""
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        raise ValueError(f"Alloy with id {alloy_id} not found")

    element = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not element:
        raise ValueError(f"Element with id {element_id} not found")

    if percentage <= 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")

    existing = db.execute(
        alloy_element_association.select().where(
            (alloy_element_association.c.alloy_id == alloy_id) &
            (alloy_element_association.c.element_id == element_id)
        )
    ).first()

    if existing:
        raise ValueError("This element is already added to the alloy")

    try:
        stmt = alloy_element_association.insert().values(
            alloy_id=alloy_id,
            element_id=element_id,
            percentage=percentage
        )
        db.execute(stmt)
        db.commit()

        new_record = db.execute(
            alloy_element_association.select().where(
                (alloy_element_association.c.alloy_id == alloy_id) &
                (alloy_element_association.c.element_id == element_id)
            )
        ).first()
        return new_record
    except Exception as e:
        db.rollback()
        raise ValueError(f"Database error: {str(e)}")


def remove_element_from_alloy(db: Session, alloy_id: int, element_id: int):
    """Удаляет связь между сплавом и химическим элементом"""
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        raise ValueError(f"Alloy with id {alloy_id} not found")

    element = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not element:
        raise ValueError(f"Element with id {element_id} not found")

    existing = db.execute(
        alloy_element_association.select().where(
            (alloy_element_association.c.alloy_id == alloy_id) &
            (alloy_element_association.c.element_id == element_id)
        )
    ).first()

    if not existing:
        raise ValueError(f"Element {element_id} is not associated with alloy {alloy_id}")

    try:
        stmt = alloy_element_association.delete().where(
            (alloy_element_association.c.alloy_id == alloy_id) &
            (alloy_element_association.c.element_id == element_id)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0
    except Exception as e:
        db.rollback()
        raise ValueError(f"Database error: {str(e)}")


def get_alloy_elements_with_percentages(db: Session, alloy_id: int) -> List[Dict]:
    """Получает элементы сплава с их процентным содержанием"""
    alloy = db.query(Alloy).filter(Alloy.id == alloy_id).first()
    if not alloy:
        return []

    elements_with_percentages = []
    for element in alloy.elements:
        assoc = db.execute(
            alloy_element_association.select().where(
                alloy_element_association.c.alloy_id == alloy_id,
                alloy_element_association.c.element_id == element.id
            )
        ).first()
        if assoc:
            elements_with_percentages.append({
                'element_id': element.id,
                'element_name': element.name,
                'element_symbol': element.symbol,
                'element_atomic_number': element.atomic_number,
                'percentage': float(assoc.percentage)
            })
    return elements_with_percentages


# ========== PREDICTION ==========

@dbexception
def create_prediction(
    db: Session,
    prop_value: Optional[float] = None,
    temperature: Optional[float] = None,
    category: Optional[str] = None,
    ml_model_id: int = None,
    rolling_type: Optional[str] = None,
    person_id: int = None
) -> Optional[Prediction]:
    prediction = Prediction(
        _prop_value=prop_value,
        temperature=temperature,
        category=category,
        ml_model_id=ml_model_id,
        rolling_type=rolling_type,
        person_id=person_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


@dbexception
def get_prediction_by_id(db: Session, prediction_id: int) -> Optional[Prediction]:
    return db.query(Prediction).filter(Prediction.id == prediction_id).first()


@dbexception
def get_all_predictions(db: Session, skip: int = 0, limit: int = 100) -> List[Prediction]:
    return db.query(Prediction).offset(skip).limit(limit).all()


@dbexception
def update_prediction(db: Session, prediction_id: int, **kwargs) -> Optional[Prediction]:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if prediction:
        for key, value in kwargs.items():
            if hasattr(prediction, key):
                setattr(prediction, key, value)
        prediction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(prediction)
    return prediction


@dbexception
def delete_prediction(db: Session, prediction_id: int) -> bool:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if prediction:
        db.delete(prediction)
        db.commit()
        return True
    return False


@dbexception
def get_predictions_by_person(db: Session, person_id: int) -> List[Prediction]:
    return db.query(Prediction).filter(Prediction.person_id == person_id).all()


@dbexception
def get_predictions_by_element(db: Session, element_id: int) -> List[Prediction]:
    return db.query(Prediction).join(
        prediction_element_association
    ).filter(
        prediction_element_association.c.element_id == element_id
    ).all()


@dbexception
def get_predictions_by_model(db: Session, model_id: int) -> List[Prediction]:
    return db.query(Prediction).filter(Prediction.ml_model_id == model_id).all()


# ========== PREDICTION-ELEMENT ASSOCIATION ==========

def add_element_to_prediction(db: Session, prediction_id: int, element_id: int, percentage: float):
    """Добавляет связь между прогнозом и химическим элементом"""
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise ValueError(f"Prediction with id {prediction_id} not found")

    element = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not element:
        raise ValueError(f"Element with id {element_id} not found")

    if percentage <= 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")

    existing = db.execute(
        prediction_element_association.select().where(
            (prediction_element_association.c.prediction_id == prediction_id) &
            (prediction_element_association.c.element_id == element_id)
        )
    ).first()

    if existing:
        raise ValueError("This element is already added to the prediction")

    try:
        stmt = prediction_element_association.insert().values(
            prediction_id=prediction_id,
            element_id=element_id,
            percentage=percentage
        )
        db.execute(stmt)
        db.commit()

        new_record = db.execute(
            prediction_element_association.select().where(
                (prediction_element_association.c.prediction_id == prediction_id) &
                (prediction_element_association.c.element_id == element_id)
            )
        ).first()
        return new_record
    except Exception as e:
        db.rollback()
        raise ValueError(f"Database error: {str(e)}")


def remove_element_from_prediction(db: Session, prediction_id: int, element_id: int) -> bool:
    """Удаляет связь между прогнозом и химическим элементом"""
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        raise ValueError(f"Prediction with id {prediction_id} not found")

    element = db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()
    if not element:
        raise ValueError(f"Element with id {element_id} not found")

    existing = db.execute(
        prediction_element_association.select().where(
            (prediction_element_association.c.prediction_id == prediction_id) &
            (prediction_element_association.c.element_id == element_id)
        )
    ).first()

    if not existing:
        raise ValueError(f"Element {element_id} is not associated with prediction {prediction_id}")

    try:
        stmt = prediction_element_association.delete().where(
            (prediction_element_association.c.prediction_id == prediction_id) &
            (prediction_element_association.c.element_id == element_id)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0
    except Exception as e:
        db.rollback()
        raise ValueError(f"Database error: {str(e)}")


def get_prediction_elements_with_percentages(db: Session, prediction_id: int) -> List[Dict]:
    """Получает элементы прогноза с их процентным содержанием"""
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not prediction:
        return []

    elements_with_percentages = []
    for element in prediction.elements:
        assoc = db.execute(
            prediction_element_association.select().where(
                prediction_element_association.c.prediction_id == prediction_id,
                prediction_element_association.c.element_id == element.id
            )
        ).first()
        if assoc:
            elements_with_percentages.append({
                'prediction_id': prediction_id,
                'element_id': element.id,
                'element_symbol': element.symbol,
                'percentage': float(assoc.percentage)
            })
    return elements_with_percentages


# ========== PATENT ==========

# repository_service.py - только измененные функции
# (остальной код остается без изменений)

@dbexception
def create_patent(
    db: Session,
    patent_number: str,
    patent_name: str,
    country: Optional[str] = None,
    filing_date: Optional[datetime] = None,
    issue_date: Optional[datetime] = None,
    assignee: Optional[str] = None,
    ipc_code: Optional[str] = None,
    description: Optional[str] = None,
    pdf_filename: Optional[str] = None,
    pdf_file_path: Optional[str] = None,
    category: Optional[str] = None
) -> Optional[Patent]:
    patent = Patent(
        patent_number=patent_number,
        country=country,
        patent_name=patent_name,
        filing_date=filing_date,
        issue_date=issue_date,
        assignee=assignee,
        ipc_code=ipc_code,
        description=description,
        pdf_filename=pdf_filename,
        pdf_file_path=pdf_file_path,
        category=category,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(patent)
    db.commit()
    db.refresh(patent)
    return patent


@dbexception
def get_patent_by_id(db: Session, patent_id: int) -> Optional[Patent]:
    return db.query(Patent).filter(Patent.id == patent_id).first()


@dbexception
def get_patent_by_number(db: Session, patent_number: str) -> Optional[Patent]:
    return db.query(Patent).filter(Patent.patent_number == patent_number).first()


@dbexception
def get_all_patents(db: Session, skip: int = 0, limit: int = 100) -> List[Patent]:
    return db.query(Patent).offset(skip).limit(limit).all()


@dbexception
def update_patent(db: Session, patent_id: int, **kwargs) -> Optional[Patent]:
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if patent:
        for key, value in kwargs.items():
            if hasattr(patent, key):
                setattr(patent, key, value)
        patent.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patent)
    return patent


@dbexception
def delete_patent(db: Session, patent_id: int) -> bool:
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if patent:
        db.delete(patent)
        db.commit()
        return True
    return False


# ========== PATENT (дополнительные функции) ==========

@dbexception
def get_patents_by_person(db: Session, person_id: int) -> List[Patent]:
    """
    Получить патенты, где пользователь является автором ИЛИ создателем связанных сплавов.
    Для исследователя - только свои патенты.
    """
    # Патенты, где пользователь указан как автор
    author_patents = db.query(Patent).join(
        PatentAuthor, PatentAuthor.patent_id == Patent.id
    ).filter(PatentAuthor.person_id == person_id).all()

    # Патенты, связанные со сплавами, созданными пользователем
    alloy_patents = db.query(Patent).join(
        Alloy, Alloy.patent_id == Patent.id
    ).filter(Alloy.created_by_id == person_id).all()

    # Объединяем и убираем дубликаты
    all_patents = {p.id: p for p in author_patents}
    for p in alloy_patents:
        all_patents[p.id] = p

    return list(all_patents.values())


# ========== PATENT AUTHOR ==========

@dbexception
def add_patent_author(
    db: Session,
    patent_id: int,
    author_name: str,
    author_order: int,
    person_id: Optional[int] = None
) -> Optional[PatentAuthor]:
    author = PatentAuthor(
        patent_id=patent_id,
        person_id=person_id,
        author_name=author_name,
        author_order=author_order
    )
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


@dbexception
def get_patent_authors(db: Session, patent_id: int) -> List[PatentAuthor]:
    return db.query(PatentAuthor).filter(
        PatentAuthor.patent_id == patent_id
    ).order_by(PatentAuthor.author_order).all()


@dbexception
def delete_patent_author(db: Session, author_id: int) -> bool:
    author = db.query(PatentAuthor).filter(PatentAuthor.id == author_id).first()
    if author:
        db.delete(author)
        db.commit()
        return True
    return False


# ========== CHEMICAL ELEMENT ==========

@dbexception
def create_chemical_element(
    db: Session,
    name: str,
    atomic_number: int,
    symbol: str
) -> Optional[ChemicalElement]:
    existing = db.query(ChemicalElement).filter(
        (ChemicalElement.symbol == symbol) |
        (ChemicalElement.atomic_number == atomic_number)
    ).first()
    if existing:
        return None
    element = ChemicalElement(
        name=name,
        atomic_number=atomic_number,
        symbol=symbol
    )
    db.add(element)
    db.commit()
    db.refresh(element)
    return element


@dbexception
def get_element_by_id(db: Session, element_id: int) -> Optional[ChemicalElement]:
    return db.query(ChemicalElement).filter(ChemicalElement.id == element_id).first()


@dbexception
def get_element_by_symbol(db: Session, symbol: str) -> Optional[ChemicalElement]:
    return db.query(ChemicalElement).filter(ChemicalElement.symbol == symbol).first()


@dbexception
def get_element_by_atomic_number(db: Session, atomic_number: int) -> Optional[ChemicalElement]:
    return db.query(ChemicalElement).filter(ChemicalElement.atomic_number == atomic_number).first()


@dbexception
def get_all_elements(db: Session) -> List[ChemicalElement]:
    return db.query(ChemicalElement).order_by(ChemicalElement.atomic_number).all()


# ========== ORGANIZATION ==========

@dbexception
def create_organization(
    db: Session,
    name: str,
    short_name: Optional[str] = None,
    inn: Optional[str] = None,
    ogrn: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    website: Optional[str] = None
) -> Optional[Organization]:
    org = Organization(
        name=name,
        short_name=short_name,
        inn=inn,
        ogrn=ogrn,
        address=address,
        phone=phone,
        email=email,
        website=website,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@dbexception
def get_organization_by_id(db: Session, org_id: int) -> Optional[Organization]:
    return db.query(Organization).filter(Organization.id == org_id).first()


@dbexception
def get_organization_by_inn(db: Session, inn: str) -> Optional[Organization]:
    return db.query(Organization).filter(Organization.inn == inn).first()


@dbexception
def get_all_organizations(db: Session, skip: int = 0, limit: int = 100) -> List[Organization]:
    return db.query(Organization).offset(skip).limit(limit).all()


@dbexception
def update_organization(db: Session, org_id: int, **kwargs) -> Optional[Organization]:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org:
        for key, value in kwargs.items():
            if hasattr(org, key):
                setattr(org, key, value)
        org.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(org)
    return org


@dbexception
def delete_organization(db: Session, org_id: int) -> bool:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org:
        db.delete(org)
        db.commit()
        return True
    return False


# ========== PERSON ==========

@dbexception
def create_person(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    role_id: int,
    login: str,
    password_hash: str,
    middle_name: Optional[str] = None,
    organization_id: Optional[int] = None
) -> Optional[Person]:
    person = Person(
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        email=email,
        role_id=role_id,
        organization_id=organization_id,
        login=login,
        password_hash=password_hash,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )
    db.add(person)
    db.flush()
    db.refresh(person)
    return person


@dbexception
def get_person_by_id(db: Session, person_id: int) -> Optional[Person]:
    return db.query(Person).filter(Person.id == person_id).first()


@dbexception
def get_person_by_login(db: Session, login: str) -> Optional[Person]:
    return db.query(Person).filter(Person.login == login).first()


@dbexception
def get_person_by_email(db: Session, email: str) -> Optional[Person]:
    return db.query(Person).filter(Person.email == email).first()


@dbexception
def get_all_persons(db: Session, skip: int = 0, limit: int = 100) -> List[Person]:
    return db.query(Person).offset(skip).limit(limit).all()


@dbexception
def get_persons_by_role(db: Session, role_id: int) -> List[Person]:
    return db.query(Person).filter(Person.role_id == role_id).all()


@dbexception
def get_persons_by_organization(db: Session, organization_id: int) -> List[Person]:
    return db.query(Person).filter(Person.organization_id == organization_id).all()


@dbexception
def update_person(db: Session, person_id: int, **kwargs) -> Optional[Person]:
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return None

    if 'login' in kwargs and kwargs['login'] != person.login:
        existing = db.query(Person).filter(
            Person.login == kwargs['login'],
            Person.id != person_id
        ).first()
        if existing:
            return None

    if 'email' in kwargs and kwargs['email'] != person.email:
        existing = db.query(Person).filter(
            Person.email == kwargs['email'],
            Person.id != person_id
        ).first()
        if existing:
            return None

    for key, value in kwargs.items():
        if hasattr(person, key) and key not in ['id', 'created_at']:
            setattr(person, key, value)

    person.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(person)
    return person


@dbexception
def update_last_login(db: Session, person_id: int) -> bool:
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        person.last_login = datetime.utcnow()
        db.commit()
        return True
    return False


@dbexception
def delete_person(db: Session, person_id: int) -> bool:
    person = db.query(Person).filter(Person.id == person_id).first()
    if person:
        # Сначала удаляем связанные данные
        db.query(RefreshToken).filter(RefreshToken.person_id == person_id).delete()
        # Обновляем записи PatentAuthor (убираем связь с пользователем)
        db.query(PatentAuthor).filter(PatentAuthor.person_id == person_id).update({PatentAuthor.person_id: None})
        # Удаляем прогнозы пользователя
        db.query(Prediction).filter(Prediction.person_id == person_id).delete()
        # Обновляем сплавы, созданные пользователем (убираем связь)
        db.query(Alloy).filter(Alloy.created_by_id == person_id).update({Alloy.created_by_id: None})

        db.delete(person)
        db.commit()
        return True
    return False


# ========== ROLE ==========

@dbexception
def create_role(db: Session, name: str, description: str = None) -> Optional[Role]:
    existing = db.query(Role).filter(Role.name == name).first()
    if existing:
        return existing
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@dbexception
def get_role_by_id(db: Session, role_id: int) -> Optional[Role]:
    return db.query(Role).filter(Role.id == role_id).first()


@dbexception
def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    return db.query(Role).filter(Role.name == name).first()


@dbexception
def get_all_roles(db: Session) -> List[Role]:
    return db.query(Role).all()


@dbexception
def delete_role(db: Session, role_id: int) -> bool:
    role = db.query(Role).filter(Role.id == role_id).first()
    if role:
        db.delete(role)
        db.commit()
        return True
    return False


# ========== MODEL ==========

@dbexception
def create_model(db: Session, name: str, description: str = None) -> Optional[Model]:
    existing = db.query(Model).filter(Model.name == name).first()
    if existing:
        return existing
    model = Model(name=name, description=description)
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@dbexception
def get_model_by_id(db: Session, model_id: int) -> Optional[Model]:
    return db.query(Model).filter(Model.id == model_id).first()


@dbexception
def get_model_by_name(db: Session, name: str) -> Optional[Model]:
    return db.query(Model).filter(Model.name == name).first()


@dbexception
def get_all_models(db: Session) -> List[Model]:
    return db.query(Model).all()


@dbexception
def delete_model(db: Session, model_id: int) -> bool:
    model = db.query(Model).filter(Model.id == model_id).first()
    if model:
        db.delete(model)
        db.commit()
        return True
    return False


# ========== DEVICE ==========

@dbexception
def create_device(
    db: Session,
    device_name: str,
    device_fingerprint: str,
    is_trusted: bool = False
) -> Optional[Device]:
    """Создать устройство без привязки к пользователю."""
    device = Device(
        device_name=device_name,
        device_fingerprint=device_fingerprint,
        is_trusted=is_trusted,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow()
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@dbexception
def get_device_by_fingerprint(db: Session, fingerprint: str) -> Optional[Device]:
    return db.query(Device).filter(Device.device_fingerprint == fingerprint).first()


@dbexception
def get_user_devices(db: Session, person_id: int) -> List[Device]:
    """Устройства пользователя — через его активные refresh_tokens."""
    return (
        db.query(Device)
        .join(RefreshToken, RefreshToken.device_id == Device.id)
        .filter(
            RefreshToken.person_id == person_id,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        .distinct()
        .all()
    )


@dbexception
def update_device_last_seen(db: Session, device_id: int) -> bool:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        device.last_seen = datetime.utcnow()
        db.commit()
        return True
    return False


@dbexception
def delete_device(db: Session, device_id: int) -> bool:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device:
        # Сначала удаляем связанные токены
        db.query(RefreshToken).filter(RefreshToken.device_id == device_id).delete()
        db.delete(device)
        db.commit()
        return True
    return False


# ========== REFRESH TOKEN ==========

@dbexception
def create_refresh_token(
    db: Session,
    person_id: int,
    device_id: int,
    token_hash: str,
    expires_at: datetime
) -> Optional[RefreshToken]:
    token = RefreshToken(
        token_hash=token_hash,
        person_id=person_id,
        device_id=device_id,
        expires_at=expires_at,
        revoked=False,
        created_at=datetime.utcnow()
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


@dbexception
def get_refresh_token_by_hash(db: Session, token_hash: str) -> Optional[RefreshToken]:
    return db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()


@dbexception
def get_active_refresh_tokens_by_user(db: Session, person_id: int) -> List[RefreshToken]:
    return db.query(RefreshToken).filter(
        RefreshToken.person_id == person_id,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()


@dbexception
def revoke_refresh_token(db: Session, token_hash: str) -> bool:
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token:
        token.revoked = True
        db.commit()
        return True
    return False


@dbexception
def revoke_all_user_tokens(db: Session, person_id: int, exclude_device_id: Optional[int] = None) -> int:
    query = db.query(RefreshToken).filter(
        RefreshToken.person_id == person_id,
        RefreshToken.revoked == False
    )
    if exclude_device_id:
        query = query.filter(RefreshToken.device_id != exclude_device_id)
    count = query.update({"revoked": True})
    db.commit()
    return count


@dbexception
def update_token_last_used(db: Session, token_hash: str) -> bool:
    token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token:
        token.last_used_at = datetime.utcnow()
        db.commit()
        return True
    return False


# ========== COMPLEX FUNCTIONS ==========

def create_alloy_with_elements(
    db: Session,
    prop_value: Optional[float],
    category: Optional[str],
    rolling_type: Optional[str],
    patent_id: int,
    element_percentages: Dict[int, float],
    temperature: Optional[float] = None,
    created_by_id: Optional[int] = None
) -> Optional[Alloy]:
    alloy = create_alloy(
        db,
        prop_value=prop_value,
        temperature=temperature,
        category=category,
        rolling_type=rolling_type,
        patent_id=patent_id,
        created_by_id=created_by_id
    )
    if not alloy:
        return None

    for element_id, percentage in element_percentages.items():
        percentage = min(float(percentage), 99.999)
        add_element_to_alloy(db, alloy.id, element_id, percentage)

    return alloy


def create_prediction_with_elements(
    db: Session,
    prop_value: Optional[float],
    category: Optional[str],
    ml_model_id: int,
    rolling_type: Optional[str],
    person_id: int,
    element_percentages: Dict[int, float],
    temperature: Optional[float] = None
) -> Optional[Prediction]:
    prediction = create_prediction(
        db,
        prop_value=prop_value,
        temperature=temperature,
        category=category,
        ml_model_id=ml_model_id,
        rolling_type=rolling_type,
        person_id=person_id
    )
    if not prediction:
        return None

    for element_id, percentage in element_percentages.items():
        percentage = min(float(percentage), 99.999)
        add_element_to_prediction(db, prediction.id, element_id, percentage)

    return prediction


def get_alloys_with_details(db: Session):
    return db.query(Alloy).join(Patent).all()


def get_predictions_with_details(db: Session):
    return db.query(Prediction).join(Person).all()