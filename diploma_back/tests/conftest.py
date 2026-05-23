"""
Конфигурационный файл для pytest
Содержит фикстуры и настройки для всех тестов
"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь для импорта
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Импортируем только необходимые модули
from application.models.dao.alloys import Base
from application.services import repository_service

# ========== НАСТРОЙКА ТЕСТОВОЙ БД ==========

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# ========== ФИКСТУРЫ ДЛЯ ТЕСТОВ РЕПОЗИТОРИЯ ==========

@pytest.fixture(scope="session")
def db_engine():
    """Фикстура для движка БД на всю сессию"""
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Фикстура для сессии БД (создается для каждого теста)
    Использует транзакцию, которая откатывается после теста
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ========== ФИКСТУРЫ ДЛЯ ТЕСТОВ API ==========

@pytest.fixture(scope="function")
def client():
    """Фикстура для тестового клиента FastAPI"""
    # Импортируем app только здесь, чтобы избежать циклических импортов
    from main import app
    from fastapi.testclient import TestClient
    return TestClient(app)


# ========== КЛАСС-КОНТЕЙНЕР ДЛЯ ТЕСТОВЫХ ДАННЫХ ==========

class TestDataContainer:
    """Контейнер для хранения тестовых данных между фикстурами"""

    def __init__(self):
        self.researcher_role = None
        self.engineer_role = None
        self.fe_element = None
        self.c_element = None
        self.si_element = None
        self.patent1 = None
        self.patent2 = None
        self.rf_model = None
        self.nn_model = None
        self.person1 = None
        self.person2 = None


@pytest.fixture(scope="function")
def test_data(db_session) -> TestDataContainer:
    """Фикстура для создания тестовых данных перед тестами"""
    import time

    container = TestDataContainer()
    timestamp = int(time.time() * 1000)

    # Создаем роли
    container.researcher_role = repository_service.create_role(
        db_session,
        name=f'research_{timestamp}',
        description='Научный сотрудник'
    )
    container.engineer_role = repository_service.create_role(
        db_session,
        name=f'engineer_{timestamp}',
        description='Инженер'
    )

    # Создаем химические элементы
    container.fe_element = repository_service.create_chemical_element(
        db_session, 'Железо', 26, f'Fe_{timestamp}'
    )
    container.c_element = repository_service.create_chemical_element(
        db_session, 'Углерод', 6, f'C_{timestamp}'
    )
    container.si_element = repository_service.create_chemical_element(
        db_session, 'Кремний', 14, f'Si_{timestamp}'
    )

    # Создаем патенты
    container.patent1 = repository_service.create_patent(
        db_session,
        patent_number=f"PAT{timestamp}1",
        patent_name='Патент 1',
        description='Описание патента 1'
    )
    container.patent2 = repository_service.create_patent(
        db_session,
        patent_number=f"PAT{timestamp}2",
        patent_name='Патент 2',
        description='Описание патента 2'
    )

    # Создаем ML модели
    container.rf_model = repository_service.create_model(
        db_session, f'RF_{timestamp}', 'Ансамблевый алгоритм'
    )
    container.nn_model = repository_service.create_model(
        db_session, f'NN_{timestamp}', 'Нейронная сеть'
    )

    # Создаем пользователей
    container.person1 = repository_service.create_person(
        db_session,
        first_name='Тест',
        last_name='Пользователь1',
        email=f'test1_{timestamp}@example.com',
        role_id=container.researcher_role.id,
        login=f'u{timestamp}',
        password_hash='password1'
    )

    container.person2 = repository_service.create_person(
        db_session,
        first_name='Тест',
        last_name='Пользователь2',
        email=f'test2_{timestamp + 1}@example.com',
        role_id=container.engineer_role.id,
        login=f'u{timestamp + 1}',
        password_hash='password2'
    )

    db_session.flush()
    yield container