"""
Нагрузочное тестирование API металлических сплавов
Запуск: locust -f locust_tests.py --host=http://localhost:8000
"""

from locust import HttpUser, task, between, tag, events
import random
import time

# ========== ТЕСТОВЫЕ ДАННЫЕ ==========

# ВАЖНО: Используйте ТОЛЬКО существующие ID из вашей БД!
# Сначала проверьте реальные ID через API или БД
KNOWN_PATENT_IDS = [1, 2, 3, 4, 5]  # Замените на реальные ID патентов
KNOWN_ELEMENT_IDS = list(range(1, 11))  # ID химических элементов

ALLOY_CATEGORIES = ["steel", "stainless_steel", "tool_steel", "cast_iron", "aluminum_alloy", "titanium_alloy",
                    "nickel_alloy"]
ROLLING_TYPES = ["hot", "cold", "warm", "isothermal"]
PROP_VALUES = [100.5, 250.0, 500.0, 750.0, 1000.0]
TEMPERATURES = [800.0, 900.0, 950.0, 1000.0, 1050.0]
ML_MODEL_IDS = [1, 2, 3, 4]

# Тестовый пользователь (должен существовать в БД с ролью researcher)
TEST_USER = {
    "login": "researcher",
    "password": "res123",
}


class MetalAlloysAPIUser(HttpUser):
    wait_time = between(1, 3)

    access_token = None
    refresh_token = None

    def on_start(self):
        """Выполняется при запуске каждого пользователя"""
        self.authenticate()

    def authenticate(self):
        """Аутентификация"""
        with self.client.post(
                "/api/auth/login",
                json={
                    "login": TEST_USER["login"],
                    "password": TEST_USER["password"],
                    "device_name": "Locust"
                },
                catch_response=True,
                name="AUTH Login",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                print(f"[OK] Login successful: {TEST_USER['login']}")
                response.success()
            else:
                print(f"[WARN] Login failed for {TEST_USER['login']}: {response.status_code}")
                response.success()  # Не считаем ошибкой

    def get_headers(self):
        """Заголовки с токеном"""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    # ========== ПУБЛИЧНЫЕ ЭНДПОИНТЫ (не требуют авторизации) ==========

    @tag("public")
    @task(10)
    def get_all_elements(self):
        """GET /api/elements/"""
        with self.client.get(
                "/api/elements/",
                name="GET /api/elements/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(8)
    def get_all_alloys(self):
        """GET /api/alloys/"""
        skip = random.randint(0, 50)
        limit = random.randint(10, 50)
        with self.client.get(
                f"/api/alloys/?skip={skip}&limit={limit}",
                name="GET /api/alloys/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(6)
    def get_all_patents(self):
        """GET /api/patents/"""
        with self.client.get(
                "/api/patents/",
                name="GET /api/patents/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(5)
    def get_element_by_id(self):
        """GET /api/elements/{id}"""
        element_id = random.choice(KNOWN_ELEMENT_IDS)
        with self.client.get(
                f"/api/elements/{element_id}",
                name="GET /api/elements/{id}",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(4)
    def get_alloy_by_id(self):
        """GET /api/alloys/{id}"""
        alloy_id = random.randint(1, 100)
        with self.client.get(
                f"/api/alloys/{alloy_id}",
                name="GET /api/alloys/{id}",
                catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(4)
    def get_patent_by_id(self):
        """GET /api/patents/{id}"""
        patent_id = random.choice(KNOWN_PATENT_IDS)
        with self.client.get(
                f"/api/patents/{patent_id}",
                name="GET /api/patents/{id}",
                catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(3)
    def search_alloys_by_category(self):
        """GET /api/alloys/category/{category}"""
        category = random.choice(ALLOY_CATEGORIES)
        with self.client.get(
                f"/api/alloys/category/{category}",
                name="GET /api/alloys/category/{category}",
                catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(3)
    def get_alloy_elements(self):
        """GET /api/alloys/{id}/elements"""
        alloy_id = random.randint(1, 100)
        with self.client.get(
                f"/api/alloys/{alloy_id}/elements",
                name="GET /api/alloys/{id}/elements",
                catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(5)
    def ml_predict(self):
        """POST /api/ml/predict"""
        elements = []
        for _ in range(random.randint(1, 3)):
            elements.append({
                "element_id": random.choice(KNOWN_ELEMENT_IDS),
                "percentage": round(random.uniform(0.5, 95.0), 1)
            })

        predict_data = {
            "ml_model_id": random.choice(ML_MODEL_IDS),
            "category": random.choice(ALLOY_CATEGORIES),
            "rolling_type": random.choice(ROLLING_TYPES),
            "temperature": random.choice(TEMPERATURES),
            "elements": elements
        }

        with self.client.post(
                "/api/ml/predict",
                json=predict_data,
                name="POST /api/ml/predict",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("public")
    @task(3)
    def find_similar_alloys(self):
        """POST /api/ml/find-similar"""
        composition = {
            "Fe": round(random.uniform(50, 98), 1),
            "C": round(random.uniform(0.1, 2.0), 2),
            "Cr": round(random.uniform(0, 18), 1),
        }

        with self.client.post(
                "/api/ml/find-similar",
                json={"composition": composition, "limit": 10},
                name="POST /api/ml/find-similar",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ========== ЗАЩИЩЕННЫЕ ЭНДПОИНТЫ ==========

    @tag("protected")
    @task(3)
    def get_my_predictions(self):
        """GET /api/predictions/"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/predictions/",
                headers=self.get_headers(),
                name="GET /api/predictions/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(2)
    def get_organizations(self):
        """GET /api/organizations/"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/organizations/",
                headers=self.get_headers(),
                name="GET /api/organizations/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(2)
    def get_roles(self):
        """GET /api/roles/"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/roles/",
                headers=self.get_headers(),
                name="GET /api/roles/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(2)
    def get_models(self):
        """GET /api/models/"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/models/",
                headers=self.get_headers(),
                name="GET /api/models/",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(1)
    def get_me(self):
        """GET /api/auth/me"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/auth/me",
                headers=self.get_headers(),
                name="GET /api/auth/me",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(1)
    def get_profile(self):
        """GET /api/auth/profile"""
        if not self.access_token:
            return

        with self.client.get(
                "/api/auth/profile",
                headers=self.get_headers(),
                name="GET /api/auth/profile",
                catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @tag("protected")
    @task(1)
    def create_alloy(self):
        """POST /api/alloys/ - создание сплава (требует валидный patent_id)"""
        if not self.access_token:
            return

        # Используем ТОЛЬКО существующие patent_id
        if not KNOWN_PATENT_IDS:
            return

        alloy_data = {
            "prop_value": random.choice(PROP_VALUES),
            "temperature": random.choice(TEMPERATURES),
            "category": random.choice(ALLOY_CATEGORIES),
            "rolling_type": random.choice(ROLLING_TYPES),
            "patent_id": random.choice(KNOWN_PATENT_IDS),
        }

        with self.client.post(
                "/api/alloys/",
                json=alloy_data,
                headers=self.get_headers(),
                name="POST /api/alloys/",
                catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code in [401, 403]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}, Response: {response.text[:100]}")

    @tag("protected")
    @task(1)
    def create_prediction(self):
        """POST /api/predictions/"""
        if not self.access_token:
            return

        prediction_data = {
            "prop_value": random.choice(PROP_VALUES),
            "temperature": random.choice(TEMPERATURES),
            "category": random.choice(ALLOY_CATEGORIES),
            "ml_model_id": random.choice(ML_MODEL_IDS),
            "rolling_type": random.choice(ROLLING_TYPES),
        }

        with self.client.post(
                "/api/predictions/",
                json=prediction_data,
                headers=self.get_headers(),
                name="POST /api/predictions/",
                catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code in [401, 403]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    # ========== СТРЕСС-ТЕСТЫ ==========

    @tag("stress")
    @task(15)
    def stress_get_random(self):
        """Стресс-тест: случайные GET запросы"""
        endpoints = [
            ("/api/elements/", "STRESS GET /api/elements/"),
            ("/api/alloys/?skip=0&limit=50", "STRESS GET /api/alloys/"),
            ("/api/patents/", "STRESS GET /api/patents/"),
        ]

        url, name = random.choice(endpoints)

        with self.client.get(
                url,
                name=name,
                catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length,
                       exception, context, **kwargs):
    """Логирование ошибок"""
    if exception:
        if "ConnectionRefusedError" not in str(exception):
            print(f"[ERROR] {request_type} {name}: {str(exception)[:80]}")
    elif response_time > 5000:
        print(f"[SLOW] {request_type} {name}: {response_time}ms")


if __name__ == "__main__":
    import subprocess
    import sys

    print("=" * 60)
    print("Запуск Locust для нагрузочного тестирования")
    print("=" * 60)
    print("\nПеред запуском:")
    print("1. Убедитесь, что сервер запущен на http://localhost:8000")
    print("2. Проверьте, что пользователь 'researcher' с паролем 'res123' существует")
    print("3. Проверьте, что в KNOWN_PATENT_IDS указаны реальные ID патентов из БД")
    print(f"\nТекущие KNOWN_PATENT_IDS: {KNOWN_PATENT_IDS}")
    print("=" * 60)

    subprocess.run([
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", "http://localhost:8000"
    ])