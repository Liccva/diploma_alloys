# routes.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi import UploadFile, File, Form
from starlette.responses import RedirectResponse, FileResponse
from typing import List, Optional, Dict
from pydantic import BaseModel
from fastapi import Body, Request
from datetime import datetime
import os
import hashlib

from fastapi.responses import StreamingResponse
import io

# Импорт DTO
from application.models.dto import (
    ChemicalElementDTO,
    ChemicalElementCreateDTO,
    AlloyDTO,
    AlloyCreateDTO,
    AlloyUpdateDTO,
    AlloyDetailDTO,
    AlloyElementAssociationDTO,
    AlloyElementResponseDTO,
    PredictionDTO,
    PredictionCreateDTO,
    PredictionUpdateDTO,
    PredictionDetailDTO,
    PredictionElementAssociationDTO,
    PatentDTO,
    PatentCreateDTO,
    PatentUpdateDTO,
    PatentDetailDTO,
    PatentCreateWithAuthorsDTO,
    PatentAuthorDTO,
    PersonDTO,
    PersonCreateDTO,
    PersonUpdateDTO,
    PersonDetailDTO,
    RoleDTO,
    RoleCreateDTO,
    ModelDTO,
    ModelCreateDTO,
    OrganizationDTO,
    OrganizationCreateDTO,
    OrganizationUpdateDTO,
    DeviceDTO,
    DeviceCreateDTO,
    RefreshTokenDTO,
    LoginRequestDTO,
    LoginResponseDTO,
    RefreshRequestDTO,
    RefreshResponseDTO,
    LogoutRequestDTO,
    GrantRoleToOrganizationDTO,
    ChangePasswordDTO
)

# Импорт моделей DAO
from application.models.dao.alloys import (
    Person, Alloy, Patent, ChemicalElement, Prediction,
    Role, Model, Organization, Device, RefreshToken, PatentAuthor
)

# Импорт сервисов и утилит
from application.services import repository_service as service
from application.utils.auth import (
    get_current_user,
    get_current_user_optional,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token_in_db,
    validate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    create_device_fingerprint,
    hash_token,
    get_db as get_auth_db,
    is_admin,
    is_researcher,
    require_admin,
    require_researcher,
)
from application.utils.patent_utils import get_category_by_ipc
from sqlalchemy.orm import Session
from application.config import SessionLocal, get_db as get_db_config
from application.services.ml_inference import MLInference

router = APIRouter(prefix='/api', tags=['Metal Alloys API'])


def get_db() -> Session:
    """Context manager для безопасной работы с БД"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Вспомогательные функции проверки прав
def can_edit_alloy(db: Session, user: Person, alloy_id: int) -> bool:
    """Проверка прав на редактирование сплава"""
    if is_admin(user):
        return True
    alloy = service.get_alloy_by_id(db, alloy_id)
    return alloy and alloy.created_by_id == user.id


def can_edit_patent(db: Session, user: Person, patent_id: int) -> bool:
    """Проверка прав на редактирование патента"""
    if is_admin(user):
        return True
    authors = service.get_patent_authors(db, patent_id)
    return any(a.person_id == user.id for a in authors)


def can_view_prediction(user: Person, prediction_person_id: int) -> bool:
    """Проверка прав на просмотр прогноза"""
    if is_admin(user):
        return True
    return user.id == prediction_person_id


@router.get('/')
async def root():
    """Переадресация на страницу Swagger"""
    return RedirectResponse(url='/docs', status_code=307)


# ========== CHEMICAL ELEMENTS ROUTES ==========

@router.get('/elements/', response_model=List[ChemicalElementDTO])
async def get_all_elements(
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все химические элементы (доступно всем, включая неавторизованных)"""
    elements = service.get_all_elements(db)
    return elements or []


@router.get('/elements/{element_id}', response_model=ChemicalElementDTO)
async def get_element_by_id(
        element_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить химический элемент по ID (доступно всем)"""
    element = service.get_element_by_id(db, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return element


@router.get('/elements/symbol/{symbol}', response_model=ChemicalElementDTO)
async def get_element_by_symbol(
        symbol: str,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить химический элемент по символу (доступно всем)"""
    element = service.get_element_by_symbol(db, symbol)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found")
    return element


@router.post('/elements/', status_code=201)
async def create_element(
        element: ChemicalElementCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Создать новый химический элемент (только админ)"""
    existing_element = service.get_element_by_symbol(db, element.symbol)
    if existing_element:
        raise HTTPException(
            status_code=409,
            detail=f"Element with symbol '{element.symbol}' already exists"
        )

    result = service.create_chemical_element(
        db,
        name=element.name,
        atomic_number=element.atomic_number,
        symbol=element.symbol,
    )

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create element due to database error",
        )

    return {
        "message": "Chemical element created successfully",
        "id": result.id,
        "symbol": result.symbol,
    }


# ========== ALLOYS ROUTES ==========

@router.get('/alloys/', response_model=List[AlloyDTO])
async def get_all_alloys(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все сплавы (доступно всем, включая неавторизованных)"""
    alloys = service.get_all_alloys(db, skip, limit)
    return alloys or []


@router.get('/alloys/{alloy_id}', response_model=AlloyDTO)
async def get_alloy_by_id(
        alloy_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить сплав по ID (доступно всем)"""
    alloy = service.get_alloy_by_id(db, alloy_id)
    if alloy is None:
        raise HTTPException(status_code=404, detail="Alloy not found")
    return alloy


@router.post('/alloys/', status_code=201)
async def create_alloy(
        alloy: AlloyCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Создать новый сплав (админ и исследователь)"""
    if not is_admin(current_user) and not is_researcher(current_user):
        raise HTTPException(status_code=403, detail="Only admins and researchers can create alloys")

    result = service.create_alloy(
        db,
        prop_value=alloy.prop_value,
        temperature=alloy.temperature,
        category=alloy.category,
        rolling_type=alloy.rolling_type,
        patent_id=alloy.patent_id,
        created_by_id=current_user.id
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create alloy")
    return result


@router.put('/alloys/{alloy_id}', response_model=AlloyDTO)
async def update_alloy(
        alloy_id: int,
        alloy: AlloyUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Обновить сплав (только создатель или админ)"""
    existing = service.get_alloy_by_id(db, alloy_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Alloy not found")
    if not can_edit_alloy(db, current_user, alloy_id):
        raise HTTPException(status_code=403, detail="You are not creator of this alloy")
    update_data = alloy.dict(exclude_unset=True)
    result = service.update_alloy(db, alloy_id, **update_data)
    return result


@router.delete('/alloys/{alloy_id}', status_code=200)
async def delete_alloy(
        alloy_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить сплав (только создатель или админ)"""
    existing = service.get_alloy_by_id(db, alloy_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Alloy not found")
    if not can_edit_alloy(db, current_user, alloy_id):
        raise HTTPException(status_code=403, detail="You are not creator of this alloy")
    if not service.delete_alloy(db, alloy_id):
        raise HTTPException(status_code=404, detail="Alloy not found")
    return {"message": "Alloy deleted successfully"}


@router.get('/alloys/patent/{patent_id}', response_model=List[AlloyDTO])
async def get_alloys_by_patent(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить сплавы по патенту (доступно всем)"""
    alloys = service.get_alloys_by_patent(db, patent_id)
    return alloys or []


@router.get('/alloys/category/{category}', response_model=List[AlloyDTO])
async def search_alloys_by_category(
        category: str,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Поиск сплавов по категории (доступно всем)"""
    alloys = service.search_alloys_by_category(db, category)
    return alloys or []


# ========== ALLOY-ELEMENT ASSOCIATION ROUTES ==========

@router.post('/alloys/{alloy_id}/elements/{element_id}', status_code=201, response_model=AlloyElementAssociationDTO)
async def add_element_to_alloy(
        alloy_id: int,
        element_id: int,
        percentage: float,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Добавить элемент к сплаву (админ или создатель сплава)"""
    if not is_admin(current_user):
        alloy = service.get_alloy_by_id(db, alloy_id)
        if not alloy or alloy.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not creator of this alloy")

    try:
        result = service.add_element_to_alloy(db, alloy_id, element_id, percentage)
        return AlloyElementAssociationDTO(
            alloy_id=result.alloy_id,
            element_id=result.element_id,
            percentage=float(result.percentage)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete('/alloys/{alloy_id}/elements/{element_id}', status_code=204)
async def remove_element_from_alloy(
        alloy_id: int,
        element_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить элемент из сплава (админ или создатель сплава)"""
    if not is_admin(current_user):
        alloy = service.get_alloy_by_id(db, alloy_id)
        if not alloy or alloy.created_by_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not creator of this alloy")

    try:
        service.remove_element_from_alloy(db, alloy_id, element_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get('/alloys/{alloy_id}/elements', response_model=List[AlloyElementResponseDTO])
async def get_alloy_elements(
        alloy_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить элементы сплава с процентным содержанием (доступно всем)"""
    elements = service.get_alloy_elements_with_percentages(db, alloy_id)
    return elements or []


# ========== PREDICTIONS ROUTES ==========

@router.get('/predictions/', response_model=List[PredictionDTO])
async def get_my_predictions(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить свои прогнозы (админ видит все, исследователь только свои)"""
    if is_admin(current_user):
        predictions = service.get_all_predictions(db, skip, limit)
    else:
        predictions = service.get_predictions_by_person(db, current_user.id)
    return predictions or []


@router.get('/predictions/{prediction_id}', response_model=PredictionDTO)
async def get_prediction_by_id(
        prediction_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить прогноз по ID (только свои для исследователей, все для админа)"""
    prediction = service.get_prediction_by_id(db, prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not can_view_prediction(current_user, prediction.person_id):
        raise HTTPException(status_code=403, detail="You can only view your own predictions")
    return prediction


@router.post('/predictions/', status_code=201)
async def create_prediction(
        prediction: PredictionCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Создать новый прогноз (админ и исследователь)"""
    if not is_admin(current_user) and not is_researcher(current_user):
        raise HTTPException(status_code=403, detail="Only admins and researchers can create predictions")

    result = service.create_prediction(
        db,
        prop_value=prediction.prop_value,
        temperature=prediction.temperature,
        category=prediction.category,
        ml_model_id=prediction.ml_model_id,
        rolling_type=prediction.rolling_type,
        person_id=current_user.id
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create prediction")
    return {"message": "Prediction created successfully", "id": result.id}


@router.put('/predictions/{prediction_id}', response_model=PredictionDTO)
async def update_prediction(
        prediction_id: int,
        prediction: PredictionUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Обновить прогноз (только свои)"""
    existing = service.get_prediction_by_id(db, prediction_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prediction not found")

    if not can_view_prediction(current_user, existing.person_id):
        raise HTTPException(status_code=403, detail="You can only update your own predictions")

    update_data = prediction.dict(exclude_unset=True)
    result = service.update_prediction(db, prediction_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return result


@router.delete('/predictions/{prediction_id}', status_code=200)
async def delete_prediction(
        prediction_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить прогноз (только свои)"""
    existing = service.get_prediction_by_id(db, prediction_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Prediction not found")

    if not can_view_prediction(current_user, existing.person_id):
        raise HTTPException(status_code=403, detail="You can only delete your own predictions")

    if not service.delete_prediction(db, prediction_id):
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {"message": "Prediction deleted successfully"}


@router.get('/predictions/person/{person_id}', response_model=List[PredictionDTO])
async def get_predictions_by_person(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить прогнозы по пользователю (только админ или свои)"""
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="You can only view your own predictions")

    predictions = service.get_predictions_by_person(db, person_id)
    return predictions or []


@router.get('/predictions/element/{element_id}', response_model=List[PredictionDTO])
async def get_predictions_by_element(
        element_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить прогнозы по химическому элементу (только свои)"""
    if is_admin(current_user):
        predictions = service.get_predictions_by_element(db, element_id)
    else:
        predictions = service.get_predictions_by_element(db, element_id)
        predictions = [p for p in predictions if p.person_id == current_user.id]
    return predictions or []


@router.get('/predictions/model/{model_id}', response_model=List[PredictionDTO])
async def get_predictions_by_model(
        model_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить прогнозы по ML модели (только свои)"""
    if is_admin(current_user):
        predictions = service.get_predictions_by_model(db, model_id)
    else:
        predictions = service.get_predictions_by_model(db, model_id)
        predictions = [p for p in predictions if p.person_id == current_user.id]
    return predictions or []


# ========== PREDICTION-ELEMENT ASSOCIATION ROUTES ==========

@router.post('/predictions/{prediction_id}/elements/{element_id}', status_code=201,
             response_model=PredictionElementAssociationDTO)
async def add_element_to_prediction(
        prediction_id: int,
        element_id: int,
        percentage: float,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Добавить элемент к прогнозу (только свои прогнозы)"""
    prediction = service.get_prediction_by_id(db, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not can_view_prediction(current_user, prediction.person_id):
        raise HTTPException(status_code=403, detail="You can only modify your own predictions")

    try:
        result = service.add_element_to_prediction(db, prediction_id, element_id, percentage)
        return PredictionElementAssociationDTO(
            prediction_id=result.prediction_id,
            element_id=result.element_id,
            percentage=float(result.percentage)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete('/predictions/{prediction_id}/elements/{element_id}', status_code=200)
async def remove_element_from_prediction(
        prediction_id: int,
        element_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить элемент из прогноза (только свои прогнозы)"""
    prediction = service.get_prediction_by_id(db, prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if not can_view_prediction(current_user, prediction.person_id):
        raise HTTPException(status_code=403, detail="You can only modify your own predictions")

    try:
        service.remove_element_from_prediction(db, prediction_id, element_id)
        return {"message": f"Element {element_id} successfully removed from prediction {prediction_id}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get('/predictions/{prediction_id}/elements', response_model=List[PredictionElementAssociationDTO])
async def get_prediction_elements(
        prediction_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить элементы прогноза (доступно всем)"""
    elements = service.get_prediction_elements_with_percentages(db, prediction_id)
    return elements or []


# ========== PATENTS ROUTES ==========

@router.get('/patents/', response_model=List[PatentDTO])
async def get_all_patents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все патенты (доступно всем, включая неавторизованных)"""
    patents = service.get_all_patents(db, skip, limit)
    return patents or []


@router.get('/patents/{patent_id}', response_model=PatentDetailDTO)
async def get_patent_by_id(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить патент по ID с авторами (доступно всем)"""
    patent = service.get_patent_by_id(db, patent_id)
    if patent is None:
        raise HTTPException(status_code=404, detail="Patent not found")

    authors = service.get_patent_authors(db, patent_id)

    return PatentDetailDTO(
        id=patent.id,
        patent_number=patent.patent_number,
        country=patent.country,
        patent_name=patent.patent_name,
        filing_date=patent.filing_date,
        issue_date=patent.issue_date,
        assignee=patent.assignee,
        ipc_code=patent.ipc_code,
        description=patent.description,
        pdf_file_path=patent.pdf_file_path,
        pdf_filename=patent.pdf_filename,
        category=patent.category,
        created_at=patent.created_at,
        updated_at=patent.updated_at,
        authors=authors
    )


@router.get('/patents/number/{patent_number}', response_model=PatentDetailDTO)
async def get_patent_by_number(
        patent_number: str,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить патент по номеру с авторами (доступно всем)"""
    patent = service.get_patent_by_number(db, patent_number)
    if patent is None:
        raise HTTPException(status_code=404, detail="Patent not found")

    authors = service.get_patent_authors(db, patent.id)

    return PatentDetailDTO(
        id=patent.id,
        patent_number=patent.patent_number,
        country=patent.country,
        patent_name=patent.patent_name,
        filing_date=patent.filing_date,
        issue_date=patent.issue_date,
        assignee=patent.assignee,
        ipc_code=patent.ipc_code,
        description=patent.description,
        pdf_file_path=patent.pdf_file_path,
        pdf_filename=patent.pdf_filename,
        category=patent.category,
        created_at=patent.created_at,
        updated_at=patent.updated_at,
        authors=authors
    )


@router.post('/patents/', status_code=201)
async def create_patent(
        patent: PatentCreateWithAuthorsDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Создать новый патент (админ может всё, исследователь добавляется как автор)"""

    if not is_admin(current_user) and not is_researcher(current_user):
        raise HTTPException(status_code=403, detail="Only admins and researchers can create patents")

    category = patent.category
    if not category and patent.ipc_code:
        category = get_category_by_ipc(patent.ipc_code)

    result = service.create_patent(
        db,
        patent_number=patent.patent_number,
        country=patent.country,
        patent_name=patent.patent_name,
        filing_date=patent.filing_date,
        issue_date=patent.issue_date,
        assignee=patent.assignee,
        ipc_code=patent.ipc_code,
        description=patent.description,
        category=category
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create patent")

    if is_admin(current_user):
        for author_data in patent.authors:
            service.add_patent_author(
                db,
                patent_id=result.id,
                author_name=author_data.author_name,
                author_order=author_data.author_order,
                person_id=author_data.person_id
            )
    else:
        # Исследователь автоматически становится первым автором
        service.add_patent_author(
            db,
            patent_id=result.id,
            author_name=f"{current_user.first_name} {current_user.last_name}",
            author_order=1,
            person_id=current_user.id
        )

        for idx, author_data in enumerate(patent.authors, start=2):
            if author_data.person_id == current_user.id:
                continue
            service.add_patent_author(
                db,
                patent_id=result.id,
                author_name=author_data.author_name,
                author_order=idx,
                person_id=author_data.person_id
            )

    return {"message": "Patent created successfully", "id": result.id}


# Добавляем оба варианта: с / и без / в конце
@router.post('/patents/with-authors/', status_code=201)
@router.post('/patents/with-authors', status_code=201)  # Дополнительный роут без слеша
async def create_patent_with_authors(
        patent: PatentCreateWithAuthorsDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Создать патент вместе с авторами (админ может всё, исследователь добавляется как соавтор)"""

    if not is_admin(current_user) and not is_researcher(current_user):
        raise HTTPException(status_code=403, detail="Only admins and researchers can create patents")

    category = patent.category
    if not category and patent.ipc_code:
        category = get_category_by_ipc(patent.ipc_code)

    result = service.create_patent(
        db,
        patent_number=patent.patent_number,
        country=patent.country,
        patent_name=patent.patent_name,
        filing_date=patent.filing_date,
        issue_date=patent.issue_date,
        assignee=patent.assignee,
        ipc_code=patent.ipc_code,
        description=patent.description,
        category=category
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create patent")

    if is_admin(current_user):
        # Админ добавляет всех авторов как указано в форме
        for author_data in patent.authors:
            service.add_patent_author(
                db,
                patent_id=result.id,
                author_name=author_data.author_name,
                author_order=author_data.author_order,
                person_id=author_data.person_id
            )
    else:
        # Исследователь — добавляем всех авторов из формы
        has_current_user = False
        for idx, author_data in enumerate(patent.authors, start=1):
            service.add_patent_author(
                db,
                patent_id=result.id,
                author_name=author_data.author_name,
                author_order=author_data.author_order or idx,
                person_id=author_data.person_id
            )
            if author_data.person_id == current_user.id:
                has_current_user = True

        # Если текущий пользователь не был добавлен явно, добавляем его как автора
        if not has_current_user:
            next_order = len(patent.authors) + 1
            service.add_patent_author(
                db,
                patent_id=result.id,
                author_name=f"{current_user.first_name} {current_user.last_name}",
                author_order=next_order,
                person_id=current_user.id
            )

    return {"message": "Patent with authors created successfully", "id": result.id}


@router.put('/patents/{patent_id}', response_model=PatentDTO)
async def update_patent(
        patent_id: int,
        patent: PatentUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Обновить патент (только автор или админ)"""
    existing = service.get_patent_by_id(db, patent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Patent not found")
    if not can_edit_patent(db, current_user, patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")
    update_data = patent.dict(exclude_unset=True)
    result = service.update_patent(db, patent_id, **update_data)
    return result


@router.delete('/patents/{patent_id}', status_code=200)
async def delete_patent(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить патент (только автор или админ)"""
    existing = service.get_patent_by_id(db, patent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Patent not found")
    if not can_edit_patent(db, current_user, patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")
    if not service.delete_patent(db, patent_id):
        raise HTTPException(status_code=404, detail="Patent not found")
    return {"message": "Patent deleted successfully"}


@router.get('/patents/for-alloy/', response_model=List[PatentDTO])
async def get_patents_for_alloy(
    db: Session = Depends(get_db),
    current_user: Person = Depends(get_current_user)
):
    """
    Получить патенты для выбора в форме сплава.
    - Админ видит все патенты
    - Исследователь видит только патенты, где он автор или создатель сплава
    """
    if is_admin(current_user):
        patents = service.get_all_patents(db, skip=0, limit=500)
    else:
        patents = service.get_patents_by_person(db, current_user.id)
    return patents or []


# ========== PATENT AUTHORS ROUTES ==========

@router.get('/patents/{patent_id}/authors', response_model=List[PatentAuthorDTO])
async def get_patent_authors(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить авторов патента (доступно всем)"""
    authors = service.get_patent_authors(db, patent_id)
    return authors


@router.post('/patents/{patent_id}/authors', status_code=201)
async def add_patent_author(
        patent_id: int,
        author_name: str,
        author_order: int,
        person_id: Optional[int] = None,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Добавить автора к патенту (админ или автор патента)"""
    if not can_edit_patent(db, current_user, patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")

    result = service.add_patent_author(
        db,
        patent_id=patent_id,
        author_name=author_name,
        author_order=author_order,
        person_id=person_id
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't add author")
    return {"message": "Author added successfully", "id": result.id}


@router.delete('/patents/authors/{author_id}', status_code=200)
async def delete_patent_author(
        author_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить автора патента (админ или автор патента)"""
    # Получаем автора, чтобы узнать patent_id
    authors = db.query(PatentAuthor).filter(PatentAuthor.id == author_id).first()
    if not authors:
        raise HTTPException(status_code=404, detail="Author not found")

    if not can_edit_patent(db, current_user, authors.patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")

    if not service.delete_patent_author(db, author_id):
        raise HTTPException(status_code=404, detail="Author not found")
    return {"message": "Author deleted successfully"}


# ========== PATENT PDF ROUTES ==========

@router.post('/patents/{patent_id}/upload-pdf', status_code=200)
async def upload_patent_pdf(
        patent_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Загрузить PDF файл патента (только автор или админ)"""
    import os, shutil

    existing = service.get_patent_by_id(db, patent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patent not found")
    if not can_edit_patent(db, current_user, patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are allowed")

    upload_dir = os.path.join("uploads", "patents")
    os.makedirs(upload_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"patent_{patent_id}_{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_name)

    if existing.pdf_file_path and os.path.exists(existing.pdf_file_path):
        try:
            os.remove(existing.pdf_file_path)
        except Exception as e:
            print(f"Warning: Could not delete old PDF file: {e}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    service.update_patent(
        db,
        patent_id,
        pdf_filename=safe_name,
        pdf_file_path=file_path
    )

    return {
        "message": "PDF uploaded successfully",
        "pdf_filename": safe_name,
        "pdf_file_path": file_path
    }


@router.delete('/patents/{patent_id}/pdf', status_code=200)
async def delete_patent_pdf(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Удалить PDF файл патента (только автор или админ)"""
    import os

    existing = service.get_patent_by_id(db, patent_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Patent not found")
    if not can_edit_patent(db, current_user, patent_id):
        raise HTTPException(status_code=403, detail="You are not author of this patent")

    if existing.pdf_file_path and os.path.exists(existing.pdf_file_path):
        try:
            os.remove(existing.pdf_file_path)
        except Exception as e:
            print(f"Warning: Could not delete PDF file: {e}")

    service.update_patent(db, patent_id, pdf_filename=None, pdf_file_path=None)

    return {"message": "PDF deleted successfully"}


@router.get('/patents/{patent_id}/pdf', response_class=FileResponse)
async def download_patent_pdf(
        patent_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Скачать PDF файл патента (доступно всем)"""
    import os

    patent = service.get_patent_by_id(db, patent_id)
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")

    if not patent.pdf_file_path or not os.path.exists(patent.pdf_file_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        path=patent.pdf_file_path,
        filename=patent.pdf_filename or f"patent_{patent_id}.pdf",
        media_type="application/pdf"
    )


# ========== PERSONS ROUTES ==========

@router.get('/persons/', response_model=List[PersonDTO])
async def get_all_persons(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить всех пользователей (админ видит всех, остальные - базовую информацию)"""
    persons = service.get_all_persons(db, skip, limit)

    if not is_admin(current_user):
        # Для не-админов возвращаем базовую информацию, но с реальными данными
        limited_persons = []
        for p in persons:
            # Получаем роль и организацию
            role_name = p.role.name if p.role else None
            org_name = p.organization_rel.name if p.organization_rel else None

            limited_persons.append({
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "middle_name": p.middle_name or "",
                "email": p.email if current_user.id == p.id else "",
                "role_id": p.role_id,
                "role_name": role_name,
                "organization_id": p.organization_id,
                "organization_name": org_name,
                "login": p.login,
                "avatar_url": p.avatar_url,
                "avatar_filename": p.avatar_filename,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "last_login": p.last_login.isoformat() if p.last_login else None,
                "is_active": p.is_active,
            })
        return limited_persons

    # Для админов возвращаем полные данные
    return persons


@router.get('/persons/{person_id}', response_model=PersonDetailDTO)
async def get_person_by_id(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Получить пользователя по ID (админ - полную, остальные - базовую)"""
    person = service.get_person_by_id(db, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    if not is_admin(current_user):
        # Возвращаем только базовую информацию для не-админов
        return {
            "id": person.id,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "middle_name": person.middle_name or "",
            "email": person.email if current_user.id == person.id else "",  # Свой email видно
            "role_id": person.role_id,
            "role_name": person.role.name if person.role else "",
            "organization_id": person.organization_id,
            "organization_name": person.organization_rel.name if person.organization_rel else "",
            "login": person.login,
            "avatar_url": person.avatar_url,
            "avatar_filename": person.avatar_filename,
            "created_at": person.created_at,
            "updated_at": person.updated_at,
            "last_login": person.last_login,
            "is_active": person.is_active,
            "devices": [],
            "active_sessions_count": 0,
        }

    devices = service.get_user_devices(db, person_id)
    return PersonDetailDTO(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        middle_name=person.middle_name,
        email=person.email,
        role_id=person.role_id,
        role_name=person.role.name if person.role else None,
        organization_id=person.organization_id,
        organization_name=person.organization_rel.name if person.organization_rel else None,
        login=person.login,
        avatar_url=person.avatar_url,
        avatar_filename=person.avatar_filename,
        created_at=person.created_at,
        updated_at=person.updated_at,
        last_login=person.last_login,
        is_active=person.is_active,
        devices=devices,
        active_sessions_count=len([d for d in devices if d.refresh_tokens])
    )


@router.get('/persons/login/{login}', response_model=PersonDTO)
async def get_person_by_login(
        login: str,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Получить пользователя по логину (только админ)"""
    person = service.get_person_by_login(db, login)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get('/persons/email/{email}', response_model=PersonDTO)
async def get_person_by_email(
        email: str,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Получить пользователя по email (только админ)"""
    person = service.get_person_by_email(db, email)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.post('/persons/', status_code=status.HTTP_201_CREATED)
async def create_person(
        person: PersonCreateDTO,
        db: Session = Depends(get_db)
):
    """Создать пользователя (доступно всем - регистрация)"""
    # Проверка уникальности логина
    existing_login = service.get_person_by_login(db, person.login)
    if existing_login:
        raise HTTPException(status_code=409, detail="Login already exists")

    # Проверка уникальности email
    existing_email = service.get_person_by_email(db, person.email)
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already exists")

    # Обработка организации: если передана строка, ищем или создаём
    organization_id = person.organization_id  # из DTO
    if not organization_id and person.organization and person.organization.strip():
        org_name = person.organization.strip()
        # Ищем организацию по имени
        org = db.query(Organization).filter(Organization.name == org_name).first()
        if not org:
            org = Organization(name=org_name)
            db.add(org)
            db.flush()
        organization_id = org.id

    password_hash = get_password_hash(person.password)

    result = service.create_person(
        db,
        first_name=person.first_name,
        last_name=person.last_name,
        middle_name=person.middle_name,
        email=person.email,
        role_id=person.role_id,
        organization_id=organization_id,   # найденный или переданный id
        login=person.login,
        password_hash=password_hash,
    )

    if result is None:
        raise HTTPException(status_code=500, detail="Can't create person")

    return {"message": "Person created successfully", "id": result.id}


@router.put('/persons/{person_id}', response_model=PersonDTO)
async def update_person(
        person_id: int,
        person: PersonUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Обновить пользователя (админ — всё; владелец — через /profile)"""
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Access denied")

    existing_person = service.get_person_by_id(db, person_id)
    if existing_person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    update_data = person.dict(exclude_unset=True)

    # Если передана organization как строка — ищем или создаём организацию
    org_name = update_data.pop('organization', None)
    if org_name is not None:
        if org_name.strip():
            from application.models.dao.alloys import Organization as Org
            org = db.query(Org).filter(Org.name == org_name.strip()).first()
            if not org:
                org = Org(name=org_name.strip())
                db.add(org)
                db.flush()
            update_data['organization_id'] = org.id
        else:
            update_data['organization_id'] = None

    # Не-админ не может менять роль и статус
    if not is_admin(current_user):
        update_data.pop('role_id', None)
        update_data.pop('is_active', None)

    result = service.update_person(db, person_id, **update_data)

    if result is None:
        raise HTTPException(status_code=409, detail="Login or email already exists")

    if current_user.id == person_id:
        db.commit()

    return result


@router.delete('/persons/{person_id}', status_code=200)
async def delete_person(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Удалить пользователя (только админ)"""
    if not service.delete_person(db, person_id):
        raise HTTPException(status_code=404, detail="Person not found")
    return {"message": "Person deleted successfully"}


@router.get('/persons/role/{role_id}', response_model=List[PersonDTO])
async def get_persons_by_role(
        role_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Получить пользователей по роли (только админ)"""
    persons = service.get_persons_by_role(db, role_id)
    return persons or []


# ========== ACTIVATE / DEACTIVATE ==========

@router.post('/persons/{person_id}/deactivate', status_code=200)
async def deactivate_person(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Деактивировать аккаунт (владелец или админ)"""
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Access denied")

    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    service.update_person(db, person_id, is_active=False)

    # Отзываем все refresh-токены
    from application.models.dao.alloys import RefreshToken
    db.query(RefreshToken).filter(
        RefreshToken.person_id == person_id,
        RefreshToken.revoked == False
    ).update({"revoked": True})
    db.commit()

    return {"message": "Account deactivated"}


@router.post('/persons/{person_id}/activate', status_code=200)
async def activate_person(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Активировать аккаунт (только админ)"""
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    service.update_person(db, person_id, is_active=True)
    db.commit()
    return {"message": "Account activated"}


# ========== PROFILE ROUTES ==========

@router.put('/persons/{person_id}/profile', status_code=200)
async def update_own_profile(
        person_id: int,
        data: PersonUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Обновить свой профиль (только владелец). Роль и статус менять нельзя."""
    if current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Can only edit own profile")

    update_data = data.dict(exclude_unset=True)
    update_data.pop('role_id', None)
    update_data.pop('is_active', None)

    org_name = update_data.pop('organization', None)
    if org_name is not None:
        if org_name.strip():
            org = db.query(Organization).filter(Organization.name == org_name.strip()).first()
            if not org:
                org = Organization(name=org_name.strip())
                db.add(org)
                db.flush()
            update_data['organization_id'] = org.id
        else:
            update_data['organization_id'] = None

    result = service.update_person(db, person_id, **update_data)
    if result is None:
        raise HTTPException(status_code=409, detail="Login or email already exists")
    db.commit()
    return {"message": "Profile updated"}


# ========== AVATAR ROUTES ==========

@router.post('/persons/{person_id}/upload-avatar', status_code=200)
async def upload_avatar(
        person_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Загрузить аватарку (сам пользователь или админ)"""
    import shutil
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Access denied")
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    allowed = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(status_code=422, detail="Only image files allowed")
    upload_dir = os.path.join("uploads", "avatars")
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[1].lower()
    safe_name = f"avatar_{person_id}{ext}"
    file_path = os.path.join(upload_dir, safe_name)
    if person.avatar_filename:
        old_path = os.path.join(upload_dir, person.avatar_filename)
        if os.path.exists(old_path):
            try: os.remove(old_path)
            except: pass
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    service.update_person(db, person_id,
        avatar_filename=safe_name,
        avatar_url=f"/static/avatars/{safe_name}")
    return {"message": "Avatar uploaded", "avatar_filename": safe_name,
            "avatar_url": f"/static/avatars/{safe_name}"}


@router.delete('/persons/{person_id}/avatar', status_code=200)
async def delete_avatar(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    if not is_admin(current_user) and current_user.id != person_id:
        raise HTTPException(status_code=403, detail="Access denied")
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    if person.avatar_filename:
        file_path = os.path.join("uploads", "avatars", person.avatar_filename)
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
    service.update_person(db, person_id, avatar_filename=None, avatar_url=None)
    return {"message": "Avatar deleted"}


@router.get('/persons/{person_id}/avatar', response_class=FileResponse)
async def get_avatar(person_id: int, db: Session = Depends(get_db)):
    person = service.get_person_by_id(db, person_id)
    if not person or not person.avatar_filename:
        raise HTTPException(status_code=404, detail="Avatar not found")
    file_path = os.path.join("uploads", "avatars", person.avatar_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Avatar file not found")
    return FileResponse(path=file_path, filename=person.avatar_filename)


# ========== DEVICES ROUTES ==========

@router.get('/persons/{person_id}/devices', response_model=List[DeviceDTO])
async def get_user_devices(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Получить устройства пользователя (только админ)"""
    devices = service.get_user_devices(db, person_id)
    return devices


# ========== ROLES ROUTES ==========

@router.get('/roles/', response_model=List[RoleDTO])
async def get_all_roles(
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все роли (доступно всем, включая неавторизованных)"""
    roles = service.get_all_roles(db)
    return roles or []


@router.get('/roles/{role_id}', response_model=RoleDTO)
async def get_role_by_id(
        role_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить роль по ID (доступно всем)"""
    role = service.get_role_by_id(db, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.post('/roles/', status_code=201)
async def create_role(
        role: RoleCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Создать новую роль (только админ)"""
    result = service.create_role(db, name=role.name, description=role.description)
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create role")
    return {"message": "Role created successfully", "id": result.id}


@router.delete('/roles/{role_id}', status_code=200)
async def delete_role(
        role_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Удалить роль (только админ)"""
    if not service.delete_role(db, role_id):
        raise HTTPException(status_code=404, detail="Role not found")
    return {"message": "Role deleted successfully"}


# ========== MODELS ROUTES ==========

@router.get('/models/', response_model=List[ModelDTO])
async def get_all_models(
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все ML модели (доступно всем)"""
    models = service.get_all_models(db)
    return models or []


@router.get('/models/{model_id}', response_model=ModelDTO)
async def get_model_by_id(
        model_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить ML модель по ID (доступно всем)"""
    model = service.get_model_by_id(db, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.post('/models/', status_code=201)
async def create_model(
        model: ModelCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Создать новую ML модель (только админ)"""
    result = service.create_model(db, name=model.name, description=model.description)
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create model")
    return {"message": "Model created successfully", "id": result.id}


@router.delete('/models/{model_id}', status_code=200)
async def delete_model(
        model_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Удалить модель (только админ)"""
    if not service.delete_model(db, model_id):
        raise HTTPException(status_code=404, detail="Model not found")
    return {"message": "Model deleted successfully"}


# ========== ORGANIZATIONS ROUTES ==========

@router.get('/organizations/', response_model=List[OrganizationDTO])
async def get_all_organizations(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить все организации (доступно всем)"""
    orgs = service.get_all_organizations(db, skip, limit)
    return orgs or []


@router.get('/organizations/{org_id}', response_model=OrganizationDTO)
async def get_organization_by_id(
        org_id: int,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить организацию по ID (доступно всем)"""
    org = service.get_organization_by_id(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post('/organizations/', status_code=201)
async def create_organization(
        org: OrganizationCreateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Создать новую организацию (только админ)"""
    result = service.create_organization(
        db,
        name=org.name,
        short_name=org.short_name,
        inn=org.inn,
        ogrn=org.ogrn,
        address=org.address,
        phone=org.phone,
        email=org.email,
        website=org.website
    )
    if result is None:
        raise HTTPException(status_code=500, detail="Can't create organization")
    return {"message": "Organization created successfully", "id": result.id}


@router.put('/organizations/{org_id}', response_model=OrganizationDTO)
async def update_organization(
        org_id: int,
        org: OrganizationUpdateDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Обновить организацию (только админ)"""
    update_data = org.dict(exclude_unset=True)
    result = service.update_organization(db, org_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result


@router.delete('/organizations/{org_id}', status_code=200)
async def delete_organization(
        org_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Удалить организацию (только админ)"""
    if not service.delete_organization(db, org_id):
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"message": "Organization deleted successfully"}


# ========== AUTH ROUTES ==========

@router.post("/auth/login", response_model=LoginResponseDTO)
async def login(request: LoginRequestDTO, request_obj: Request, db: Session = Depends(get_db)):
    """Вход в систему (доступно всем)"""
    person = service.get_person_by_login(db, request.login)
    if not person:
        person = service.get_person_by_email(db, request.login)

    if not person:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    if not verify_password(request.password, person.password_hash):
        # Логируем формат хэша для диагностики (первые 10 символов)
        hash_prefix = person.password_hash[:10] if person.password_hash else "None"
        print(f"[LOGIN] Password mismatch for '{request.login}'. Hash prefix: {hash_prefix}")
        raise HTTPException(status_code=401, detail="Неверный пароль")

    if not person.is_active:
        raise HTTPException(status_code=401, detail="Аккаунт деактивирован")

    user_agent = request_obj.headers.get("user-agent", "Unknown")
    fingerprint = create_device_fingerprint(user_agent)

    device = service.get_device_by_fingerprint(db, fingerprint)
    if not device:
        device = service.create_device(
            db,
            device_name=request.device_name or user_agent[:100],
            device_fingerprint=fingerprint,
            is_trusted=False
        )
    else:
        service.update_device_last_seen(db, device.id)

    access_token = create_access_token(person.id, person.login)
    refresh_token = create_refresh_token_in_db(db, person.id, device_id=device.id)

    service.update_last_login(db, person.id)

    return LoginResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/auth/refresh", response_model=RefreshResponseDTO)
async def refresh_token(request: RefreshRequestDTO, db: Session = Depends(get_db)):
    """
    Обновление access токена с ротацией refresh токена.
    Старый токен отзывается, выдаётся новый.
    """
    from application.models.dao.alloys import RefreshToken as RT

    token_hash = hash_token(request.refresh_token)

    db_token = db.query(RT).filter(
        RT.token_hash == token_hash,
        RT.revoked == False,
        RT.expires_at > datetime.utcnow()
    ).first()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    person = service.get_person_by_id(db, db_token.person_id)
    if not person:
        raise HTTPException(status_code=401, detail="User not found")

    # Деактивированный пользователь не может обновить токен
    if not person.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    device_id = db_token.device_id

    # Ротация: отзываем использованный токен
    db_token.revoked = True
    db.commit()

    # Выдаём новые токены
    access_token     = create_access_token(person.id, person.login)
    new_refresh_token = create_refresh_token_in_db(db, person.id, device_id=device_id)

    return RefreshResponseDTO(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post("/auth/logout")
async def logout(request: LogoutRequestDTO, db: Session = Depends(get_db)):
    """Выход из системы (доступно всем)"""
    revoked = revoke_refresh_token(db, request.refresh_token)
    if not revoked:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"message": "Logged out successfully"}


@router.post('/persons/{person_id}/reset-password', status_code=200)
async def reset_person_password(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Сброс пароля пользователя (только админ) — устанавливает пароль 'password123'"""
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    new_hash = get_password_hash("password123")
    service.update_person(db, person_id, password_hash=new_hash)
    db.commit()
    return {"message": "Password reset to 'password123'"}


@router.get("/auth/debug-hash/{login}")
async def debug_hash(login: str, db: Session = Depends(get_db)):
    """
    ВРЕМЕННЫЙ диагностический эндпоинт.
    Показывает первые 10 символов хэша пароля пользователя.
    Удалите после диагностики!
    """
    person = service.get_person_by_login(db, login)
    if not person:
        raise HTTPException(status_code=404, detail="Not found")
    h = person.password_hash or ""
    return {
        "login": person.login,
        "hash_length": len(h),
        "hash_prefix": h[:15],
        "is_bcrypt": h.startswith(("$2b$", "$2a$", "$2y$")),
        "is_md5_len": len(h) == 32,
    }


@router.post('/persons/{person_id}/reset-password', status_code=200)
async def reset_person_password(
        person_id: int,
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Сброс пароля пользователя администратором — устанавливает пароль 'password123'"""
    person = service.get_person_by_id(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    new_hash = get_password_hash("password123")
    service.update_person(db, person_id, password_hash=new_hash)
    db.commit()
    return {"message": "Password reset to 'password123'. Please change it after login."}


@router.post("/auth/change-password")
async def change_password(
        data: ChangePasswordDTO,
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Смена пароля (текущий пользователь)"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный текущий пароль")
    new_hash = get_password_hash(data.new_password)
    service.update_person(db, current_user.id, password_hash=new_hash)
    db.commit()
    return {"message": "Пароль успешно изменён"}


@router.get("/auth/me")
async def get_me(
        current_user: Person = Depends(get_current_user),
        db: Session = Depends(get_auth_db)
):
    """Получить данные текущего пользователя (по access token)"""
    role_name = None
    if current_user.role_id:
        role = service.get_role_by_id(db, current_user.role_id)
        role_name = role.name if role else None

    return {
        "id": current_user.id,
        "login": current_user.login,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "middle_name": getattr(current_user, "middle_name", None),
        "email": getattr(current_user, "email", None),
        "role_id": current_user.role_id,
        "role_name": role_name,
        "is_active": current_user.is_active,
    }


@router.get("/auth/profile")
async def get_profile(
        current_user: Person = Depends(get_current_user),
        db: Session = Depends(get_auth_db)
):
    """Полный профиль текущего пользователя с устройствами"""
    role_name = None
    if current_user.role_id:
        role = service.get_role_by_id(db, current_user.role_id)
        role_name = role.name if role else None

    try:
        devices = service.get_user_devices(db, current_user.id)
    except Exception:
        devices = []

    return {
        "id": current_user.id,
        "login": current_user.login,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "middle_name": getattr(current_user, "middle_name", None),
        "email": getattr(current_user, "email", None),
        "role_id": current_user.role_id,
        "role_name": role_name,
        "is_active": current_user.is_active,
        "devices": [{"id": d.id, "device_name": d.device_name} for d in (devices or [])],
    }


# ========== ADMIN ROUTES ==========

@router.post('/admin/grant_role', status_code=200)
async def grant_role_to_organization(
        payload: GrantRoleToOrganizationDTO = Body(...),
        db: Session = Depends(get_db),
        current_user: Person = Depends(require_admin)
):
    """Выдать роль всем пользователям организации (только админ)"""
    persons = service.get_persons_by_organization(db, payload.organization_id)
    if not persons:
        raise HTTPException(status_code=404, detail="No persons found for this organization")

    updated = 0
    for person in persons:
        if person.role_id != payload.role_id:
            service.update_person(db, person.id, role_id=payload.role_id)
            updated += 1

    return {
        "message": "Role granted successfully",
        "updated": updated,
        "organization_id": payload.organization_id,
        "role_id": payload.role_id
    }


# ========== ML ROUTES ==========

ml_infer = MLInference()


class MLPredictElementDTO(BaseModel):
    element_id: int
    percentage: float


class MLPredictRequestDTO(BaseModel):
    ml_model_id: int
    category: str
    rolling_type: str
    temperature: Optional[float] = None
    size: Optional[float] = None
    elements: List[MLPredictElementDTO] = []


@router.post("/ml/predict", status_code=200)
async def ml_predict(
        payload: MLPredictRequestDTO,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """ML предсказание свойств сплава (доступно всем)"""
    all_elements = service.get_all_elements(db)
    id_to_symbol = {int(e.id): str(e.symbol).lower() for e in (all_elements or [])}

    composition = {}
    for it in payload.elements:
        sym = id_to_symbol.get(int(it.element_id))
        if not sym:
            continue
        composition[sym] = float(it.percentage)

    try:
        value = ml_infer.predict(
            ml_model_id=payload.ml_model_id,
            category=payload.category,
            rolling_type=payload.rolling_type,
            temperature=payload.temperature,
            size=payload.size,
            composition_by_symbol=composition,
        )

        # конвертируем numpy типы в стандартные Python типы
        if hasattr(value, 'item'):
            value = value.item()  # numpy.float32 -> float
        elif isinstance(value, (list, tuple)):
            value = [v.item() if hasattr(v, 'item') else v for v in value]

        # Дополнительно преобразуем в float для уверенности
        if isinstance(value, (int, float)):
            value = float(value)

        return {"prop_value": value}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML error: {str(e)}")


@router.post("/api/ml/predict", status_code=200)   # для обработки "двойного /api"
async def ml_predict_fallback(payload: MLPredictRequestDTO, db: Session = Depends(get_db),
                              current_user: Optional[Person] = Depends(get_current_user_optional)):
    return await ml_predict(payload, db, current_user)

# ========== ML ПОИСК ПОХОЖИХ СПЛАВОВ ==========

class FindSimilarRequestDTO(BaseModel):
    composition: Dict[str, float]
    limit: int = 10


@router.post("/ml/find-similar", status_code=200)
async def find_similar_alloys(
        payload: FindSimilarRequestDTO,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    from math import sqrt

    alloys = service.get_all_alloys(db, limit=1000)

    results = []
    target_comp = payload.composition

    for alloy in alloys:
        alloy_elements = service.get_alloy_elements_with_percentages(db, alloy.id)
        alloy_comp = {e['element_symbol']: e['percentage'] for e in alloy_elements}

        all_symbols = set(target_comp.keys()) | set(alloy_comp.keys())
        distance = 0.0
        for symbol in all_symbols:
            target_pct = target_comp.get(symbol, 0)
            alloy_pct = alloy_comp.get(symbol, 0)
            distance += (target_pct - alloy_pct) ** 2
        distance = sqrt(distance)

        similarity = max(0, 100 - distance)

        results.append({
            "alloy_id": alloy.id,
            "patent_name": alloy.patent.patent_name if alloy.patent else None,
            "similarity": round(similarity, 2),
            "composition": alloy_comp
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)

    return {"similar_alloys": results[:payload.limit]}


class MLModelsListDTO(BaseModel):
    """Список доступных ML моделей"""
    id: int
    name: str
    description: str
    category: str


class MLPredictResponseDTO(BaseModel):
    """Ответ ML предсказания"""
    prop_value: float
    category: str
    confidence: float
    model_used: str


@router.get("/ml/models", response_model=List[MLModelsListDTO])
async def get_ml_models(
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """Получить список доступных ML моделей"""
    return [
        {"id": 1, "name": "Random Forest", "description": "Ансамбль деревьев решений", "category": "all"},
        {"id": 2, "name": "XGBoost", "description": "Градиентный бустинг", "category": "all"},
        {"id": 3, "name": "LightGBM", "description": "Быстрый градиентный бустинг", "category": "all"},
        {"id": 4, "name": "Gradient Boosting", "description": "Градиентный бустинг", "category": "all"},
    ]


@router.post("/ml/predict/v2", response_model=MLPredictResponseDTO)
async def ml_predict_v2(
        payload: MLPredictRequestDTO,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """ML предсказание свойств сплава с использованием обученных моделей."""
    all_elements = service.get_all_elements(db)
    id_to_symbol = {int(e.id): str(e.symbol).lower() for e in (all_elements or [])}

    composition = {}
    for it in payload.elements:
        sym = id_to_symbol.get(int(it.element_id))
        if sym:
            composition[sym] = float(it.percentage)

    try:
        value = ml_infer.predict(
            ml_model_id=payload.ml_model_id,
            category=payload.category,
            rolling_type=payload.rolling_type,
            size=payload.size,
            composition_by_symbol=composition,
            temperature=payload.temperature
        )

        # 🔧 ИСПРАВЛЕНИЕ: конвертируем numpy типы
        if hasattr(value, 'item'):
            value = value.item()
        value = float(value)

        category_used = payload.category
        if not category_used or category_used == "unknown":
            category_used, confidence = ml_infer.predict_category(composition, payload.size)
        else:
            _, confidence = ml_infer.predict_category(composition, payload.size)

        return MLPredictResponseDTO(
            prop_value=round(value, 1),
            category=category_used,
            confidence=round(float(confidence), 4),
            model_used="XGBoost" if payload.ml_model_id == 2 else "RandomForest"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML error: {str(e)}")


@router.post("/ml/classify", response_model=Dict)
async def classify_alloy(
        payload: MLPredictRequestDTO,
        db: Session = Depends(get_db),
        current_user: Optional[Person] = Depends(get_current_user_optional)
):
    """
    Определить категорию сплава по составу (без предсказания свойств)
    """
    all_elements = service.get_all_elements(db)
    id_to_symbol = {int(e.id): str(e.symbol).lower() for e in (all_elements or [])}

    composition = {}
    for it in payload.elements:
        sym = id_to_symbol.get(int(it.element_id))
        if sym:
            composition[sym] = float(it.percentage)

    try:
        category, confidence = ml_infer.predict_category(composition, payload.size)

        # 🔧 ИСПРАВЛЕНИЕ: конвертируем numpy типы в стандартные Python типы
        if hasattr(confidence, 'item'):
            confidence = confidence.item()

        return {
            "category": category,
            "confidence": round(float(confidence), 4),
            "composition": composition
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")


# ========== REPORT ROUTES ==========

@router.get("/reports/download-pdf")
async def download_report_html(
        db: Session = Depends(get_db),
        current_user: Person = Depends(get_current_user)
):
    """Скачать отчёт в HTML"""
    is_admin_user = is_admin(current_user)

    if is_admin_user:
        persons = service.get_all_persons(db)
        predictions = service.get_all_predictions(db, limit=10000)
        alloys = service.get_all_alloys(db)
        patents = service.get_all_patents(db)
        models = service.get_all_models(db)
        elements = service.get_all_elements(db)
    else:
        predictions = service.get_predictions_by_person(db, current_user.id)
        models = service.get_all_models(db)

    # Статистика
    cat_count = {}
    roll_count = {}
    model_count = {}
    model_dict = {m.id: m.name for m in models}

    for p in predictions:
        cat = p.category or "Не указана"
        cat_count[cat] = cat_count.get(cat, 0) + 1
        roll = p.rolling_type or "Не указан"
        roll_count[roll] = roll_count.get(roll, 0) + 1
        mn = model_dict.get(p.ml_model_id, f"Модель #{p.ml_model_id}")
        model_count[mn] = model_count.get(mn, 0) + 1

    last_preds = sorted(predictions, key=lambda x: x.created_at or datetime.min, reverse=True)[:20]

    title = "Сводный отчёт системы" if is_admin_user else "Персональный отчёт"

    html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>{title}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;padding:30px;color:#1e293b;background:#f8fafc}}
h1{{color:#1e40af;border-bottom:2px solid #2563eb;padding-bottom:10px}}
h2{{color:#2563eb;margin-top:24px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}
th{{background:#2563eb;color:#fff;padding:8px 12px;text-align:left;font-size:12px}}
td{{padding:8px 12px;border-bottom:1px solid #e2e8f0;font-size:13px}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-bottom:20px}}
.stats{{display:flex;gap:12px;flex-wrap:wrap}}.stat{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px;text-align:center;min-width:120px}}
.stat .n{{font-size:28px;font-weight:700;color:#2563eb}}.stat .l{{font-size:11px;color:#64748b;text-transform:uppercase}}
.footer{{text-align:center;margin-top:30px;color:#94a3b8;font-size:11px}}</style></head><body>
<h1>{title}</h1><p>Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Пользователь: {current_user.last_name} {current_user.first_name}</p>
<div class="stats"><div class="stat"><div class="n">{len(predictions)}</div><div class="l">Прогнозов</div></div>"""

    if is_admin_user:
        html += f"""<div class="stat"><div class="n">{len(persons)}</div><div class="l">Пользователей</div></div>
<div class="stat"><div class="n">{len(alloys)}</div><div class="l">Сплавов</div></div>
<div class="stat"><div class="n">{len(patents)}</div><div class="l">Патентов</div></div>"""

    html += "</div>"

    if cat_count:
        html += '<div class="card"><h2>По категориям</h2><table><tr><th>Категория</th><th>Кол-во</th></tr>'
        for c, n in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{c}</td><td>{n}</td></tr>"
        html += "</table></div>"

    if roll_count:
        html += '<div class="card"><h2>По прокатке</h2><table><tr><th>Тип</th><th>Кол-во</th></tr>'
        for c, n in sorted(roll_count.items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{c}</td><td>{n}</td></tr>"
        html += "</table></div>"

    if model_count:
        html += '<div class="card"><h2>По моделям</h2><table><tr><th>Модель</th><th>Кол-во</th></tr>'
        for c, n in sorted(model_count.items(), key=lambda x: x[1], reverse=True):
            html += f"<tr><td>{c}</td><td>{n}</td></tr>"
        html += "</table></div>"

    if last_preds:
        html += '<div class="card"><h2>Последние прогнозы</h2><table><tr><th>ID</th><th>Категория</th><th>Прокатка</th><th>МПа</th><th>Дата</th></tr>'
        for p in last_preds:
            html += f"<tr><td>{p.id}</td><td>{p.category or '-'}</td><td>{p.rolling_type or '-'}</td><td>{p.prop_value or '-'}</td><td>{p.created_at.strftime('%d.%m.%Y') if p.created_at else '-'}</td></tr>"
        html += "</table></div>"

    html += f'<div class="footer">AlloyVault &copy; {datetime.now().year}</div></body></html>'

    return StreamingResponse(
        io.BytesIO(html.encode('utf-8')),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=Otchet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"}
    )