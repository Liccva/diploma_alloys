# application/utils/patent_utils.py
"""Утилиты для работы с патентами и IPC классификацией"""

from datetime import datetime
from typing import Optional, List, Dict


def get_category_by_ipc(ipc_code: str) -> str:
    """
    Определить категорию сплава по IPC коду

    IPC классификация для металлов и сплавов:
    - C22C19/05: Никелевые суперсплавы
    - C22C38: Стали
    - C22C21: Алюминиевые сплавы
    - C22C14: Титановые сплавы
    """
    if not ipc_code:
        return "unknown"

    # Сплавы на основе никеля
    if ipc_code.startswith("C22C19/05"):
        return "nickel_based_superalloy"
    elif ipc_code.startswith("C22C19/07"):
        return "cobalt_based_alloy"

    # Стали
    if ipc_code.startswith("C22C38"):
        return "steel"

    # Цветные металлы
    if ipc_code.startswith("C22C21"):
        return "aluminum_alloy"
    elif ipc_code.startswith("C22C14"):
        return "titanium_alloy"
    elif ipc_code.startswith("C22C9"):
        return "copper_alloy"
    elif ipc_code.startswith("C22C23"):
        return "magnesium_alloy"

    # Чугуны
    if ipc_code.startswith("C22C37"):
        return "cast_iron"

    return "other"


def parse_date(date_str: str) -> Optional[datetime]:
    """Преобразовать дату из формата YYYY.MM.DD"""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y.%m.%d")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None


def parse_percentage(value_str: str) -> float:
    """
    Преобразовать строку процента в число

    Примеры:
    "3.2-3.9%" -> 3.55 (среднее)
    "0.02%" -> 0.02
    """
    if not value_str:
        return 0.0

    # Убираем знак процента
    value_str = value_str.replace("%", "").strip()

    if "-" in value_str:
        parts = value_str.split("-")
        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return round((low + high) / 2, 3)
        except ValueError:
            return 0.0
    else:
        try:
            return float(value_str)
        except ValueError:
            return 0.0


def clean_compositions(compositions: List[Dict]) -> List[Dict]:
    """Очистить состав от дубликатов и ошибок"""
    cleaned = []
    seen_elements = set()

    for comp in compositions:
        element = comp.get("element")
        value = comp.get("value", "")

        # Пропускаем пустые значения
        if value in [".%", "", None]:
            continue

        # Пропускаем явные ошибки (B 100% - это ошибка)
        if element == "B" and "100" in value:
            continue

        # Сохраняем только первое вхождение каждого элемента
        if element in seen_elements:
            continue
        seen_elements.add(element)

        cleaned.append({"element": element, "value": value})

    return cleaned