from pydantic import BaseModel
from typing import (
    Deque, Dict, List, Optional, Sequence, Set, Tuple, Union
)

class AlloyElementAssociationDTO(BaseModel):
    """ DTO для получения процентного содержания элементов в сплаве """
    alloy_id: int
    element_id: int
    percentage: float

class AlloyElementResponseDTO(BaseModel):
    element_id: int
    element_name: str
    element_symbol: str
    element_atomic_number: int
    percentage: float
