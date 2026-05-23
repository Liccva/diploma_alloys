import json
import os
import numpy as np
import pandas as pd
import joblib
import warnings

warnings.filterwarnings('ignore')


class HybridAlloyPredictor:
    """
    Гибридный пайплайн для предсказания свойств сплавов
    Схема: классификация -> выбор регрессора по категории -> предсказание sigma_u
    """

    def __init__(self, models_dir='aloro/models'):
        self.models_dir = models_dir
        self.classifier = None
        self.classifier_scaler = None
        self.encoder = None
        self.classifier_feature_cols = None
        self.regressors = {}
        self.scalers = {}
        self.regressor_feature_cols = {}  # Сохраняем точные имена признаков для каждой модели
        self.load_all_models()

    def load_all_models(self):
        """Загружает классификатор и регрессоры sigma_u"""

        print("=" * 70)
        print("ЗАГРУЗКА ГИБРИДНОГО ПАЙПЛАЙНА (sigma_u)")
        print("=" * 70)

        # 1. Загружаем классификатор
        try:
            self.classifier = joblib.load(f'{self.models_dir}/best_classifier.joblib')
            self.classifier_scaler = joblib.load(f'{self.models_dir}/scaler.joblib')
            self.encoder = joblib.load(f'{self.models_dir}/label_encoder.joblib')
            self.classifier_feature_cols = joblib.load(f'{self.models_dir}/feature_cols.joblib')
            print(f"Классификатор загружен ({len(self.classifier_feature_cols)} признаков)")
        except FileNotFoundError as e:
            print(f"Ошибка загрузки классификатора: {e}")
            raise

        # 2. Загружаем регрессоры sigma_u для каждой категории
        categories = ['nickel_alloy', 'titanium_alloy', 'aluminum_alloy',
                      'steel_alloy', 'copper_alloy', 'other']

        print("\nЗагрузка регрессоров sigma_u:")
        print("-" * 60)

        for category in categories:
            model_file = f'{self.models_dir}/{category}_sigma_u.joblib'
            scaler_file = f'{self.models_dir}/{category}_sigma_u_scaler.joblib'
            feature_cols_file = f'{self.models_dir}/{category}_feature_cols.json'

            if os.path.exists(model_file) and os.path.exists(scaler_file):
                try:
                    model = joblib.load(model_file)
                    scaler = joblib.load(scaler_file)

                    self.regressors[category] = model
                    self.scalers[category] = scaler

                    # Загружаем точные имена признаков для этой модели
                    if os.path.exists(feature_cols_file):
                        with open(feature_cols_file, 'r', encoding='utf-8') as f:
                            self.regressor_feature_cols[category] = json.load(f)
                        print(f"  {category:20s} -> sigma_u ({len(self.regressor_feature_cols[category])} признаков)")
                    else:
                        # Если файла нет, пытаемся определить по модели
                        if hasattr(model, 'feature_names_in_'):
                            self.regressor_feature_cols[category] = list(model.feature_names_in_)
                        elif hasattr(model, 'n_features_in_'):
                            # Создаем стандартные имена
                            self.regressor_feature_cols[category] = [f'feature_{i}' for i in
                                                                     range(model.n_features_in_)]
                        else:
                            self.regressor_feature_cols[category] = None
                        print(f"  {category:20s} -> sigma_u (признаки определены автоматически)")

                except Exception as e:
                    print(f"  {category:20s} -> ошибка загрузки: {e}")
            else:
                print(f"  {category:20s} -> модель не найдена")

        print("\n" + "=" * 70)
        print("ГИБРИДНЫЙ ПАЙПЛАЙН ГОТОВ")
        print("=" * 70)

    def extract_features_for_classifier(self, composition, size=None):
        """Извлекает признаки для классификатора"""
        features = {col: 0.0 for col in self.classifier_feature_cols}

        for element, value in composition.items():
            col_name = f'comp_{element.lower()}'
            if col_name in features:
                if isinstance(value, dict):
                    if 'min' in value and 'max' in value:
                        features[col_name] = (value['min'] + value['max']) / 2
                    elif 'value' in value:
                        features[col_name] = value['value']
                else:
                    features[col_name] = float(value)

        if size is not None and 'size' in self.classifier_feature_cols:
            features['size'] = float(size)

        X = pd.DataFrame([features])
        X = X[self.classifier_feature_cols].fillna(0)
        X_scaled = self.classifier_scaler.transform(X)

        return X_scaled, X

    def extract_features_for_regressor(self, composition, category, size=None, rolling='unknown'):
        """
        Извлекает признаки для регрессора конкретной категории
        Использует ТОЧНЫЕ имена признаков, которые ожидает модель
        """
        if category not in self.regressor_feature_cols:
            raise ValueError(f"Неизвестные признаки для категории {category}")

        expected_cols = self.regressor_feature_cols[category]

        # Создаем словарь признаков
        features = {col: 0.0 for col in expected_cols}

        # Заполняем химические элементы
        for element, value in composition.items():
            # Пробуем разные варианты имени колонки
            possible_names = [
                f'comp_{element.lower()}',
                f'comp_{element}',
                element.lower(),
                element
            ]

            for col_name in possible_names:
                if col_name in features:
                    if isinstance(value, dict):
                        if 'min' in value and 'max' in value:
                            features[col_name] = (value['min'] + value['max']) / 2
                        elif 'value' in value:
                            features[col_name] = value['value']
                    else:
                        features[col_name] = float(value)
                    break

        # Заполняем размер
        if size is not None and 'size' in features:
            features['size'] = float(size)

        # Заполняем тип прокатки
        rolling_col = f'rolling_{rolling}'
        if rolling_col in features:
            features[rolling_col] = 1

        # Также заполняем rolling_unknown если есть
        if 'rolling_unknown' in features and rolling_col not in features:
            features['rolling_unknown'] = 1

        # Создаем DataFrame с правильным порядком колонок
        X = pd.DataFrame([features])
        X = X[expected_cols].fillna(0)

        # Масштабируем
        scaler = self.scalers.get(category)
        if scaler is not None:
            X_scaled = scaler.transform(X)
        else:
            X_scaled = X.values

        return X_scaled

    def predict_category(self, composition, size=None):
        """Предсказывает категорию сплава"""
        X_scaled, _ = self.extract_features_for_classifier(composition, size)

        pred_class = self.classifier.predict(X_scaled)[0]
        category = self.encoder.inverse_transform([pred_class])[0]

        probs = self.classifier.predict_proba(X_scaled)[0]
        confidence = max(probs)

        return category, confidence

    def predict_sigma_u(self, composition, size=None, rolling='unknown'):
        """
        Предсказывает предел прочности (sigma_u) для сплава

        Returns:
            tuple: (prediction, category, confidence, error_message)
        """
        # Сначала определяем категорию
        category, confidence = self.predict_category(composition, size)

        # Проверяем, есть ли модель для этой категории
        if category not in self.regressors:
            return None, category, confidence, f"Нет модели sigma_u для категории {category}"

        # Получаем модель
        model = self.regressors[category]

        # Извлекаем признаки для регрессора
        try:
            X = self.extract_features_for_regressor(composition, category, size, rolling)
            prediction = model.predict(X)[0]
            return prediction, category, confidence, None
        except Exception as e:
            return None, category, confidence, f"Ошибка предсказания: {e}"

    def predict_all_properties(self, composition, size=None, rolling='unknown'):
        """Предсказывает все доступные свойства (сейчас только sigma_u)"""
        sigma_u, category, confidence, error = self.predict_sigma_u(composition, size, rolling)

        results = {
            'category': category,
            'confidence': confidence,
            'properties': {}
        }

        if sigma_u is not None:
            results['properties']['Предел прочности (σ_u), MPa'] = round(float(sigma_u), 1)
        else:
            results['properties']['Предел прочности (σ_u), MPa'] = None
            results['error'] = error

        return results


def test_pipeline():
    """Тестирует пайплайн"""

    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ГИБРИДНОГО ПАЙПЛАЙНА (sigma_u)")
    print("=" * 70)

    predictor = HybridAlloyPredictor()

    test_alloys = [
        {
            'name': 'Нержавеющая сталь 304',
            'composition': {'fe': 70.0, 'cr': 18.0, 'ni': 8.0, 'mn': 2.0, 'c': 0.08, 'si': 0.75},
            'expected': 'steel_alloy',
            'rolling': 'hot'
        },
        {
            'name': 'Алюминиевый сплав Д16',
            'composition': {'al': 93.5, 'cu': 4.4, 'mg': 1.5, 'mn': 0.6, 'fe': 0.5, 'si': 0.5},
            'expected': 'aluminum_alloy',
            'rolling': 'cold'
        },
        {
            'name': 'Титановый сплав ВТ6',
            'composition': {'ti': 89.0, 'al': 6.0, 'v': 4.0, 'fe': 0.3, 'o': 0.2},
            'expected': 'titanium_alloy',
            'rolling': 'unknown'
        },
        {
            'name': 'Бронза БрОЦС5-5-5',
            'composition': {'cu': 85.0, 'sn': 5.0, 'zn': 5.0, 'pb': 5.0},
            'expected': 'copper_alloy',
            'rolling': 'cast'
        },
        {
            'name': 'Никелевый суперсплав Inconel 718',
            'composition': {'ni': 52.5, 'cr': 19.0, 'fe': 18.5, 'nb': 5.1, 'mo': 3.0, 'ti': 0.9, 'al': 0.5},
            'expected': 'nickel_alloy',
            'rolling': 'forged'
        }
    ]

    print("\nРезультаты тестирования:")
    print("-" * 70)

    for alloy in test_alloys:
        print(f"\n{alloy['name']}")
        print(f"   Состав: {alloy['composition']}")
        print(f"   Прокатка: {alloy.get('rolling', 'unknown')}")

        try:
            sigma_u, category, confidence, error = predictor.predict_sigma_u(
                alloy['composition'],
                rolling=alloy.get('rolling', 'unknown')
            )

            print(f"\n   Категория: {category}")
            print(f"      (уверенность: {confidence:.1%})")
            print(f"   Ожидалось: {alloy['expected']}")

            if category == alloy['expected']:
                print("   Категория определена верно")
            else:
                print("   Категория не совпадает с ожидаемой")

            if sigma_u is not None:
                print(f"\n   Предсказанный предел прочности (σ_u): {sigma_u:.1f} MPa")
            else:
                print(f"\n   Ошибка: {error}")

        except Exception as e:
            print(f"   Ошибка: {e}")

    print("\n" + "=" * 70)
    print("Тестирование завершено")
    print("=" * 70)


def interactive_mode():
    """Интерактивный режим"""

    predictor = HybridAlloyPredictor()

    print("\n" + "=" * 70)
    print("ИНТЕРАКТИВНЫЙ РЕЖИМ (sigma_u)")
    print("=" * 70)
    print("\nВведите состав сплава в формате: элемент:значение")
    print("Пример: fe:70, cr:18, ni:8")
    print("Для выхода введите 'exit'\n")

    while True:
        print("-" * 50)
        comp_input = input("Введите состав: ").strip()

        if comp_input.lower() == 'exit':
            break

        if not comp_input:
            continue

        try:
            composition = {}
            parts = comp_input.split(',')
            for part in parts:
                if ':' in part:
                    elem, val = part.split(':')
                    composition[elem.strip().lower()] = float(val.strip())

            if not composition:
                print("Неверный формат")
                continue

            sigma_u, category, confidence, error = predictor.predict_sigma_u(composition)

            print(f"\nРезультаты:")
            print(f"   Категория: {category} (уверенность: {confidence:.1%})")

            if sigma_u is not None:
                print(f"   Предел прочности (σ_u): {sigma_u:.1f} MPa")
            else:
                print(f"   Ошибка: {error}")

        except ValueError:
            print("Ошибка: значения должны быть числами")
        except Exception as e:
            print(f"Ошибка: {e}")


def batch_predict():
    """Пакетный режим для предсказания нескольких сплавов из файла"""

    predictor = HybridAlloyPredictor()

    print("\n" + "=" * 70)
    print("ПАКЕТНЫЙ РЕЖИМ")
    print("=" * 70)

    test_compositions = [
        {"name": "Steel 45", "composition": {"fe": 97, "c": 0.45, "mn": 0.65, "si": 0.25}},
        {"name": "Aluminum D16", "composition": {"al": 93.5, "cu": 4.4, "mg": 1.5, "mn": 0.6}},
        {"name": "Titanium VT6", "composition": {"ti": 89, "al": 6, "v": 4, "fe": 0.3}},
        {"name": "Brass L63", "composition": {"cu": 63, "zn": 37}},
        {"name": "Inconel 718", "composition": {"ni": 52.5, "cr": 19, "fe": 18.5, "nb": 5.1}},
    ]

    print("\nРезультаты пакетного предсказания:")
    print("-" * 80)
    print(f"{'Название':<20} {'Категория':<18} {'σ_u (MPa)':<12} {'Уверенность':<12}")
    print("-" * 80)

    for item in test_compositions:
        sigma_u, category, confidence, error = predictor.predict_sigma_u(item["composition"])

        if sigma_u is not None:
            print(f"{item['name']:<20} {category:<18} {sigma_u:<12.1f} {confidence:<12.1%}")
        else:
            print(f"{item['name']:<20} {category:<18} {'Ошибка':<12} {confidence:<12.1%}")

    print("-" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Гибридный предсказатель свойств сплавов')
    parser.add_argument('--mode', type=str, default='test',
                        choices=['test', 'interactive', 'batch'],
                        help='Режим работы: test, interactive, batch')

    args = parser.parse_args()

    if args.mode == 'test':
        test_pipeline()
    elif args.mode == 'interactive':
        interactive_mode()
    elif args.mode == 'batch':
        batch_predict()