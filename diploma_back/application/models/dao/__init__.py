# application/models/dao/__init__.py
"""
Модуль DAO (Data Access Objects)
"""

from .alloys import (
    Base,
    Alloy, Patent, ChemicalElement, Prediction, Person, Role, Model,
    Organization, Device, RefreshToken, PatentAuthor,
    alloy_element_association, prediction_element_association
)