from pydantic import BaseModel


class ChemicalElementDTO(BaseModel):
    """ DTO для добавления, получения химического элемента """
    id: int
    name: str
    atomic_number: int
    symbol: str

class ChemicalElementCreateDTO(BaseModel):
    """ DTO для создания химического элемента """
    name: str
    atomic_number: int
    symbol: str
