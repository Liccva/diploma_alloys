from application.config import get_engine, SessionLocal
from application.models.dao import Base  # ← Base из models.dao
from predictions_db import (
    populate_chemical_elements,
    populate_roles,
    populate_models,
    populate_organizations,
    populate_patents,
    populate_patent_authors,
    populate_persons,
    populate_devices,
    populate_refresh_tokens,
    populate_alloys,
    populate_predictions
)


def create_database():
    """Создание всех таблиц в базе данных"""
    print("Создание таблиц в базе данных...")

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы!")

    print("\nЗаполнение базы данных тестовыми данными...")
    db = SessionLocal()

    try:
        populate_chemical_elements(db)
        print("✓ Химические элементы добавлены")

        populate_roles(db)
        print("✓ Роли добавлены")

        populate_models(db)
        print("✓ ML модели добавлены")

        organizations = populate_organizations(db)
        print("✓ Организации добавлены")

        patents = populate_patents(db)
        print("✓ Патенты добавлены")

        populate_patent_authors(db, patents)
        print("✓ Авторы патентов добавлены")

        persons = populate_persons(db, organizations)
        print("✓ Пользователи добавлены")

        devices = populate_devices(db, persons)
        print("✓ Устройства добавлены")

        populate_refresh_tokens(db, persons, devices)
        print("✓ Refresh токены добавлены")

        populate_alloys(db)
        print("✓ Сплавы добавлены")

        populate_predictions(db)
        print("✓ Прогнозы добавлены")

        db.commit()
        print("\nБаза данных успешно создана и заполнена!")

    except Exception as e:
        print(f"Ошибка при заполнении базы данных: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_database()