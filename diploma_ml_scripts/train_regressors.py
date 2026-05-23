import json
import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
import joblib
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Создаем директории
os.makedirs('aloro/models', exist_ok=True)
os.makedirs('aloro/results', exist_ok=True)


# ==================== 1. ВСЕ 118 ХИМИЧЕСКИХ ЭЛЕМЕНТОВ ====================

def get_all_chemical_elements():
    """Возвращает список ВСЕХ 118 химических элементов"""
    return [
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


def collect_all_rolling_types():
    """Собирает ВСЕ возможные типы прокатки из данных"""
    categories = ['nickel_alloy', 'titanium_alloy', 'aluminum_alloy',
                  'steel_alloy', 'copper_alloy', 'other']

    rolling_types = set()

    for category in categories:
        input_file = f'aloro/split_by_category/{category}.json'
        if not os.path.exists(input_file):
            continue

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for entry in data:
            rolling = entry.get('rolling', 'unknown')
            rolling_types.add(rolling)

    return sorted(list(rolling_types))


def prepare_data_with_all_elements(data, all_elements, all_rolling_types):
    """
    Подготавливает данные с использованием ВСЕХ 118 элементов и ВСЕХ типов прокатки
    """
    rows = []

    for entry in data:
        composition = entry.get('composition', {})

        # Создаем вектор признаков для ВСЕХ элементов
        row = {}

        # Для каждого из 118 элементов - берем значение из состава или 0
        for element in all_elements:
            value = composition.get(element, composition.get(element.upper(), 0))

            if isinstance(value, dict):
                if 'min' in value and 'max' in value:
                    row[f'comp_{element}'] = (value['min'] + value['max']) / 2
                elif 'value' in value:
                    row[f'comp_{element}'] = value['value']
                else:
                    row[f'comp_{element}'] = 0
            elif isinstance(value, (int, float)):
                row[f'comp_{element}'] = value
            else:
                row[f'comp_{element}'] = 0

        # Добавляем размер (если есть)
        size = entry.get('size')
        row['size'] = float(size) if size is not None else 0

        # Добавляем ВСЕ типы прокатки (one-hot encoding)
        current_rolling = entry.get('rolling', 'unknown')
        for rolling_type in all_rolling_types:
            row[f'rolling_{rolling_type}'] = 1 if current_rolling == rolling_type else 0

        # Целевая переменная - sigma_u
        mech = entry.get('mechanical_properties', {})
        target = mech.get('sigma_u')

        if target is not None:
            # Если target словарь с min/max, берем среднее
            if isinstance(target, dict):
                if 'min' in target and 'max' in target:
                    target = (target['min'] + target['max']) / 2
                elif 'value' in target:
                    target = target['value']
            row['target'] = float(target)
            rows.append(row)

    if not rows:
        return None, None, None

    df = pd.DataFrame(rows)

    # Заполняем пропуски
    df = df.fillna(0)

    # Отделяем признаки от цели
    target_col = 'target'
    feature_cols = [col for col in df.columns if col != target_col]

    X = df[feature_cols].values
    y = df[target_col].values

    return X, y, feature_cols


# ==================== 2. ОБУЧЕНИЕ МОДЕЛЕЙ ====================

def train_and_select_best(X, y, category_name):
    """
    Обучает XGBoost, Random Forest и LightGBM, выбирает лучшую по R²
    """
    if len(y) < 10:
        print(f"    Недостаточно данных: {len(y)} образцов")
        return None, None, None, None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Масштабирование
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        'xgboost': xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1
        ),
        'random_forest': RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        ),
        'lightgbm': lgb.LGBMRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    }

    results = []

    for model_name, model in models.items():
        try:
            print(f"    Training {model_name}...", end=" ", flush=True)
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)

            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            print(f"R²={r2:.4f}, MAE={mae:.1f} MPa")

            results.append({
                'name': model_name,
                'model': model,
                'r2': r2,
                'mae': mae,
                'rmse': rmse
            })
        except Exception as e:
            print(f"Ошибка: {str(e)[:50]}")
            continue

    if not results:
        return None, None, None, None

    # Выбираем лучшую модель по R²
    best = max(results, key=lambda x: x['r2'])

    print(f"\n    Лучшая модель для {category_name}: {best['name']}")
    print(f"       R²={best['r2']:.4f}, MAE={best['mae']:.1f} MPa")

    return best['model'], scaler, best, results


# ==================== 3. ОБУЧЕНИЕ ДЛЯ ВСЕХ КАТЕГОРИЙ ====================

def train_all_regressors():
    """Обучает регрессоры для ВСЕХ категорий"""

    print("=" * 70)
    print("СБОР ВСЕХ ТИПОВ ПРОКАТКИ ИЗ ДАННЫХ")
    print("=" * 70)

    # Собираем все типы прокатки
    all_rolling_types = collect_all_rolling_types()
    print(f"Найдено {len(all_rolling_types)} типов прокатки")
    print(f"   Первые 10: {', '.join(all_rolling_types[:10])}...")

    print("\n" + "=" * 70)
    print("ИСПОЛЬЗОВАНИЕ ВСЕХ 118 ХИМИЧЕСКИХ ЭЛЕМЕНТОВ")
    print("=" * 70)

    # Получаем ВСЕ 118 элементов
    all_elements = get_all_chemical_elements()
    print(f"Используем ВСЕ {len(all_elements)} химических элементов")

    # Сохраняем список всех элементов и типов прокатки
    with open('aloro/models/all_elements.json', 'w', encoding='utf-8') as f:
        json.dump(all_elements, f, ensure_ascii=False, indent=2)

    with open('aloro/models/all_rolling_types.json', 'w', encoding='utf-8') as f:
        json.dump(all_rolling_types, f, ensure_ascii=False, indent=2)

    categories = ['nickel_alloy', 'titanium_alloy', 'aluminum_alloy',
                  'steel_alloy', 'copper_alloy', 'other']

    results = {}
    model_comparison = {}

    for category in categories:
        print("\n" + "=" * 70)
        print(f"ОБУЧЕНИЕ ДЛЯ КАТЕГОРИИ: {category.upper()}")
        print("=" * 70)

        input_file = f'aloro/split_by_category/{category}.json'
        if not os.path.exists(input_file):
            print(f"  Файл не найден, пропускаем")
            continue

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"  Исходных записей: {len(data)}")

        # Подготавливаем данные
        X, y, feature_cols = prepare_data_with_all_elements(data, all_elements, all_rolling_types)

        if X is None or len(y) == 0:
            print(f"  Нет данных с sigma_u, пропускаем")
            continue

        total_features = len(all_elements) + 1 + len(all_rolling_types)
        print(f"  Образцов с sigma_u: {len(y)}")
        print(f"  Количество признаков: {X.shape[1]} (118 элементов + size + {len(all_rolling_types)} прокатки)")

        # Обучаем и выбираем лучшую модель
        model, scaler, best_info, all_results = train_and_select_best(X, y, category)

        if model is None:
            continue

        # Сохраняем лучшую модель
        model_file = f'aloro/models/{category}_sigma_u.joblib'
        scaler_file = f'aloro/models/{category}_sigma_u_scaler.joblib'

        joblib.dump(model, model_file)
        joblib.dump(scaler, scaler_file)

        # Сохраняем список признаков
        with open(f'aloro/models/{category}_feature_cols.json', 'w', encoding='utf-8') as f:
            json.dump(feature_cols, f, ensure_ascii=False, indent=2)

        results[category] = {
            'best_model': best_info['name'],
            'n_samples': len(y),
            'n_features': X.shape[1],
            'metrics': {
                'r2': best_info['r2'],
                'mae': best_info['mae'],
                'rmse': best_info['rmse']
            }
        }

        model_comparison[category] = all_results

        print(f"\n  Модель сохранена: {model_file}")

    # Сохраняем результаты
    with open('aloro/results/training_results_sigma_u.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    # Создаем отчет
    create_report(results, all_elements, all_rolling_types)
    create_model_comparison_report(model_comparison)

    return results


def create_report(results, all_elements, all_rolling_types):
    """Создает отчет"""

    report_file = 'aloro/results/training_summary_sigma_u.txt'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ОТЧЕТ ОБ ОБУЧЕНИИ РЕГРЕССОРОВ (sigma_u)\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"ХИМИЧЕСКИХ ЭЛЕМЕНТОВ: {len(all_elements)}\n")
        f.write(f"ТИПОВ ПРОКАТКИ: {len(all_rolling_types)}\n")
        f.write(f"ИТОГО ПРИЗНАКОВ: {len(all_elements) + 1 + len(all_rolling_types)}\n\n")

        f.write("-" * 80 + "\n")
        f.write(f"{'Категория':<20} {'Модель':<15} {'Образцов':<10} {'R²':<10} {'MAE':<10}\n")
        f.write("-" * 80 + "\n")

        for category, info in results.items():
            f.write(f"{category:<20} {info['best_model']:<15} {info['n_samples']:<10} ")
            f.write(f"{info['metrics']['r2']:<10.4f} {info['metrics']['mae']:<10.1f}\n")

    print(f"\nОтчет сохранен: {report_file}")


def create_model_comparison_report(model_comparison):
    """Создает детальный отчет о сравнении моделей"""

    report_file = 'aloro/results/model_comparison.md'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Сравнение моделей регрессии (sigma_u)\n\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for category, results in model_comparison.items():
            f.write(f"## {category.upper()}\n\n")
            f.write("| Модель | R² | MAE (MPa) | RMSE (MPa) |\n")
            f.write("|--------|-----|-----------|------------|\n")

            # Сортируем по R²
            sorted_results = sorted(results, key=lambda x: x['r2'], reverse=True)

            for r in sorted_results:
                f.write(f"| {r['name']} | {r['r2']:.4f} | {r['mae']:.1f} | {r['rmse']:.1f} |\n")

            f.write(f"\n**Лучшая модель:** {sorted_results[0]['name']}\n\n")
            f.write("---\n\n")

    print(f"Сравнение моделей сохранено: {report_file}")


# ==================== 4. ЗАПУСК ====================

if __name__ == "__main__":
    print("=" * 70)
    print("ОБУЧЕНИЕ РЕГРЕССОРОВ ДЛЯ ВСЕХ КАТЕГОРИЙ")
    print("ЦЕЛЕВАЯ ПЕРЕМЕННАЯ: sigma_u")
    print("=" * 70)
    print("\nКЛЮЧЕВЫЕ ИЗМЕНЕНИЯ:")
    print("  Сравнение XGBoost, Random Forest, LightGBM")
    print("  Выбирается ЛУЧШАЯ модель по R²")
    print("  ВСЕ модели используют ВСЕ 118 химических элементов")
    print()

    results = train_all_regressors()

    print("\n" + "=" * 70)
    print("ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    print("=" * 70)