import json
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
from datetime import datetime

os.makedirs('aloro/models', exist_ok=True)
os.makedirs('aloro/results', exist_ok=True)

print("=" * 70)
print("ОБУЧЕНИЕ МОДЕЛИ НА ПАТЕНТНЫХ ДАННЫХ")
print("=" * 70)

# 1. Загружаем патенты
print("\n1. Загрузка патентов...")
with open('aloro/patents_all.json', 'r', encoding='utf-8') as f:
    patents = json.load(f)

print(f"   Всего патентов: {len(patents)}")

# 2. Отбираем патенты с sigma_u
patents_with_sigma = []
for p in patents:
    mech = p.get('mechanical_properties')
    if mech and mech.get('sigma_u'):
        patents_with_sigma.append(p)

print(f"   Патентов с sigma_u: {len(patents_with_sigma)}")

# 3. Загружаем список всех элементов
try:
    with open('aloro/models/all_elements.json', 'r', encoding='utf-8') as f:
        all_elements = json.load(f)
    print(f"   Химических элементов: {len(all_elements)}")
except:
    # Стандартные 118 элементов
    all_elements = [
        'h', 'he', 'li', 'be', 'b', 'c', 'n', 'o', 'f', 'ne',
        'na', 'mg', 'al', 'si', 'p', 's', 'cl', 'ar', 'k', 'ca',
        'sc', 'ti', 'v', 'cr', 'mn', 'fe', 'co', 'ni', 'cu', 'zn',
        'ga', 'ge', 'as', 'se', 'br', 'kr', 'rb', 'sr', 'y', 'zr',
        'nb', 'mo', 'tc', 'ru', 'rh', 'pd', 'ag', 'cd', 'in', 'sn',
        'sb', 'te', 'i', 'xe', 'cs', 'ba', 'la', 'ce', 'pr', 'nd',
        'pm', 'sm', 'eu', 'gd', 'tb', 'dy', 'ho', 'er', 'tm', 'yb',
        'lu', 'hf', 'ta', 'w', 're', 'os', 'ir', 'pt', 'au', 'hg',
        'tl', 'pb', 'bi', 'po', 'at', 'rn', 'fr', 'ra', 'ac', 'th',
        'pa', 'u', 'np', 'pu', 'am', 'cm', 'bk', 'cf', 'es', 'fm',
        'md', 'no', 'lr', 'rf', 'db', 'sg', 'bh', 'hs', 'mt', 'ds',
        'rg', 'cn', 'nh', 'fl', 'mc', 'lv', 'ts', 'og'
    ]
    print(f"   Используем {len(all_elements)} стандартных элементов")

# 4. Преобразуем патенты в признаки
print("\n2. Преобразование в признаки...")
X_list = []
y_list = []

for p in patents_with_sigma:
    # Получаем sigma_u
    sigma = p['mechanical_properties']['sigma_u']
    if isinstance(sigma, dict):
        if 'min' in sigma and 'max' in sigma:
            sigma_val = (sigma['min'] + sigma['max']) / 2
        else:
            sigma_val = sigma.get('value', 0)
    else:
        sigma_val = float(sigma)

    # Пропускаем аномальные значения
    if sigma_val <= 0 or sigma_val > 3000:
        continue

    # Вектор состава
    composition = p.get('composition', {})
    row = []
    for element in all_elements:
        value = composition.get(element, 0)
        if isinstance(value, dict):
            if 'min' in value and 'max' in value:
                val = (value['min'] + value['max']) / 2
            elif 'value' in value:
                val = value['value']
            else:
                val = 0
        elif isinstance(value, (int, float)):
            val = value
        else:
            val = 0
        row.append(val)

    # size в патентах нет
    row.append(0)

    X_list.append(row)
    y_list.append(sigma_val)

X = np.array(X_list)
y = np.array(y_list)

print(f"   Отобрано образцов: {len(X)}")

# 5. Удаляем выбросы
print("\n3. Удаление выбросов...")
q1 = np.percentile(y, 25)
q3 = np.percentile(y, 75)
iqr = q3 - q1
lower = q1 - 2.5 * iqr
upper = q3 + 2.5 * iqr

mask = (y >= lower) & (y <= upper)
X = X[mask]
y = y[mask]

print(f"   После удаления выбросов: {len(X)} образцов")
print(f"   Диапазон sigma_u: {np.min(y):.0f} - {np.max(y):.0f} MPa")
print(f"   Среднее sigma_u: {np.mean(y):.0f} +- {np.std(y):.0f} MPa")

# 6. Разделяем на train/test
print("\n4. Обучение модели...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Масштабирование
scaler = RobustScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Обучаем XGBoost
model = xgb.XGBRegressor(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train_scaled, y_train)

# Оценка
y_pred = model.predict(X_test_scaled)
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))

print(f"\n   Результаты:")
print(f"   R² = {r2:.4f}")
print(f"   MAE = {mae:.1f} MPa")
print(f"   RMSE = {rmse:.1f} MPa")

# 7. Сохраняем модель
print("\n5. Сохранение модели...")
joblib.dump(model, 'aloro/models/patent_model.joblib')
joblib.dump(scaler, 'aloro/models/patent_scaler.joblib')
joblib.dump(all_elements, 'aloro/models/patent_elements.joblib')

print("   Модель сохранена: aloro/models/patent_model.joblib")
print("   Скейлер сохранен: aloro/models/patent_scaler.joblib")
print("   Элементы сохранены: aloro/models/patent_elements.joblib")

# 8. Отчет (без спецсимволов)
with open('aloro/results/patent_model_report.txt', 'w', encoding='utf-8') as f:
    f.write("=" * 60 + "\n")
    f.write("REPORT: PATENT MODEL (sigma_u)\n")
    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Samples after filtering: {len(X)}\n")
    f.write(f"R²: {r2:.4f}\n")
    f.write(f"MAE: {mae:.1f} MPa\n")
    f.write(f"RMSE: {rmse:.1f} MPa\n")
    f.write(f"Sigma range: {np.min(y):.0f} - {np.max(y):.0f} MPa\n")
    f.write(f"Sigma mean: {np.mean(y):.0f} +- {np.std(y):.0f} MPa\n")

print("\nОтчет сохранен: aloro/results/patent_model_report.txt")

print("\n" + "=" * 70)
print("ПАТЕНТНАЯ МОДЕЛЬ ГОТОВА!")
print("=" * 70)
print("\nТеперь у вас есть 2 модели:")
print("  1. Справочная модель: aloro/models/best_classifier.joblib")
print("  2. Патентная модель:  aloro/models/patent_model.joblib")