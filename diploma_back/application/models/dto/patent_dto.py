from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .patent_author_dto import PatentAuthorDTO, PatentAuthorCreateDTO


class PatentDTO(BaseModel):
    """DTO для вывода информации о патенте"""
    id: int
    patent_number: str
    country: Optional[str] = None
    patent_name: str
    filing_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    assignee: Optional[str] = None
    ipc_code: Optional[str] = None
    description: Optional[str] = None
    pdf_filename: Optional[str] = None  # Имя файла PDF
    pdf_file_path: Optional[str] = None  # Полный путь к файлу
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PatentDetailDTO(PatentDTO):
    """Расширенный DTO для патента с авторами"""
    authors: List[PatentAuthorDTO] = Field(default_factory=list, description="Авторы патента")


class PatentCreateDTO(BaseModel):
    """DTO для создания патента"""
    patent_number: str = Field(..., max_length=50)
    country: Optional[str] = Field(None, max_length=10)
    patent_name: str = Field(..., max_length=500)
    filing_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    assignee: Optional[str] = Field(None, max_length=300)
    ipc_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)


class PatentCreateWithAuthorsDTO(PatentCreateDTO):
    """DTO для создания патента вместе с авторами"""
    authors: List[PatentAuthorCreateDTO] = Field(default_factory=list, description="Авторы патента")


class PatentUpdateDTO(BaseModel):
    """DTO для обновления патента"""
    patent_number: Optional[str] = Field(None, max_length=50)
    country: Optional[str] = Field(None, max_length=10)
    patent_name: Optional[str] = Field(None, max_length=500)
    filing_date: Optional[datetime] = None
    issue_date: Optional[datetime] = None
    assignee: Optional[str] = Field(None, max_length=300)
    ipc_code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    pdf_filename: Optional[str] = Field(None, max_length=255)
    pdf_file_path: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)


class PatentUploadPdfResponseDTO(BaseModel):
    """DTO для ответа после загрузки PDF"""
    message: str
    pdf_filename: str
    pdf_file_path: str


class PatentListDTO(BaseModel):
    """DTO для пагинированного списка патентов"""
    total: int
    page: int
    per_page: int
    items: List[PatentDTO]