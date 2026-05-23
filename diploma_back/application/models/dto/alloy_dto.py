from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== DTO ДЛЯ ВЫВОДА (RESPONSE) ==========
class AlloyDTO(BaseModel):
    """DTO для получения информации о сплаве"""
    id: int
    prop_value: Optional[float] = Field(None, description="Значение свойства (может быть NULL)")
    temperature: Optional[float] = Field(None, description="Температура испытания")
    category: Optional[str] = Field(None, description="Категория сплава")
    rolling_type: Optional[str] = Field(None, description="Тип прокатки")
    patent_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = Field(None, description="ID пользователя, добавившего сплав")
    created_by_name: Optional[str] = Field(None, description="Имя создателя (для удобства)")

    class Config:
        from_attributes = True


# ========== DTO ДЛЯ СОЗДАНИЯ (CREATE) ==========
class AlloyCreateDTO(BaseModel):
    """DTO для создания сплава"""
    prop_value: Optional[float] = Field(None, description="Значение свойства (опционально)")
    temperature: Optional[float] = Field(None, description="Температура испытания")
    category: Optional[str] = Field(None, max_length=100)
    rolling_type: Optional[str] = Field(None, max_length=50)
    patent_id: int = Field(..., gt=0, description="ID патента")

    class Config:
        json_schema_extra = {
            "example": {
                "prop_value": 850.5,
                "temperature": 950.0,
                "category": "steel",
                "rolling_type": "hot",
                "patent_id": 1
            }
        }


# ========== DTO ДЛЯ ОБНОВЛЕНИЯ (UPDATE) ==========
class AlloyUpdateDTO(BaseModel):
    """DTO для обновления сплава (все поля опциональны)"""
    prop_value: Optional[float] = Field(None, description="Значение свойства")
    temperature: Optional[float] = Field(None, description="Температура испытания")
    category: Optional[str] = Field(None, max_length=100)
    rolling_type: Optional[str] = Field(None, max_length=50)
    patent_id: Optional[int] = Field(None, gt=0, description="ID патента")

    class Config:
        json_schema_extra = {
            "example": {
                "prop_value": 900.0,
                "temperature": 1000.0,
                "category": "steel",
                "rolling_type": "cold"
            }
        }


# ========== DTO ДЛЯ СПЛАВА С ЭЛЕМЕНТАМИ (ДЕТАЛЬНЫЙ) ==========
class AlloyElementDTO(BaseModel):
    """DTO для элемента сплава с процентным содержанием"""
    element_id: int
    element_symbol: str
    element_name: str
    percentage: float


class AlloyDetailDTO(AlloyDTO):
    """Расширенный DTO для сплава со списком элементов"""
    elements: List[AlloyElementDTO] = Field(default_factory=list, description="Состав сплава")

    class Config:
        from_attributes = True


# ========== DTO ДЛЯ СОЗДАНИЯ СПЛАВА С ЭЛЕМЕНТАМИ ==========
class AlloyWithElementsCreateDTO(BaseModel):
    """DTO для создания сплава с элементами (одним запросом)"""
    # Поля сплава
    prop_value: Optional[float] = None
    temperature: Optional[float] = None
    category: Optional[str] = None
    rolling_type: Optional[str] = None
    patent_id: int = Field(..., gt=0)

    # Элементы с процентами
    elements: List[AlloyElementDTO] = Field(..., min_length=1, description="Состав сплава")

    class Config:
        json_schema_extra = {
            "example": {
                "prop_value": 850.5,
                "temperature": 950.0,
                "category": "steel",
                "rolling_type": "hot",
                "patent_id": 1,
                "elements": [
                    {"element_id": 26, "element_symbol": "Fe", "element_name": "Железо", "percentage": 95.5},
                    {"element_id": 6, "element_symbol": "C", "element_name": "Углерод", "percentage": 0.5},
                    {"element_id": 24, "element_symbol": "Cr", "element_name": "Хром", "percentage": 4.0}
                ]
            }
        }


# ========== DTO ДЛЯ ФИЛЬТРАЦИИ ==========
class AlloyFilterDTO(BaseModel):
    """DTO для фильтрации списка сплавов"""
    category: Optional[str] = Field(None, description="Категория сплава")
    rolling_type: Optional[str] = Field(None, description="Тип прокатки")
    patent_id: Optional[int] = Field(None, description="ID патента")
    min_prop_value: Optional[float] = Field(None, description="Минимальное значение свойства")
    max_prop_value: Optional[float] = Field(None, description="Максимальное значение свойства")
    min_temperature: Optional[float] = Field(None, description="Минимальная температура")
    max_temperature: Optional[float] = Field(None, description="Максимальная температура")
    element_ids: Optional[List[int]] = Field(None, description="ID элементов в составе")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "steel",
                "min_prop_value": 500,
                "max_prop_value": 1000
            }
        }