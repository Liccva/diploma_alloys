import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import xgboost as xgb
import lightgbm as lgb
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Создаем директорию для моделей
os.makedirs('aloro/models', exist_ok=True)


def load_and_prepare_data(json_path='aloro/data_cleaned.json'):
    """Загружает данные и подготавливает признаки для классификации"""

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = []

    for entry in data:
        composition = entry.get('composition', {})
        if not composition:
            continue

        row = {}

        for element, value in composition.items():
            if isinstance(value, dict):
                if 'min' in value and 'max' in value:
                    row[f'comp_{element}'] = (value['min'] + value['max']) / 2
                elif 'value' in value:
                    row[f'comp_{element}'] = value['value']
            else:
                row[f'comp_{element}'] = value

        size = entry.get('size')
        if size is not None:
            row['size'] = float(size)

        raw_category = entry.get('category', 'unknown')
        row['category_raw'] = raw_category

        rows.append(row)

    df = pd.DataFrame(rows)

    category_mapping = create_category_mapping(df)
    df['category'] = df['category_raw'].map(category_mapping)
    df = df.dropna(subset=['category'])

    print(f"Загружено {len(df)} образцов")
    print(f"\nРаспределение по категориям:")
    print(df['category'].value_counts())

    return df, category_mapping


def create_category_mapping(df):
    """Создает маппинг исходных категорий в 6 основных классов"""

    category_keywords = {
        'nickel_alloy': ['nickel', 'ni-base', 'inconel', 'hastelloy', 'superalloy', 'copper-nickel'],
        'aluminum_alloy': ['aluminum', 'aluminium', 'al alloy', 'antifriction aluminum',
                           'aluminum alloy', 'al-li', 'al-cu', 'al-mg', 'al-si'],
        'titanium_alloy': ['titanium', 'ti alloy', 'ti-base', 'titanium alloy'],
        'steel_alloy': ['steel', 'roll tool steel', 'stainless', 'carbon steel',
                        'alloy steel', 'tool steel', 'construction steel',
                        'spring steel', 'bearing steel', 'structural steel',
                        'corrosion-resistant', 'heat resistant'],
        'copper_alloy': ['copper', 'bronze', 'brass', 'cu alloy', 'cu-base'],
    }

    mapping = {}
    unique_categories = df['category_raw'].unique()

    for cat in unique_categories:
        cat_lower = cat.lower()
        assigned = False

        for main_cat, keywords in category_keywords.items():
            if any(keyword in cat_lower for keyword in keywords):
                mapping[cat] = main_cat
                assigned = True
                break

        if not assigned:
            mapping[cat] = 'other'

    return mapping


def prepare_features(df):
    """Подготавливает признаки для обучения"""

    feature_cols = [col for col in df.columns if col.startswith('comp_')]

    if 'size' in df.columns:
        feature_cols.append('size')

    X = df[feature_cols].copy()
    X = X.fillna(0)

    y = df['category'].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"\nКоличество признаков: {X_scaled.shape[1]}")

    return X_scaled, y, scaler, feature_cols


def train_best_model(X, y):
    """Обучает лучшую модель (XGBoost)"""

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        use_label_encoder=False,
        eval_metric='mlogloss'
    )

    print("\nОбучение XGBoost классификатора...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {accuracy:.4f}")

    # Дополнительные метрики
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred))

    return model


def save_model(model, scaler, feature_cols, encoder, category_mapping):
    """Сохраняет все компоненты модели в папку aloro/models/"""

    # Убеждаемся, что директория существует
    os.makedirs('aloro/models', exist_ok=True)

    # Сохраняем модель и компоненты
    joblib.dump(model, 'aloro/models/best_classifier.joblib')
    joblib.dump(scaler, 'aloro/models/scaler.joblib')
    joblib.dump(feature_cols, 'aloro/models/feature_cols.joblib')
    joblib.dump(encoder, 'aloro/models/label_encoder.joblib')

    # Сохраняем маппинг категорий
    with open('aloro/models/category_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(category_mapping, f, ensure_ascii=False, indent=2)

    # Сохраняем список классов
    with open('aloro/models/classes.json', 'w', encoding='utf-8') as f:
        json.dump(list(encoder.classes_), f, ensure_ascii=False, indent=2)

    print(f"\nМодель и компоненты сохранены в aloro/models/")
    print(f"   - best_classifier.joblib")
    print(f"   - scaler.joblib")
    print(f"   - feature_cols.joblib")
    print(f"   - label_encoder.joblib")
    print(f"   - category_mapping.json")
    print(f"   - classes.json")


if __name__ == "__main__":
    print("=" * 60)
    print("КЛАССИФИКАТОР ТИПОВ СПЛАВОВ")
    print("=" * 60)

    print("\n1. Загрузка данных...")
    df, category_mapping = load_and_prepare_data('aloro/data_cleaned.json')

    print("\n2. Подготовка признаков...")
    X, y, scaler, feature_cols = prepare_features(df)

    encoder = LabelEncoder()
    y_encoded = encoder.fit_transform(y)
    class_names = encoder.classes_
    print(f"\nКлассы: {list(class_names)}")

    print("\n3. Обучение модели...")
    best_model = train_best_model(X, y_encoded)

    print("\n4. Сохранение модели...")
    save_model(best_model, scaler, feature_cols, encoder, category_mapping)

    print("\n5. Пример предсказания:")
    test_composition = {'fe': 85.0, 'cr': 18.0, 'ni': 8.0, 'c': 0.08, 'mn': 1.5}

    # Тестовое предсказание
    features = {col: 0 for col in feature_cols}
    for elem, val in test_composition.items():
        col_name = f'comp_{elem}'
        if col_name in features:
            features[col_name] = val

    X_test = pd.DataFrame([features]).fillna(0)
    X_test_scaled = scaler.transform(X_test)
    pred = best_model.predict(X_test_scaled)[0]
    category = encoder.inverse_transform([pred])[0]

    # Вероятности
    probs = best_model.predict_proba(X_test_scaled)[0]
    confidence = max(probs)

    print(f"  Состав: {test_composition}")
    print(f"  Категория: {category}")
    print(f"  Уверенность: {confidence:.1%}")

    print("\nГотово!")

    # Проверяем содержимое папки models
    print("\nСодержимое папки aloro/models:")
    for file in os.listdir('aloro/models'):
        file_path = os.path.join('aloro/models', file)
        size = os.path.getsize(file_path) / 1024  # KB
        print(f"   - {file} ({size:.1f} KB)")