# application/models/__init__.py
"""
Модуль моделей данных
"""

from .dao.alloys import (
    Base,
    Alloy, Patent, ChemicalElement, Prediction, Person, Role, Model,
    Organization, Device, RefreshToken, PatentAuthor,
    alloy_element_association, prediction_element_association
)