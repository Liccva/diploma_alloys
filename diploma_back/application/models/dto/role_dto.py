from pydantic import BaseModel
from typing import (
    Deque, Dict, List, Optional, Sequence, Set, Tuple, Union
)

class RoleDTO(BaseModel):
    """ DTO для получения, добавления, обновления роли пользователя """
    id: int
    name: str
    description: Optional[str]

class RoleCreateDTO(BaseModel):
    """ DTO для получения, добавления, обновления роли пользователя """
    name: str
    description: Optional[str]