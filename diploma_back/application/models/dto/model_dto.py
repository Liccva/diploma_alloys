from pydantic import BaseModel
from typing import (
    Deque, Dict, List, Optional, Sequence, Set, Tuple, Union
)

class ModelDTO(BaseModel):
    """ DTO для получения новой модели """
    id: int
    name: str
    description: Optional[str]

class ModelCreateDTO(BaseModel):
    """ DTO для добавления новой модели """
    name: str
    description: Optional[str]
