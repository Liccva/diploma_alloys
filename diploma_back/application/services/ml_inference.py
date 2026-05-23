import os
import json
import joblib
import pandas as pd
import numpy as np
import warnings
from typing import Dict, Optional, Tuple

warnings.filterwarnings('ignore')


class MLInference:
    """Инференс для ML моделей сплавов"""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.ml_models_dir = os.path.join(self.base_dir, "ml_models")

        # Классификатор (определяет категорию)
        self.classifier = None
        self.classifier_scaler = None
        self.encoder = None
        self.classifier_feature_cols = None

        # Регрессоры для каждой категории
        self.regressors = {}
        self.scalers = {}

        # Данные для признаков
        self.all_elements = None
        self.all_rolling_types = None

        self.load_models()

    def load_models(self):
        """Загружает классификатор и регрессоры"""
        print("=" * 60)
        print("Загрузка ML моделей...")
        print("=" * 60)

        if not os.path.exists(self.ml_models_dir):
            print(f"Директория не найдена: {self.ml_models_dir}")
            return

        # 1. Загружаем классификатор с обработкой ошибок
        try:
            self.classifier = joblib.load(os.path.join(self.ml_models_dir, "best_classifier.joblib"))
            self.classifier_scaler = joblib.load(os.path.join(self.ml_models_dir, "scaler.joblib"))
            self.encoder = joblib.load(os.path.join(self.ml_models_dir, "label_encoder.joblib"))
            self.classifier_feature_cols = joblib.load(os.path.join(self.ml_models_dir, "feature_cols.joblib"))
            print(f"Классификатор загружен ({len(self.classifier_feature_cols)} признаков)")
        except Exception as e:
            print(f"Ошибка загрузки классификатора: {e}")
            print("   Будет использован fallback классификатор")
            self.classifier = None

        # 2. Загружаем элементы
        try:
            elements_path = os.path.join(self.ml_models_dir, "all_elements.json")
            if os.path.exists(elements_path):
                with open(elements_path, 'r', encoding='utf-8') as f:
                    self.all_elements = json.load(f)
                print(f"Загружено {len(self.all_elements)} элементов")
            else:
                self.all_elements = self._get_default_elements()
                print(f"Используем стандартные элементы ({len(self.all_elements)})")
        except Exception as e:
            self.all_elements = self._get_default_elements()
            print(f"Ошибка загрузки элементов: {e}")

        # 3. Загружаем типы прокатки
        try:
            rolling_path = os.path.join(self.ml_models_dir, "all_rolling_types.json")
            if os.path.exists(rolling_path):
                with open(rolling_path, 'r', encoding='utf-8') as f:
                    self.all_rolling_types = json.load(f)
                print(f"Загружено {len(self.all_rolling_types)} типов прокатки")
            else:
                self.all_rolling_types = ['unknown', 'hot', 'cold', 'cast', 'forged']
                print(f"Используем стандартные типы прокатки")
        except Exception as e:
            self.all_rolling_types = ['unknown', 'hot', 'cold', 'cast', 'forged']
            print(f"Ошибка загрузки типов прокатки: {e}")

        # 4. Загружаем регрессоры для каждой категории
        categories = ['nickel_alloy', 'titanium_alloy', 'aluminum_alloy',
                      'steel_alloy', 'copper_alloy', 'other']

        for category in categories:
            model_file = os.path.join(self.ml_models_dir, f"{category}_sigma_u.joblib")
            scaler_file = os.path.join(self.ml_models_dir, f"{category}_sigma_u_scaler.joblib")

            if os.path.exists(model_file):
                try:
                    self.regressors[category] = joblib.load(model_file)
                    if os.path.exists(scaler_file):
                        self.scalers[category] = joblib.load(scaler_file)
                    print(f"Загружен регрессор для {category}")
                except Exception as e:
                    print(f"Ошибка загрузки {category}: {e}")

        print(f"Загружено регрессоров: {len(self.regressors)} из {len(categories)}")
        print("=" * 60)

    def _get_default_elements(self) -> list:
        """Возвращает список 118 элементов"""
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

    def _fallback_category(self, composition: Dict[str, float]) -> str:
        """Fallback определение категории по основному элементу"""
        # Находим элемент с максимальным содержанием
        if not composition:
            return 'other'

        main_element = max(composition.items(), key=lambda x: x[1])[0] if composition else ''

        if main_element in ['ni', 'nickel'] or composition.get('ni', 0) > 50:
            return 'nickel_alloy'
        if main_element in ['ti', 'titanium'] or composition.get('ti', 0) > 50:
            return 'titanium_alloy'
        if main_element in ['al', 'aluminum', 'aluminium'] or composition.get('al', 0) > 50:
            return 'aluminum_alloy'
        if main_element in ['fe', 'iron'] or composition.get('fe', 0) > 50:
            return 'steel_alloy'
        if main_element in ['cu', 'copper'] or composition.get('cu', 0) > 50:
            return 'copper_alloy'

        return 'other'

    def predict_category(self, composition: Dict[str, float], size: Optional[float] = None) -> Tuple[str, float]:
        """Определяет категорию сплава"""
        # Если классификатор не загружен, используем fallback
        if self.classifier is None or self.classifier_feature_cols is None:
            category = self._fallback_category(composition)
            print(f"Fallback категория: {category}")
            return category, 0.8

        try:
            # Создаем признаки для классификатора
            features = {col: 0.0 for col in self.classifier_feature_cols}

            for element, value in composition.items():
                col_name = f'comp_{element.lower()}'
                if col_name in features:
                    features[col_name] = float(value)

            if size is not None and 'size' in self.classifier_feature_cols:
                features['size'] = float(size)

            X = pd.DataFrame([features])
            X = X[self.classifier_feature_cols].fillna(0)
            X_scaled = self.classifier_scaler.transform(X)

            pred_class = self.classifier.predict(X_scaled)[0]
            category = self.encoder.inverse_transform([pred_class])[0]

            probs = self.classifier.predict_proba(X_scaled)[0]
            confidence = max(probs)

            return category, confidence

        except Exception as e:
            print(f"Ошибка классификации: {e}, используем fallback")
            return self._fallback_category(composition), 0.5

    def extract_regressor_features(self, composition: Dict[str, float], size: Optional[float] = None,
                                   rolling_type: str = "unknown") -> np.ndarray:
        """Извлекает признаки для регрессора"""
        features = []

        # 118 элементов
        for element in self.all_elements:
            value = composition.get(element, 0)
            features.append(float(value) if value else 0.0)

        # size
        features.append(float(size) if size else 0.0)

        # one-hot для типов прокатки
        for rt in self.all_rolling_types:
            features.append(1.0 if rt == rolling_type else 0.0)

        return np.array([features])

    def predict_sigma_u(self, composition: Dict[str, float], size: Optional[float] = None,
                        rolling_type: str = "unknown") -> Tuple[float, str, float]:
        """
        Предсказывает sigma_u.
        Автоматически определяет категорию и выбирает модель.

        Returns:
            (sigma_u, категория, уверенность)
        """
        # 1. Определяем категорию
        category, confidence = self.predict_category(composition, size)
        print(f"Категория: {category} (уверенность: {confidence:.1%})")

        # 2. Проверяем модель для категории
        if category not in self.regressors:
            # Пробуем alternative
            alt = self._fallback_category(composition)
            if alt in self.regressors:
                category = alt
                print(f"   Используем альтернативную категорию: {category}")
            else:
                raise ValueError(f"Нет модели для категории {category}")

        # 3. Извлекаем признаки
        X = self.extract_regressor_features(composition, size, rolling_type)

        # 4. Масштабируем
        scaler = self.scalers.get(category)
        if scaler:
            X_scaled = scaler.transform(X)
        else:
            X_scaled = X

        # 5. Предсказываем
        model = self.regressors[category]
        prediction = model.predict(X_scaled)[0]

        # Ограничиваем
        prediction = max(0, min(2000, prediction))

        return prediction, category, confidence

    # Для совместимости со старым API
    def predict(self, ml_model_id: int, category: str, rolling_type: str,
                size: float, composition_by_symbol: Dict[str, float],
                temperature: float = None) -> float:
        """Старый метод для обратной совместимости"""
        prediction, detected_category, confidence = self.predict_sigma_u(
            composition_by_symbol, size, rolling_type
        )
        return prediction


ml_inference = MLInference()