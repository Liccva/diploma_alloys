from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== DTO ДЛЯ ВЫВОДА (RESPONSE) ==========
class PredictionDTO(BaseModel):
    """DTO для вывода информации о прогнозе"""
    id: int
    prop_value: Optional[float] = Field(None, description="Прогнозируемое значение")
    temperature: Optional[float] = Field(None, description="Температура")
    category: Optional[str] = Field(None, description="Категория")
    ml_model_id: int
    ml_model_name: Optional[str] = Field(None, description="Название ML модели")
    rolling_type: Optional[str] = Field(None, description="Тип прокатки")
    person_id: int
    person_name: Optional[str] = Field(None, description="Имя пользователя")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== DTO ДЛЯ СОЗДАНИЯ (CREATE) ==========
class PredictionCreateDTO(BaseModel):
    """DTO для создания прогноза"""
    prop_value: Optional[float] = Field(None, description="Прогнозируемое значение")
    temperature: Optional[float] = Field(None, description="Температура")
    category: Optional[str] = Field(None, max_length=100)
    ml_model_id: int = Field(..., gt=0, description="ID ML модели")
    rolling_type: Optional[str] = Field(None, max_length=50)
    person_id: int = Field(..., gt=0, description="ID пользователя")

    class Config:
        json_schema_extra = {
            "example": {
                "prop_value": 850.5,
                "temperature": 950.0,
                "category": "steel",
                "ml_model_id": 1,
                "rolling_type": "hot",
                "person_id": 1
            }
        }


# ========== DTO ДЛЯ ОБНОВЛЕНИЯ (UPDATE) ==========
class PredictionUpdateDTO(BaseModel):
    """DTO для обновления прогноза (все поля опциональны)"""
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = Field(None, max_length=100)
    ml_model_id: Optional[int] = Field(None, gt=0)
    rolling_type: Optional[str] = Field(None, max_length=50)


# ========== DTO ДЛЯ ПРОГНОЗА С ЭЛЕМЕНТАМИ ==========
class PredictionElementDTO(BaseModel):
    """DTO для элемента прогноза с процентным содержанием"""
    element_id: int
    element_symbol: str
    element_name: str
    percentage: float = Field(..., ge=0, le=100)


class PredictionDetailDTO(PredictionDTO):
    """Расширенный DTO для прогноза со списком элементов"""
    elements: List[PredictionElementDTO] = Field(default_factory=list, description="Состав сплава")


# ========== DTO ДЛЯ СОЗДАНИЯ ПРОГНОЗА С ЭЛЕМЕНТАМИ ==========
class PredictionWithElementsCreateDTO(BaseModel):
    """DTO для создания прогноза с элементами (одним запросом)"""
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None
    ml_model_id: int = Field(..., gt=0)
    rolling_type: Optional[str] = None
    person_id: int = Field(..., gt=0)
    elements: List[PredictionElementDTO] = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "prop_value": 850.5,
                "temperature": 950.0,
                "category": "steel",
                "ml_model_id": 1,
                "rolling_type": "hot",
                "person_id": 1,
                "elements": [
                    {"element_id": 26, "element_symbol": "Fe", "element_name": "Железо", "percentage": 95.5},
                    {"element_id": 6, "element_symbol": "C", "element_name": "Углерод", "percentage": 0.5}
                ]
            }
        }


# ========== DTO ДЛЯ ФИЛЬТРАЦИИ ПРОГНОЗОВ ==========
class PredictionFilterDTO(BaseModel):
    """DTO для фильтрации списка прогнозов"""
    category: Optional[str] = None
    ml_model_id: Optional[int] = None
    person_id: Optional[int] = None
    rolling_type: Optional[str] = None
    min_prop_value: Optional[float] = None
    max_prop_value: Optional[float] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None