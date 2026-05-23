from pydantic import BaseModel, Field
from typing import Optional


class PatentAuthorDTO(BaseModel):
    """DTO для вывода информации об авторе патента"""
    id: int
    patent_id: int
    author_name: str
    author_order: int
    person_id: Optional[int] = None

    class Config:
        from_attributes = True


class PatentAuthorCreateDTO(BaseModel):
    """
    DTO для создания автора патента.
    patent_id НЕ включён — он берётся из URL (/patents/{patent_id}/authors
    или из тела PatentCreateWithAuthorsDTO на уровне роута).
    """
    author_name: str = Field(..., min_length=1, max_length=200, description="Имя автора")
    author_order: int = Field(..., ge=1, description="Порядковый номер автора")
    person_id: Optional[int] = Field(None, description="ID пользователя в системе (если есть)")


class PatentAuthorUpdateDTO(BaseModel):
    """DTO для обновления данных автора"""
    author_name: Optional[str] = Field(None, min_length=1, max_length=200)
    author_order: Optional[int] = Field(None, ge=1)
