from pydantic import BaseModel
from typing import (
    Deque, Dict, List, Optional, Sequence, Set, Tuple, Union
)

class PredictionElementAssociationDTO(BaseModel):
    """ DTO для получения процентного содержания элементов в предсказанном сплаве  """
    prediction_id: int
    element_id: int
    percentage: float
