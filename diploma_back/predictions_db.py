from sqlalchemy.orm import Session
from application.models.dao import Base
from application.config import SessionLocal
from application.services.repository_service import (
    get_element_by_symbol, create_chemical_element,
    get_role_by_name, create_role,
    get_model_by_name, create_model,
    get_all_roles, get_all_persons, get_all_models,
    get_all_elements, get_all_alloys,
    get_alloy_elements_with_percentages, add_element_to_alloy,
)
from application.models.dao import (
    Organization, Patent, PatentAuthor, Person,
    Device, RefreshToken, Alloy, Prediction,
    prediction_element_association,
)
from application.utils.patent_utils import get_category_by_ipc
from passlib.context import CryptContext
import random
import hashlib
import string
from datetime import datetime, timedelta

# ========== КОНСТАНТЫ ==========

CATEGORIES = ['Сталь конструкционная', 'Сталь инструментальная', 'Чугун', 'Алюминиевый сплав', 'Медный сплав']
ROLLING_TYPES = ['Горячая', 'Холодная', 'Прессование', 'Волочение']

PATENT_NAMES = [
    'High strength structural steel',
    'Improved stainless steel composition',
    'Heat treatment method for aluminum alloys',
    'Innovative copper alloy composition',
]

ORGANIZATIONS = [
    'Металлургический институт',
    'Центр исследований сплавов',
    'Технологический университет',
    'Промышленный комбинат',
]

IPC_CODES = {
    'Сталь конструкционная': 'C22C38/00',
    'Сталь инструментальная': 'C22C38/00',
    'Чугун':                  'C22C37/00',
    'Алюминиевый сплав':      'C22C21/00',
    'Медный сплав':           'C22C9/00',
}

PATENT_AUTHORS_DATA = {
    'High strength structural steel':           [('Иванов А.И.', 1), ('Петров С.В.', 2), ('Сидорова М.К.', 3)],
    'Improved stainless steel composition':     [('Петров С.В.', 1), ('Кузнецов Д.П.', 2)],
    'Heat treatment method for aluminum alloys':[('Сидорова М.К.', 1), ('Иванов А.И.', 2), ('Васильева Е.Н.', 3)],
    'Innovative copper alloy composition':      [('Кузнецов Д.П.', 1)],
}

CHEMICAL_ELEMENTS = [
    ('Водород',  1, 'H'),  ('Гелий',    2, 'He'), ('Литий',    3, 'Li'),
    ('Бериллий', 4, 'Be'), ('Бор',      5, 'B'),  ('Углерод',  6, 'C'),
    ('Азот',     7, 'N'),  ('Кислород', 8, 'O'),  ('Фтор',     9, 'F'),
    ('Неон',    10, 'Ne'), ('Натрий',  11, 'Na'), ('Магний',  12, 'Mg'),
    ('Алюминий',13, 'Al'), ('Кремний', 14, 'Si'), ('Фосфор',  15, 'P'),
    ('Сера',    16, 'S'),  ('Хлор',    17, 'Cl'), ('Аргон',   18, 'Ar'),
    ('Калий',   19, 'K'),  ('Кальций', 20, 'Ca'), ('Скандий', 21, 'Sc'),
    ('Титан',   22, 'Ti'), ('Ванадий', 23, 'V'),  ('Хром',    24, 'Cr'),
    ('Марганец',25, 'Mn'), ('Железо',  26, 'Fe'), ('Кобальт', 27, 'Co'),
    ('Никель',  28, 'Ni'), ('Медь',    29, 'Cu'), ('Цинк',    30, 'Zn'),
]

ROLES = [
    ('администратор', 'Администратор системы с полными правами'),
    ('исследователь', 'Научный сотрудник, проводящий исследования'),
]

ML_MODELS = [
    ('Random Forest',     'Ансамблевый алгоритм на основе деревьев решений'),
    ('Gradient Boosting', 'Градиентный бустинг'),
]

# ========== УТИЛИТЫ ==========

# bcrypt — совместимо с auth.py (НЕ md5)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def generate_random_login(length: int = 8) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))


# ========== POPULATE ==========

def populate_chemical_elements(db: Session) -> None:
    for name, atomic_number, symbol in CHEMICAL_ELEMENTS:
        if not get_element_by_symbol(db, symbol):
            el = create_chemical_element(db, name=name, atomic_number=atomic_number, symbol=symbol)
            if el:
                print(f"  Элемент: {symbol} - {name}")


def populate_roles(db: Session) -> None:
    for name, desc in ROLES:
        if not get_role_by_name(db, name):
            r = create_role(db, name=name, description=desc)
            if r:
                print(f"  Роль: {name}")


def populate_models(db: Session) -> None:
    for name, desc in ML_MODELS:
        if not get_model_by_name(db, name):
            m = create_model(db, name=name, description=desc)
            if m:
                print(f"  Модель: {name}")


def populate_organizations(db: Session) -> list:
    result = []
    for name in ORGANIZATIONS:
        org = db.query(Organization).filter(Organization.name == name).first()
        if not org:
            org = Organization(name=name, short_name=name[:10], created_at=datetime.utcnow())
            db.add(org)
            db.flush()
            print(f"  Организация: {name}")
        result.append(org)
    db.commit()
    return result


# predictions_db.py - только измененная функция populate_patents
# (остальной код остается без изменений)

def populate_patents(db: Session) -> list:
    result = []
    for i, name in enumerate(PATENT_NAMES):
        number = f"RU2024{i:04d}"
        if db.query(Patent).filter(Patent.patent_number == number).first():
            continue
        category = CATEGORIES[i % len(CATEGORIES)]
        patent = Patent(
            patent_number=number,
            country="RU",
            patent_name=name,
            filing_date=datetime(2020 + i, 1, 1),
            issue_date=datetime(2023 + i, 12, 31),
            assignee=random.choice(ORGANIZATIONS),
            ipc_code=IPC_CODES.get(category, 'C22C00/00'),
            description=f"Описание: {name}",
            # Поля для локального хранения
            pdf_filename=None,  # При создании PDF еще нет
            pdf_file_path=None,  # При создании PDF еще нет
            category=category,
            created_at=datetime.utcnow(),
        )
        db.add(patent)
        db.flush()
        result.append(patent)
        print(f"  Патент: {name}")
    db.commit()
    return result


def populate_patent_authors(db: Session, patents: list) -> None:
    if not patents:
        return
    for patent in patents:
        for author_name, order in PATENT_AUTHORS_DATA.get(patent.patent_name, [('Неизвестный', 1)]):
            exists = db.query(PatentAuthor).filter(
                PatentAuthor.patent_id == patent.id,
                PatentAuthor.author_order == order,
            ).first()
            if not exists:
                db.add(PatentAuthor(patent_id=patent.id, person_id=None,
                                    author_name=author_name, author_order=order))
    db.commit()
    print(f"  Авторы добавлены для {len(patents)} патентов")


def populate_persons(db: Session, organizations: list) -> list:
    first_names   = ['Алексей', 'Сергей', 'Мария', 'Дмитрий', 'Ольга', 'Иван']
    last_names    = ['Иванов', 'Петров', 'Сидорова', 'Кузнецов', 'Васильева', 'Николаев']
    middle_names  = [None, 'Александрович', 'Владимировна', 'Петровна', 'Сергеевич']

    roles = get_all_roles(db)
    if not roles:
        print("  Ошибка: нет ролей")
        return []

    result = []
    for i in range(8):
        login = generate_random_login()
        email = f"user_{generate_random_login(4)}@example.com"
        if db.query(Person).filter(Person.login == login).first():
            continue
        if db.query(Person).filter(Person.email == email).first():
            continue
        person = Person(
            first_name=random.choice(first_names),
            last_name=random.choice(last_names),
            middle_name=random.choice(middle_names),
            email=email,
            role_id=roles[i % len(roles)].id,
            organization_id=organizations[i % len(organizations)].id if organizations else None,
            login=login,
            password_hash=hash_password(f"user{i}_123"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )
        db.add(person)
        db.flush()
        result.append(person)
        print(f"  Пользователь: {person.first_name} {person.last_name} ({person.login})")
    db.commit()
    return result


def populate_devices(db: Session, persons: list) -> list:
    """
    Устройства создаются БЕЗ person_id.
    Устройство = браузер/клиент. Кто с него входит — определяется
    через RefreshToken, а не через Device.
    """
    if not persons:
        print("  Нет пользователей — устройства не созданы")
        return []

    device_names = ['Chrome на Windows', 'Firefox на Linux', 'Safari на Mac', 'Mobile App']
    result = []

    for i in range(min(5, len(persons))):
        # Fingerprint на основе индекса — детерминированный для воспроизводимости
        fingerprint = hashlib.sha256(f"device_seed_{i}".encode()).hexdigest()

        device = db.query(Device).filter(Device.device_fingerprint == fingerprint).first()
        if not device:
            device = Device(
                # person_id отсутствует — новая архитектура
                device_name=device_names[i % len(device_names)],
                device_fingerprint=fingerprint,
                is_trusted=False,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
            )
            db.add(device)
            db.flush()
            print(f"  Устройство: {device.device_name}")
        result.append(device)

    db.commit()
    return result


def populate_refresh_tokens(db: Session, persons: list, devices: list) -> None:
    """
    RefreshToken — единственное место где хранится связь (person, device).
    Перед созданием нового токена старые для той же пары отзываются,
    чтобы не было бесконечного роста таблицы.
    """
    if not persons or not devices:
        print("  Нет данных для refresh токенов")
        return

    count = 0
    for i, person in enumerate(persons[:5]):
        device = devices[i % len(devices)]

        # Отзываем предыдущие активные токены этой пары (person, device)
        db.query(RefreshToken).filter(
            RefreshToken.person_id == person.id,
            RefreshToken.device_id == device.id,
            RefreshToken.revoked == False,
        ).update({"revoked": True})

        token_hash = hashlib.sha256(f"seed_token_{person.id}_{device.id}".encode()).hexdigest()

        if db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first():
            continue

        db.add(RefreshToken(
            token_hash=token_hash,
            person_id=person.id,   # связь person→device живёт здесь
            device_id=device.id,
            expires_at=datetime.utcnow() + timedelta(days=30),
            revoked=False,
            created_at=datetime.utcnow(),
        ))
        count += 1

    db.commit()
    print(f"  Refresh токенов создано: {count}")


def populate_alloys(db: Session) -> int:
    elements = get_all_elements(db)
    patents  = db.query(Patent).all()

    if not elements or not patents:
        print("  Ошибка: нет элементов или патентов")
        return 0

    main_metals = [e for e in elements if e.symbol in ('Fe', 'Al', 'Cu', 'Mg', 'Ti')]
    alloying    = [e for e in elements if e.symbol in ('C', 'Si', 'Mn', 'Cr', 'Ni', 'Zn')]

    if not main_metals:
        print("  Ошибка: нет основных металлов")
        return 0

    count = 0
    for i in range(min(15, len(patents))):
        main = random.choice(main_metals)
        pcts = {main.id: round(random.uniform(85.0, 98.0), 2)}

        selected  = random.sample(alloying, random.randint(1, min(3, len(alloying))))
        remaining = 100.0 - list(pcts.values())[0]
        for j, elem in enumerate(selected):
            p = remaining if j == len(selected) - 1 else round(random.uniform(0.1, remaining * 0.7), 2)
            remaining -= p if j < len(selected) - 1 else 0
            pcts[elem.id] = min(round(p, 2), 99.999)

        try:
            alloy = Alloy(
                prop_value=round(random.uniform(10.0, 100.0), 1),
                temperature=round(random.uniform(20, 1200), 1),
                category=random.choice(CATEGORIES),
                rolling_type=random.choice(ROLLING_TYPES),
                patent_id=patents[i % len(patents)].id,
            )
            db.add(alloy)
            db.flush()
            for eid, p in pcts.items():
                add_element_to_alloy(db, alloy.id, eid, p)
            count += 1
            print(f"  Сплав #{alloy.id}")
        except Exception as e:
            print(f"  Ошибка сплава: {e}")

    db.commit()
    return count


def populate_predictions(db: Session) -> int:
    alloys  = get_all_alloys(db, limit=1000)
    persons = get_all_persons(db, limit=1000)
    models  = get_all_models(db)

    if not alloys or not persons or not models:
        print("  Ошибка: недостаточно данных")
        return 0

    count = 0
    for i in range(min(25, len(alloys))):
        base = alloys[i]
        elems = get_alloy_elements_with_percentages(db, base.id)

        adjusted = {}
        for e in elems:
            p = max(0.1, round(float(e['percentage']) * random.uniform(0.95, 1.05), 2))
            adjusted[e['element_id']] = min(p, 99.999)

        total = sum(adjusted.values())
        if abs(total - 100.0) > 0.01:
            adjusted = {k: round(v * 100.0 / total, 2) for k, v in adjusted.items()}

        try:
            pred = Prediction(
                prop_value=round((float(base.prop_value) if base.prop_value else 50.0) * random.uniform(0.8, 1.2), 1),
                temperature=base.temperature,
                category=base.category,
                ml_model_id=models[i % len(models)].id,
                rolling_type=base.rolling_type,
                person_id=persons[i % len(persons)].id,
            )
            db.add(pred)
            db.flush()
            for eid, p in adjusted.items():
                db.execute(prediction_element_association.insert().values(
                    prediction_id=pred.id, element_id=eid, percentage=p))
            count += 1
            print(f"  Прогноз #{pred.id}")
        except Exception as e:
            print(f"  Ошибка прогноза: {e}")

    db.commit()
    return count


# ========== ТОЧКА ВХОДА ==========

if __name__ == "__main__":
    print("=" * 60)
    print("Заполнение базы данных тестовыми данными")
    print("=" * 60)

    with SessionLocal() as session:
        try:
            print("\n1. Химические элементы...")
            populate_chemical_elements(session)
            print("\n2. Роли...")
            populate_roles(session)
            print("\n3. ML модели...")
            populate_models(session)
            print("\n4. Организации...")
            organizations = populate_organizations(session)
            print("\n5. Патенты...")
            patents = populate_patents(session)
            print("\n6. Авторы патентов...")
            populate_patent_authors(session, patents)
            print("\n7. Пользователи...")
            persons = populate_persons(session, organizations)
            print("\n8. Устройства...")
            devices = populate_devices(session, persons)
            print("\n9. Refresh токены...")
            populate_refresh_tokens(session, persons, devices)
            print("\n10. Сплавы...")
            populate_alloys(session)
            print("\n11. Прогнозы...")
            populate_predictions(session)
            print("\n" + "=" * 60)
            print("✓ База данных успешно заполнена!")
            print("=" * 60)
        except Exception as e:
            print(f"\n✗ Критическая ошибка: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
