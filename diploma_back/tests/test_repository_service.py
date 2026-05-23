"""
Тесты для репозитория
"""

import os
import sys
import datetime
import time
from typing import Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application.services import repository_service
from application.models.dao import Base
from application.models.dao import (
    Alloy, Patent, ChemicalElement, Prediction, Person, Role, Model,
    Organization, Device, RefreshToken, PatentAuthor,
)

# ========== НАСТРОЙКА ТЕСТОВОЙ БД ==========

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    """Фикстура для движка БД на всю сессию"""
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Фикстура для сессии БД (создается для каждого теста)"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ========== ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ ==========

class TestDataContainer:
    """Контейнер для тестовых данных"""

    def __init__(self):
        self.researcher_role: Optional[Role] = None
        self.engineer_role: Optional[Role] = None
        self.fe_element: Optional[ChemicalElement] = None
        self.c_element: Optional[ChemicalElement] = None
        self.si_element: Optional[ChemicalElement] = None
        self.patent1: Optional[Patent] = None
        self.patent2: Optional[Patent] = None
        self.rf_model: Optional[Model] = None
        self.nn_model: Optional[Model] = None
        self.person1: Optional[Person] = None
        self.person2: Optional[Person] = None
        self.organization: Optional[Organization] = None


@pytest.fixture(scope="function")
def test_data(db_session) -> TestDataContainer:
    """Фикстура для создания тестовых данных перед тестами"""
    container = TestDataContainer()
    timestamp = int(time.time() * 1000)

    try:
        # Создаем организацию
        container.organization = repository_service.create_organization(
            db_session,
            name=f'Тестовая организация {timestamp}',
            short_name=f'ТО{timestamp}',
            inn=f'770{timestamp % 1000000}'
        )

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
            db_session,
            name='Железо',
            atomic_number=26,
            symbol=f'Fe_{timestamp}'
        )
        container.c_element = repository_service.create_chemical_element(
            db_session,
            name='Углерод',
            atomic_number=6,
            symbol=f'C_{timestamp}'
        )
        container.si_element = repository_service.create_chemical_element(
            db_session,
            name='Кремний',
            atomic_number=14,
            symbol=f'Si_{timestamp}'
        )

        # Создаем патенты
        container.patent1 = repository_service.create_patent(
            db_session,
            patent_number=f"PAT{timestamp}1",
            patent_name=f'Патент 1 {timestamp}',
            description='Описание патента 1'
        )
        container.patent2 = repository_service.create_patent(
            db_session,
            patent_number=f"PAT{timestamp}2",
            patent_name=f'Патент 2 {timestamp}',
            description='Описание патента 2'
        )

        # Создаем ML модели
        container.rf_model = repository_service.create_model(
            db_session,
            name=f'RF_{timestamp}',
            description='Ансамблевый алгоритм'
        )
        container.nn_model = repository_service.create_model(
            db_session,
            name=f'NN_{timestamp}',
            description='Нейронная сеть'
        )

        # Создаем пользователей
        container.person1 = repository_service.create_person(
            db_session,
            first_name='Тест',
            last_name='Пользователь1',
            email=f'test1_{timestamp}_{int(time.time() * 1000)}@example.com',
            role_id=container.researcher_role.id,
            login=f'u{timestamp}_{int(time.time() * 1000)}',
            password_hash='password1',
            organization_id=container.organization.id
        )

        container.person2 = repository_service.create_person(
            db_session,
            first_name='Тест',
            last_name='Пользователь2',
            email=f'test2_{timestamp + 1}_{int(time.time() * 1000)}@example.com',
            role_id=container.engineer_role.id,
            login=f'u{timestamp + 1}_{int(time.time() * 1000)}',
            password_hash='password2',
            organization_id=container.organization.id
        )

        db_session.flush()

    except Exception as e:
        db_session.rollback()
        raise e

    yield container


# ========== ТЕСТЫ ХИМИЧЕСКИХ ЭЛЕМЕНТОВ ==========

class TestChemicalElements:
    """Тесты для химических элементов"""

    def test_create_chemical_element(self, db_session):
        """Тестирование создания химического элемента"""
        unique_id = int(time.time() * 1000) % 10000
        unique_symbol = f"X{unique_id}"
        unique_name = f"Эл{unique_id}"

        new_element = repository_service.create_chemical_element(
            db_session,
            name=unique_name,
            atomic_number=200 + unique_id,
            symbol=unique_symbol
        )

        assert new_element is not None
        assert new_element.name == unique_name
        assert new_element.symbol == unique_symbol

        # Проверяем, что дубликат не создается
        duplicate = repository_service.create_chemical_element(
            db_session,
            name=unique_name,
            atomic_number=200 + unique_id,
            symbol=unique_symbol
        )
        assert duplicate is None

    def test_create_duplicate_element_returns_none(self, db_session, test_data):
        """Тестирование создания дубликата элемента"""
        duplicate = repository_service.create_chemical_element(
            db_session,
            name='Дубликат',
            atomic_number=test_data.fe_element.atomic_number,
            symbol=test_data.fe_element.symbol
        )
        assert duplicate is None

    def test_get_element_by_id(self, db_session, test_data):
        """Тестирование получения элемента по ID"""
        element = repository_service.get_element_by_id(db_session, test_data.fe_element.id)
        assert element is not None
        assert element.id == test_data.fe_element.id

    def test_get_element_by_symbol(self, db_session, test_data):
        """Тестирование получения элемента по символу"""
        element = repository_service.get_element_by_symbol(db_session, test_data.fe_element.symbol)
        assert element is not None
        assert element.symbol == test_data.fe_element.symbol

    def test_get_element_by_atomic_number(self, db_session, test_data):
        """Тестирование получения элемента по атомному номеру"""
        element = repository_service.get_element_by_atomic_number(db_session, test_data.fe_element.atomic_number)
        assert element is not None
        assert element.atomic_number == test_data.fe_element.atomic_number

    def test_get_all_elements(self, db_session, test_data):
        """Тестирование получения всех элементов"""
        elements = repository_service.get_all_elements(db_session)
        assert len(elements) >= 3


# ========== ТЕСТЫ ОРГАНИЗАЦИЙ ==========

class TestOrganizations:
    """Тесты для организаций"""

    def test_create_organization(self, db_session):
        """Тестирование создания организации"""
        unique_id = int(time.time() * 1000) % 10000

        new_org = repository_service.create_organization(
            db_session,
            name=f'ООО "Тест"{unique_id}',
            short_name=f'Тест{unique_id}',
            inn=f'770{unique_id}',
            ogrn=f'1027700{unique_id}',
            address='г. Москва, ул. Тестовая, д. 1',
            phone='+7 (495) 123-45-67',
            email=f'test{unique_id}@example.com',
            website=f'www.test{unique_id}.ru'
        )
        assert new_org is not None
        assert new_org.name == f'ООО "Тест"{unique_id}'
        assert new_org.inn == f'770{unique_id}'

    def test_get_organization_by_id(self, db_session, test_data):
        """Тестирование получения организации по ID"""
        org = repository_service.get_organization_by_id(db_session, test_data.organization.id)
        assert org is not None
        assert org.id == test_data.organization.id

    def test_get_organization_by_inn(self, db_session, test_data):
        """Тестирование получения организации по ИНН"""
        org = repository_service.get_organization_by_inn(db_session, test_data.organization.inn)
        assert org is not None
        assert org.inn == test_data.organization.inn

    def test_get_all_organizations(self, db_session, test_data):
        """Тестирование получения всех организаций"""
        orgs = repository_service.get_all_organizations(db_session)
        assert len(orgs) >= 1

    def test_update_organization(self, db_session, test_data):
        """Тестирование обновления организации"""
        updated_org = repository_service.update_organization(
            db_session,
            test_data.organization.id,
            name='Обновленное название',
            phone='+7 (495) 999-99-99'
        )
        assert updated_org.name == 'Обновленное название'
        assert updated_org.phone == '+7 (495) 999-99-99'

    def test_delete_organization(self, db_session):
        """Тестирование удаления организации"""
        unique_id = int(time.time() * 1000) % 10000

        org = repository_service.create_organization(
            db_session,
            name=f'ООО "Для удаления"{unique_id}',
            inn=f'771{unique_id}'
        )
        org_id = org.id

        result = repository_service.delete_organization(db_session, org_id)
        assert result is True

        deleted_org = repository_service.get_organization_by_id(db_session, org_id)
        assert deleted_org is None


# ========== ТЕСТЫ РОЛЕЙ ==========

class TestRoles:
    """Тесты для ролей"""

    def test_create_role(self, db_session):
        """Тестирование создания роли"""
        unique_id = int(time.time() * 1000) % 10000
        role_name = f'role_{unique_id}'

        new_role = repository_service.create_role(
            db_session,
            name=role_name,
            description='Администратор системы'
        )
        assert new_role is not None
        assert new_role.name == role_name

        # Проверяем, что при повторном создании возвращается существующая роль
        existing_role = repository_service.create_role(
            db_session,
            name=role_name,
            description='Другое описание'
        )
        assert existing_role.id == new_role.id

    def test_get_role_by_id(self, db_session, test_data):
        """Тестирование получения роли по ID"""
        role = repository_service.get_role_by_id(db_session, test_data.researcher_role.id)
        assert role is not None
        assert role.id == test_data.researcher_role.id

    def test_get_role_by_name(self, db_session, test_data):
        """Тестирование получения роли по имени"""
        role = repository_service.get_role_by_name(db_session, test_data.researcher_role.name)
        assert role is not None
        assert role.name == test_data.researcher_role.name

    def test_get_all_roles(self, db_session, test_data):
        """Тестирование получения всех ролей"""
        roles = repository_service.get_all_roles(db_session)
        assert len(roles) >= 2

    def test_delete_role(self, db_session):
        """Тестирование удаления роли"""
        unique_id = int(time.time() * 1000) % 10000
        role = repository_service.create_role(
            db_session,
            name=f'delete_role_{unique_id}',
            description='Роль для удаления'
        )
        role_id = role.id

        result = repository_service.delete_role(db_session, role_id)
        assert result is True

        deleted_role = repository_service.get_role_by_id(db_session, role_id)
        assert deleted_role is None


# ========== ТЕСТЫ ML МОДЕЛЕЙ ==========

class TestModels:
    """Тесты для ML моделей"""

    def test_create_model(self, db_session):
        """Тестирование создания ML модели"""
        unique_id = int(time.time() * 1000) % 10000
        model_name = f'ML_{unique_id}'

        new_model = repository_service.create_model(
            db_session,
            name=model_name,
            description='Support Vector Machine'
        )
        assert new_model is not None
        assert new_model.name == model_name

        # Проверяем, что при повторном создании возвращается существующая модель
        existing_model = repository_service.create_model(
            db_session,
            name=model_name,
            description='Другое описание'
        )
        assert existing_model.id == new_model.id

    def test_get_model_by_id(self, db_session, test_data):
        """Тестирование получения модели по ID"""
        model = repository_service.get_model_by_id(db_session, test_data.rf_model.id)
        assert model is not None
        assert model.id == test_data.rf_model.id

    def test_get_model_by_name(self, db_session, test_data):
        """Тестирование получения модели по имени"""
        model = repository_service.get_model_by_name(db_session, test_data.rf_model.name)
        assert model is not None
        assert model.name == test_data.rf_model.name

    def test_get_all_models(self, db_session, test_data):
        """Тестирование получения всех моделей"""
        models = repository_service.get_all_models(db_session)
        assert len(models) >= 2

    def test_delete_model(self, db_session):
        """Тестирование удаления модели"""
        unique_id = int(time.time() * 1000) % 10000
        model = repository_service.create_model(
            db_session,
            name=f'delete_model_{unique_id}',
            description='Модель для удаления'
        )
        model_id = model.id

        result = repository_service.delete_model(db_session, model_id)
        assert result is True

        deleted_model = repository_service.get_model_by_id(db_session, model_id)
        assert deleted_model is None


# ========== ТЕСТЫ ПАТЕНТОВ ==========

class TestPatents:
    """Тесты для патентов"""

    def test_create_patent(self, db_session):
        """Тестирование создания патента"""
        unique_id = int(time.time() * 1000) % 10000
        patent_number = f"PN{unique_id}"

        new_patent = repository_service.create_patent(
            db_session,
            patent_number=patent_number,
            patent_name=f'Патент{unique_id}',
            country='RU',
            filing_date=datetime.datetime.utcnow(),
            description='Описание патента'
        )
        assert new_patent is not None
        assert new_patent.patent_number == patent_number
        assert new_patent.patent_name == f'Патент{unique_id}'

    def test_get_patent_by_id(self, db_session, test_data):
        """Тестирование получения патента по ID"""
        patent = repository_service.get_patent_by_id(db_session, test_data.patent1.id)
        assert patent is not None
        assert patent.id == test_data.patent1.id

    def test_get_patent_by_number(self, db_session, test_data):
        """Тестирование получения патента по номеру"""
        patent = repository_service.get_patent_by_number(db_session, test_data.patent1.patent_number)
        assert patent is not None
        assert patent.patent_number == test_data.patent1.patent_number

    def test_get_all_patents(self, db_session, test_data):
        """Тестирование получения всех патентов"""
        patents = repository_service.get_all_patents(db_session)
        assert len(patents) >= 2

    def test_update_patent(self, db_session, test_data):
        """Тестирование обновления патента"""
        updated_patent = repository_service.update_patent(
            db_session,
            test_data.patent1.id,
            description='Обновленное описание',
            assignee='ООО "Новый владелец"'
        )
        assert updated_patent.description == 'Обновленное описание'
        assert updated_patent.assignee == 'ООО "Новый владелец"'

    def test_delete_patent(self, db_session, test_data):
        """Тестирование удаления патента"""
        result = repository_service.delete_patent(db_session, test_data.patent2.id)
        assert result is True

        deleted_patent = repository_service.get_patent_by_id(db_session, test_data.patent2.id)
        assert deleted_patent is None


# ========== ТЕСТЫ АВТОРОВ ПАТЕНТОВ ==========

class TestPatentAuthors:
    """Тесты для авторов патентов"""

    def test_add_patent_author(self, db_session, test_data):
        """Тестирование добавления автора к патенту"""
        author = repository_service.add_patent_author(
            db_session,
            patent_id=test_data.patent1.id,
            author_name='Иванов И.И.',
            author_order=1,
            person_id=test_data.person1.id
        )
        assert author is not None
        assert author.author_name == 'Иванов И.И.'
        assert author.author_order == 1

    def test_get_patent_authors(self, db_session, test_data):
        """Тестирование получения авторов патента"""
        # Добавляем нескольких авторов
        repository_service.add_patent_author(
            db_session,
            patent_id=test_data.patent1.id,
            author_name='Петров П.П.',
            author_order=2,
            person_id=test_data.person2.id
        )

        authors = repository_service.get_patent_authors(db_session, test_data.patent1.id)
        assert len(authors) >= 1

    def test_delete_patent_author(self, db_session, test_data):
        """Тестирование удаления автора патента"""
        author = repository_service.add_patent_author(
            db_session,
            patent_id=test_data.patent1.id,
            author_name='Сидоров С.С.',
            author_order=3
        )

        result = repository_service.delete_patent_author(db_session, author.id)
        assert result is True


# ========== ТЕСТЫ СПЛАВОВ ==========

class TestAlloys:
    """Тесты для сплавов"""

    def test_create_alloy(self, db_session, test_data):
        """Тестирование создания сплава"""
        new_alloy = repository_service.create_alloy(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            temperature=1200.5
        )
        assert new_alloy is not None
        assert new_alloy.category == 'Сталь'
        assert new_alloy.prop_value == 50.0

    def test_create_alloy_with_elements(self, db_session, test_data):
        """Тестирование создания сплава с элементами"""
        element_percentages = {
            test_data.fe_element.id: 95.5,
            test_data.c_element.id: 2.5,
            test_data.si_element.id: 2.0
        }

        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages,
            temperature=1200.5,
            created_by_id=test_data.person1.id
        )
        assert new_alloy is not None
        assert new_alloy.category == 'Сталь'
        assert new_alloy.created_by_id == test_data.person1.id

    def test_add_element_to_alloy(self, db_session, test_data):
        """Тестирование добавления элемента к сплаву"""
        # Сначала создаем сплав
        alloy = repository_service.create_alloy(
            db_session,
            prop_value=50.0,
            category='Тестовый сплав',
            rolling_type='Холодная',
            patent_id=test_data.patent1.id
        )

        # Добавляем элемент
        result = repository_service.add_element_to_alloy(
            db_session,
            alloy.id,
            test_data.fe_element.id,
            85.5
        )
        assert result is not None

    def test_get_alloy_by_id(self, db_session, test_data):
        """Тестирование получения сплава по ID"""
        element_percentages = {
            test_data.fe_element.id: 95.5,
            test_data.c_element.id: 2.5
        }
        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        alloy = repository_service.get_alloy_by_id(db_session, new_alloy.id)
        assert alloy is not None
        assert alloy.id == new_alloy.id

    def test_get_alloys_by_patent(self, db_session, test_data):
        """Тестирование получения сплавов по патенту"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_alloy_with_elements(
            db_session,
            prop_value=45.0,
            category='Сталь1',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )
        repository_service.create_alloy_with_elements(
            db_session,
            prop_value=55.0,
            category='Сталь2',
            rolling_type='Холодная',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        alloys = repository_service.get_alloys_by_patent(db_session, test_data.patent1.id)
        assert len(alloys) >= 2

    def test_get_all_alloys(self, db_session, test_data):
        """Тестирование получения всех сплавов"""
        alloys = repository_service.get_all_alloys(db_session)
        assert isinstance(alloys, list)

    def test_get_alloy_elements_with_percentages(self, db_session, test_data):
        """Тестирование получения элементов сплава с процентами"""
        element_percentages = {
            test_data.fe_element.id: 95.5,
            test_data.c_element.id: 2.5,
            test_data.si_element.id: 2.0
        }
        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        elements = repository_service.get_alloy_elements_with_percentages(db_session, new_alloy.id)
        assert len(elements) == 3

        # Проверяем структуру данных
        for elem in elements:
            assert 'element_id' in elem
            assert 'element_name' in elem
            assert 'element_symbol' in elem
            assert 'percentage' in elem

    def test_update_alloy(self, db_session, test_data):
        """Тестирование обновления сплава"""
        element_percentages = {
            test_data.fe_element.id: 95.5,
            test_data.c_element.id: 2.5
        }
        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        updated_alloy = repository_service.update_alloy(
            db_session,
            new_alloy.id,
            category='Обновленная сталь',
            prop_value=55.0
        )
        assert updated_alloy.category == 'Обновленная сталь'
        assert updated_alloy.prop_value == 55.0

    def test_delete_alloy(self, db_session, test_data):
        """Тестирование удаления сплава"""
        element_percentages = {test_data.fe_element.id: 100.0}
        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь для удаления',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )
        alloy_id = new_alloy.id

        result = repository_service.delete_alloy(db_session, alloy_id)
        assert result is True

        deleted_alloy = repository_service.get_alloy_by_id(db_session, alloy_id)
        assert deleted_alloy is None

    def test_remove_element_from_alloy(self, db_session, test_data):
        """Тестирование удаления элемента из сплава"""
        element_percentages = {
            test_data.fe_element.id: 95.5,
            test_data.c_element.id: 2.5,
            test_data.si_element.id: 2.0
        }
        new_alloy = repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        # Удаляем элемент
        result = repository_service.remove_element_from_alloy(
            db_session,
            new_alloy.id,
            test_data.c_element.id
        )
        assert result is True

        # Проверяем, что элемент удален
        elements = repository_service.get_alloy_elements_with_percentages(db_session, new_alloy.id)
        element_ids = [e['element_id'] for e in elements]
        assert test_data.c_element.id not in element_ids


# ========== ТЕСТЫ ПРОГНОЗОВ ==========

class TestPredictions:
    """Тесты для прогнозов"""

    def test_create_prediction(self, db_session, test_data):
        """Тестирование создания прогноза"""
        new_prediction = repository_service.create_prediction(
            db_session,
            prop_value=48.5,
            category='Прогнозная сталь',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            temperature=1100.0
        )
        assert new_prediction is not None
        assert new_prediction.category == 'Прогнозная сталь'
        assert new_prediction.person_id == test_data.person1.id

    def test_create_prediction_with_elements(self, db_session, test_data):
        """Тестирование создания прогноза с элементами"""
        element_percentages = {
            test_data.fe_element.id: 94.0,
            test_data.c_element.id: 3.0,
            test_data.si_element.id: 3.0
        }

        new_prediction = repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогнозная сталь',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages,
            temperature=1100.0
        )
        assert new_prediction is not None
        assert new_prediction.category == 'Прогнозная сталь'

    def test_get_prediction_by_id(self, db_session, test_data):
        """Тестирование получения прогноза по ID"""
        element_percentages = {test_data.fe_element.id: 100.0}
        new_prediction = repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        prediction = repository_service.get_prediction_by_id(db_session, new_prediction.id)
        assert prediction is not None
        assert prediction.id == new_prediction.id

    def test_get_all_predictions(self, db_session, test_data):
        """Тестирование получения всех прогнозов"""
        predictions = repository_service.get_all_predictions(db_session)
        assert isinstance(predictions, list)

    def test_get_predictions_by_person(self, db_session, test_data):
        """Тестирование получения прогнозов по пользователю"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз1',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )
        repository_service.create_prediction_with_elements(
            db_session,
            prop_value=52.0,
            category='Прогноз2',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Холодная',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        predictions = repository_service.get_predictions_by_person(db_session, test_data.person1.id)
        assert len(predictions) >= 2

    def test_get_predictions_by_model(self, db_session, test_data):
        """Тестирование получения прогнозов по модели"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='ПрогнозRF1',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        predictions = repository_service.get_predictions_by_model(db_session, test_data.rf_model.id)
        assert len(predictions) >= 1

    def test_update_prediction(self, db_session, test_data):
        """Тестирование обновления прогноза"""
        element_percentages = {test_data.fe_element.id: 100.0}
        new_prediction = repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        updated_prediction = repository_service.update_prediction(
            db_session,
            new_prediction.id,
            category='Обновленный прогноз',
            prop_value=55.0
        )
        assert updated_prediction.category == 'Обновленный прогноз'
        assert updated_prediction.prop_value == 55.0

    def test_delete_prediction(self, db_session, test_data):
        """Тестирование удаления прогноза"""
        element_percentages = {test_data.fe_element.id: 100.0}
        new_prediction = repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз для удаления',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )
        prediction_id = new_prediction.id

        result = repository_service.delete_prediction(db_session, prediction_id)
        assert result is True

        deleted_prediction = repository_service.get_prediction_by_id(db_session, prediction_id)
        assert deleted_prediction is None

    def test_get_prediction_elements_with_percentages(self, db_session, test_data):
        """Тестирование получения элементов прогноза с процентами"""
        element_percentages = {
            test_data.fe_element.id: 94.0,
            test_data.c_element.id: 3.0,
            test_data.si_element.id: 3.0
        }
        new_prediction = repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        elements = repository_service.get_prediction_elements_with_percentages(db_session, new_prediction.id)
        assert len(elements) == 3


# ========== ТЕСТЫ ПОЛЬЗОВАТЕЛЕЙ ==========

class TestPersons:
    """Тесты для пользователей"""

    def test_create_person(self, db_session, test_data):
        """Тестирование создания пользователя"""
        timestamp = int(time.time() * 1000) % 10000

        new_person = repository_service.create_person(
            db_session,
            first_name='Новый',
            last_name='Пользователь',
            email=f'new_{timestamp}@example.com',
            role_id=test_data.researcher_role.id,
            login=f'newuser_{timestamp}',
            password_hash='newpassword',
            organization_id=test_data.organization.id
        )
        assert new_person is not None
        assert new_person.first_name == 'Новый'
        assert new_person.organization_id == test_data.organization.id

    def test_get_person_by_id(self, db_session, test_data):
        """Тестирование получения пользователя по ID"""
        person = repository_service.get_person_by_id(db_session, test_data.person1.id)
        assert person is not None
        assert person.id == test_data.person1.id

    def test_get_person_by_login(self, db_session, test_data):
        """Тестирование получения пользователя по логину"""
        person = repository_service.get_person_by_login(db_session, test_data.person1.login)
        assert person is not None
        assert person.login == test_data.person1.login

    def test_get_person_by_email(self, db_session, test_data):
        """Тестирование получения пользователя по email"""
        person = repository_service.get_person_by_email(db_session, test_data.person1.email)
        assert person is not None
        assert person.email == test_data.person1.email

    def test_get_all_persons(self, db_session, test_data):
        """Тестирование получения всех пользователей"""
        persons = repository_service.get_all_persons(db_session)
        assert len(persons) >= 2

    def test_get_persons_by_role(self, db_session, test_data):
        """Тестирование получения пользователей по роли"""
        persons = repository_service.get_persons_by_role(db_session, test_data.researcher_role.id)
        assert len(persons) >= 1

    def test_get_persons_by_organization(self, db_session, test_data):
        """Тестирование получения пользователей по организации"""
        persons = repository_service.get_persons_by_organization(db_session, test_data.organization.id)
        assert len(persons) >= 2

    def test_update_person(self, db_session, test_data):
        """Тестирование обновления пользователя"""
        updated_person = repository_service.update_person(
            db_session,
            test_data.person1.id,
            first_name='ОбновленноеИмя',
            middle_name='ОбновленноеОтчество'
        )
        assert updated_person.first_name == 'ОбновленноеИмя'
        assert updated_person.middle_name == 'ОбновленноеОтчество'

    def test_update_last_login(self, db_session, test_data):
        """Тестирование обновления времени последнего входа"""
        result = repository_service.update_last_login(db_session, test_data.person1.id)
        assert result is True

        person = repository_service.get_person_by_id(db_session, test_data.person1.id)
        assert person.last_login is not None

    def test_delete_person(self, db_session, test_data):
        """Тестирование удаления пользователя"""
        timestamp = int(time.time() * 1000) % 10000

        # Создаем организацию
        org = repository_service.create_organization(
            db_session,
            name=f'Орг для удаления {timestamp}',
            inn=f'772{timestamp}'
        )

        # Создаем пользователя для удаления
        person = repository_service.create_person(
            db_session,
            first_name='Удаляемый',
            last_name='Пользователь',
            email=f'delete_{timestamp}@example.com',
            role_id=test_data.researcher_role.id,
            login=f'deleteuser_{timestamp}',
            password_hash='password',
            organization_id=org.id
        )
        person_id = person.id

        result = repository_service.delete_person(db_session, person_id)
        assert result is True

        deleted_person = repository_service.get_person_by_id(db_session, person_id)
        assert deleted_person is None


# ========== ТЕСТЫ УСТРОЙСТВ И ТОКЕНОВ ==========

class TestDevicesAndTokens:
    """Тесты для устройств и refresh токенов"""

    def test_create_device(self, db_session):
        """Тестирование создания устройства"""
        fingerprint = f"fp_{int(time.time() * 1000)}"

        device = repository_service.create_device(
            db_session,
            device_name='Test Browser',
            device_fingerprint=fingerprint,
            is_trusted=True
        )
        assert device is not None
        assert device.device_fingerprint == fingerprint
        assert device.is_trusted is True

    def test_get_device_by_fingerprint(self, db_session):
        """Тестирование получения устройства по fingerprint"""
        fingerprint = f"fp_unique_{int(time.time() * 1000)}"

        created_device = repository_service.create_device(
            db_session,
            device_name='Unique Device',
            device_fingerprint=fingerprint
        )

        device = repository_service.get_device_by_fingerprint(db_session, fingerprint)
        assert device is not None
        assert device.id == created_device.id

    def test_update_device_last_seen(self, db_session):
        """Тестирование обновления времени последнего обращения к устройству"""
        fingerprint = f"fp_update_{int(time.time() * 1000)}"

        device = repository_service.create_device(
            db_session,
            device_name='Update Device',
            device_fingerprint=fingerprint
        )

        result = repository_service.update_device_last_seen(db_session, device.id)
        assert result is True

    def test_create_refresh_token(self, db_session, test_data):
        """Тестирование создания refresh токена"""
        device = repository_service.create_device(
            db_session,
            device_name='Token Device',
            device_fingerprint=f"fp_token_{int(time.time() * 1000)}"
        )

        token = repository_service.create_refresh_token(
            db_session,
            person_id=test_data.person1.id,
            device_id=device.id,
            token_hash=f"hash_{int(time.time() * 1000)}",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
        )
        assert token is not None
        assert token.person_id == test_data.person1.id
        assert token.revoked is False

    def test_get_active_refresh_tokens_by_user(self, db_session, test_data):
        """Тестирование получения активных токенов пользователя"""
        device = repository_service.create_device(
            db_session,
            device_name='Active Token Device',
            device_fingerprint=f"fp_active_{int(time.time() * 1000)}"
        )

        repository_service.create_refresh_token(
            db_session,
            person_id=test_data.person1.id,
            device_id=device.id,
            token_hash=f"hash_active_{int(time.time() * 1000)}",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
        )

        tokens = repository_service.get_active_refresh_tokens_by_user(db_session, test_data.person1.id)
        assert len(tokens) >= 1

    def test_revoke_refresh_token(self, db_session, test_data):
        """Тестирование отзыва refresh токена"""
        device = repository_service.create_device(
            db_session,
            device_name='Revoke Device',
            device_fingerprint=f"fp_revoke_{int(time.time() * 1000)}"
        )
        token_hash = f"hash_revoke_{int(time.time() * 1000)}"

        repository_service.create_refresh_token(
            db_session,
            person_id=test_data.person1.id,
            device_id=device.id,
            token_hash=token_hash,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
        )

        result = repository_service.revoke_refresh_token(db_session, token_hash)
        assert result is True

    def test_revoke_all_user_tokens(self, db_session, test_data):
        """Тестирование отзыва всех токенов пользователя"""
        device1 = repository_service.create_device(
            db_session,
            device_name='Device1',
            device_fingerprint=f"fp_revoke_all1_{int(time.time() * 1000)}"
        )
        device2 = repository_service.create_device(
            db_session,
            device_name='Device2',
            device_fingerprint=f"fp_revoke_all2_{int(time.time() * 1000)}"
        )

        repository_service.create_refresh_token(
            db_session,
            person_id=test_data.person1.id,
            device_id=device1.id,
            token_hash=f"hash_all1_{int(time.time() * 1000)}",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
        )
        repository_service.create_refresh_token(
            db_session,
            person_id=test_data.person1.id,
            device_id=device2.id,
            token_hash=f"hash_all2_{int(time.time() * 1000)}",
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=7)
        )

        count = repository_service.revoke_all_user_tokens(db_session, test_data.person1.id, device1.id)
        assert count >= 1

    def test_delete_device(self, db_session):
        """Тестирование удаления устройства"""
        fingerprint = f"fp_delete_{int(time.time() * 1000)}"

        device = repository_service.create_device(
            db_session,
            device_name='Delete Device',
            device_fingerprint=fingerprint
        )
        device_id = device.id

        result = repository_service.delete_device(db_session, device_id)
        assert result is True

        deleted_device = repository_service.get_device_by_fingerprint(db_session, fingerprint)
        assert deleted_device is None


# ========== ТЕСТЫ КОМПЛЕКСНЫХ ФУНКЦИЙ ==========

class TestComplexFunctions:
    """Тесты для комплексных функций"""

    def test_get_alloys_with_details(self, db_session, test_data):
        """Тестирование получения сплавов с деталями"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='Сталь',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        alloys = repository_service.get_alloys_with_details(db_session)
        assert isinstance(alloys, list)

    def test_get_predictions_with_details(self, db_session, test_data):
        """Тестирование получения прогнозов с деталями"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_prediction_with_elements(
            db_session,
            prop_value=48.5,
            category='Прогноз',
            ml_model_id=test_data.rf_model.id,
            rolling_type='Горячая',
            person_id=test_data.person1.id,
            element_percentages=element_percentages
        )

        predictions = repository_service.get_predictions_with_details(db_session)
        assert isinstance(predictions, list)


# ========== ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ ==========

class TestEdgeCases:
    """Тесты для граничных случаев"""

    def test_get_nonexistent_alloy_returns_none(self, db_session):
        """Проверка получения несуществующего сплава"""
        alloy = repository_service.get_alloy_by_id(db_session, 99999)
        assert alloy is None

    def test_get_nonexistent_patent_returns_none(self, db_session):
        """Проверка получения несуществующего патента"""
        patent = repository_service.get_patent_by_id(db_session, 99999)
        assert patent is None

    def test_get_nonexistent_person_returns_none(self, db_session):
        """Проверка получения несуществующего пользователя"""
        person = repository_service.get_person_by_id(db_session, 99999)
        assert person is None

    def test_get_nonexistent_element_returns_none(self, db_session):
        """Проверка получения несуществующего элемента"""
        element = repository_service.get_element_by_id(db_session, 99999)
        assert element is None

    def test_update_nonexistent_alloy_returns_none(self, db_session):
        """Проверка обновления несуществующего сплава"""
        result = repository_service.update_alloy(db_session, 99999, category='Test')
        assert result is None

    def test_delete_nonexistent_alloy_returns_false(self, db_session):
        """Проверка удаления несуществующего сплава"""
        result = repository_service.delete_alloy(db_session, 99999)
        assert result is False

    def test_add_element_to_nonexistent_alloy_raises_error(self, db_session, test_data):
        """Проверка добавления элемента к несуществующему сплаву"""
        with pytest.raises(ValueError, match="not found"):
            repository_service.add_element_to_alloy(db_session, 99999, test_data.fe_element.id, 50.0)

    def test_remove_element_from_nonexistent_alloy_raises_error(self, db_session, test_data):
        """Проверка удаления элемента из несуществующего сплава"""
        with pytest.raises(ValueError, match="not found"):
            repository_service.remove_element_from_alloy(db_session, 99999, test_data.fe_element.id)

    def test_add_element_with_invalid_percentage_raises_error(self, db_session, test_data):
        """Проверка добавления элемента с некорректным процентом"""
        # Создаем сплав
        alloy = repository_service.create_alloy(
            db_session,
            prop_value=50.0,
            category='Тест',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id
        )

        # Проверяем процент <= 0
        with pytest.raises(ValueError, match="between 0 and 100"):
            repository_service.add_element_to_alloy(db_session, alloy.id, test_data.fe_element.id, 0)

        # Проверяем процент > 100
        with pytest.raises(ValueError, match="between 0 and 100"):
            repository_service.add_element_to_alloy(db_session, alloy.id, test_data.fe_element.id, 150.0)

    def test_search_alloys_by_category(self, db_session, test_data):
        """Тестирование поиска сплавов по категории"""
        element_percentages = {test_data.fe_element.id: 100.0}

        repository_service.create_alloy_with_elements(
            db_session,
            prop_value=50.0,
            category='УникальнаяКатегорияДляПоиска',
            rolling_type='Горячая',
            patent_id=test_data.patent1.id,
            element_percentages=element_percentages
        )

        alloys = repository_service.search_alloys_by_category(db_session, 'УникальнаяКатегория')
        assert len(alloys) >= 1

    def test_get_alloys_count(self, db_session, test_data):
        """Тестирование получения количества сплавов"""
        count = repository_service.get_alloys_count(db_session)
        assert isinstance(count, int)
        assert count >= 0


# ========== ЗАПУСК ТЕСТОВ ==========
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])