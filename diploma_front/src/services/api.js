import axios from "axios";

const API_BASE = 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Флаг для предотвращения циклического обновления токена
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Перехватчик для авторизации
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Перехватчик для обновления токена
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // НЕ пытаемся обновить токен для:
    // 1. Запросов логина
    // 2. Запросов обновления токена (чтобы избежать рекурсии)
    // 3. Уже повторенных запросов
    if (originalRequest.url?.includes('/auth/login') ||
        originalRequest.url?.includes('/auth/refresh') ||
        originalRequest._retry) {
      return Promise.reject(error);
    }

    // Обрабатываем только 401 ошибки
    if (error.response?.status !== 401) {
      return Promise.reject(error);
    }

    // Проверяем, есть ли refresh_token
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      // Нет refresh_token - сразу на страницу логина
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // Если уже идет процесс обновления, добавляем запрос в очередь
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(token => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      }).catch(err => {
        return Promise.reject(err);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Пытаемся обновить токен
      const response = await axios.post(`${API_BASE}/auth/refresh`, {
        refresh_token: refreshToken
      });

      const newAccessToken = response.data.access_token;
      const newRefreshToken = response.data.refresh_token;

      // Сохраняем новые токены
      localStorage.setItem("access_token", newAccessToken);
      if (newRefreshToken) {
        localStorage.setItem("refresh_token", newRefreshToken);
      }

      // Обновляем заголовок для повторного запроса
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;

      // Обрабатываем очередь
      processQueue(null, newAccessToken);

      // Повторяем оригинальный запрос
      return api(originalRequest);
    } catch (refreshError) {
      // Ошибка при обновлении токена
      processQueue(refreshError, null);

      // Очищаем все данные авторизации
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("user");

      // Перенаправляем на страницу логина
      window.location.href = '/login';

      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// ========== AUTH ==========
export const authService = {
  // Вход в систему
  login: async (login, password, deviceName = "Web Browser") => {
    try {
      const response = await api.post("/auth/login", {
        login,
        password,
        device_name: deviceName
      });

      const { access_token, refresh_token } = response.data;
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      // Получаем информацию о пользователе
      const userInfo = await api.get("/auth/me");

      return {
        success: true,
        user: userInfo.data,
        access_token,
        refresh_token
      };
    } catch (error) {
      console.error("Login error:", error.response?.data);

      // Извлекаем сообщение об ошибке из разных возможных форматов ответа
      let errorMessage = "Ошибка аутентификации";

      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }

      // Пробрасываем ошибку с понятным сообщением
      const errorObj = new Error(errorMessage);
      errorObj.response = error.response;
      throw errorObj;
    }
  },

  // Остальные методы остаются без изменений...
  register: async (userData) => {
    const response = await api.post("/persons/", userData);
    return response.data;
  },

  logout: async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch (e) {
        console.error("Logout error:", e);
      }
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    return { success: true };
  },

  refreshToken: async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) throw new Error("No refresh token");
    const response = await api.post("/auth/refresh", { refresh_token: refreshToken });
    localStorage.setItem("access_token", response.data.access_token);
    if (response.data.refresh_token) {
      localStorage.setItem("refresh_token", response.data.refresh_token);
    }
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get("/auth/profile");
    return response.data;
  },

  isAuthenticated: () => {
    const token = localStorage.getItem("access_token");
    return !!token;
  },

  changePassword: async (oldPassword, newPassword) => {
    const response = await api.post("/auth/change-password", {
      old_password: oldPassword,
      new_password: newPassword,
    });
    return response.data;
  }
};

// ========== ELEMENTS ==========
export const elementService = {
  getAll: () => api.get("/elements/"),
  getById: (id) => api.get(`/elements/${id}`),
  getBySymbol: (symbol) => api.get(`/elements/symbol/${symbol}`),
  create: (data) => api.post("/elements/", data), // только админ
};

// ========== PATENTS ==========
export const patentService = {
  getAll: (skip = 0, limit = 100) => api.get("/patents/", { params: { skip, limit } }),
  getForAlloy: () => api.get('/patents/for-alloy/'),
  getById: (id) => api.get(`/patents/${id}`),
  getAllWithAuthors: (skip = 0, limit = 100) => api.get("/patents/with-authors/", { params: { skip, limit } }),
  getByNumber: (number) => api.get(`/patents/number/${number}`),
  create: (data) => api.post("/patents/", data),
  createWithAuthors: (data) => api.post("/patents/with-authors/", data),
  update: (id, data) => api.put(`/patents/${id}`, data),
  delete: (id) => api.delete(`/patents/${id}`),
  getAuthors: (patentId) => api.get(`/patents/${patentId}/authors`),
  addAuthor: (patentId, authorName, authorOrder, personId = null) =>
    api.post(`/patents/${patentId}/authors?author_name=${encodeURIComponent(authorName)}&author_order=${authorOrder}${personId ? `&person_id=${personId}` : ''}`),
  deleteAuthor: (authorId) => api.delete(`/patents/authors/${authorId}`),
  uploadPdf: (patentId, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/patents/${patentId}/upload-pdf`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deletePdf: (patentId) => api.delete(`/patents/${patentId}/pdf`),
};

// ========== ALLOYS ==========
export const alloyService = {
  getAll: (skip = 0, limit = 100) => api.get("/alloys/", { params: { skip, limit } }),
  getById: (id) => api.get(`/alloys/${id}`),
  create: (data) => api.post("/alloys/", data),
  update: (id, data) => api.put(`/alloys/${id}`, data),
  delete: (id) => api.delete(`/alloys/${id}`),

  getElements: (alloyId) => api.get(`/alloys/${alloyId}/elements`),
  addElement: (alloyId, elementId, percentage) =>
    api.post(`/alloys/${alloyId}/elements/${elementId}?percentage=${percentage}`),
  removeElement: (alloyId, elementId) =>
    api.delete(`/alloys/${alloyId}/elements/${elementId}`),

  searchByCategory: (category) => api.get(`/alloys/category/${category}`),
  getByPatent: (patentId) => api.get(`/alloys/patent/${patentId}`),

  createWithElements: async (alloyData, elements = []) => {
    const createRes = await api.post("/alloys/", alloyData);
    const created = createRes.data;

    if (!created || created.id == null) {
      throw new Error("Backend не вернул id созданного сплава");
    }

    const alloyId = created.id;
    for (const el of elements) {
      if (el && el.element_id != null && el.percentage != null) {
        await api.post(`/alloys/${alloyId}/elements/${el.element_id}?percentage=${el.percentage}`);
      }
    }

    return created;
  },
};

// ========== MODELS ==========
export const modelService = {
  getAll: () => api.get("/models/"),
  getById: (id) => api.get(`/models/${id}`),
  create: (data) => api.post("/models/", data), // только админ
  delete: (id) => api.delete(`/models/${id}`), // только админ
  getPredictions: (modelId) => api.get(`/models/${modelId}/predictions`),
};

// ========== PREDICTIONS ==========
export const predictionService = {
  getMyPredictions: (skip = 0, limit = 100) =>
    api.get("/predictions/", { params: { skip, limit } }),
  getById: (id) => api.get(`/predictions/${id}`),
  create: (data) => api.post("/predictions/", data),
  update: (id, data) => api.put(`/predictions/${id}`, data),
  delete: (id) => api.delete(`/predictions/${id}`),

  getElements: (predictionId) => api.get(`/predictions/${predictionId}/elements`),
  addElement: (predictionId, elementId, percentage) =>
    api.post(`/predictions/${predictionId}/elements/${elementId}?percentage=${percentage}`),
  removeElement: (predictionId, elementId) =>
    api.delete(`/predictions/${predictionId}/elements/${elementId}`),

  getByPerson: (personId) => api.get(`/predictions/person/${personId}`),
  getByElement: (elementId) => api.get(`/predictions/element/${elementId}`),
  getByModel: (modelId) => api.get(`/predictions/model/${modelId}`),

  createWithElements: async (predictionData, elements = []) => {
    const createRes = await api.post("/predictions/", predictionData);
    const created = createRes.data;

    const predictionId = created.id;
    if (!predictionId) {
      throw new Error("Не удалось получить ID созданного прогноза");
    }

    for (const el of elements) {
      if (el && el.element_id != null && el.percentage != null) {
        await api.post(`/predictions/${predictionId}/elements/${el.element_id}?percentage=${el.percentage}`);
      }
    }

    return { ...created, id: predictionId };
  },
};

// ========== PERSONS (админ только) ==========
export const personService = {
  getAll: () => api.get("/persons/"),
  getById: (id) => api.get(`/persons/${id}`),
  getByLogin: (login) => api.get(`/persons/login/${encodeURIComponent(login)}`),
  getByEmail: (email) => api.get(`/persons/email/${encodeURIComponent(email)}`),
  create: (data) => api.post("/persons/", data),
  update: (id, data) => api.put(`/persons/${id}`, data),
  updateProfile: (id, data) => api.put(`/persons/${id}/profile`, data),
  delete: (id) => api.delete(`/persons/${id}`),
  getByRole: (roleId) => api.get(`/persons/role/${roleId}`),
  uploadAvatar: (id, file) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/persons/${id}/upload-avatar`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteAvatar: (id) => api.delete(`/persons/${id}/avatar`),
  getAvatarUrl: (id) => `http://localhost:8000/api/persons/${id}/avatar`,
  deactivate: (id) => api.post(`/persons/${id}/deactivate`),
  activate:   (id) => api.post(`/persons/${id}/activate`),
};

// ========== ROLES ==========
export const roleService = {
  getAll: () => api.get("/roles/"),
  getById: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post("/roles/", data), // только админ
  delete: (id) => api.delete(`/roles/${id}`), // только админ
};

// ========== ORGANIZATIONS ==========
export const organizationService = {
  getAll: (skip = 0, limit = 100) => api.get("/organizations/", { params: { skip, limit } }),
  getById: (id) => api.get(`/organizations/${id}`),
  create: (data) => api.post("/organizations/", data), // только админ
  update: (id, data) => api.put(`/organizations/${id}`, data), // только админ
  delete: (id) => api.delete(`/organizations/${id}`), // только админ
};

// ========== DEVICES ==========
export const deviceService = {
  getUserDevices: (personId) => api.get(`/persons/${personId}/devices`),
};

// ========== ADMIN ==========
export const adminService = {
  grantRoleToOrganization: (organizationId, roleId) => 
    api.post("/admin/grant_role", { organization_id: organizationId, role_id: roleId }),
};

// ========== ML ==========
export const mlService = {
  predict: (data) => api.post("/ml/predict", data),
  findSimilar: (composition, limit = 10) => 
    api.post("/ml/find-similar", { composition, limit }),
};

// ========== STATISTICS ==========
export const statsService = {
  getAlloyCount: async () => {
    const res = await alloyService.getAll();
    return res.data?.length || 0;
  },
  getPredictionCount: async () => {
    const res = await predictionService.getMyPredictions();
    return res.data?.length || 0;
  },
  getPatentCount: async () => {
    const res = await patentService.getAll();
    return res.data?.length || 0;
  },
  getRecentAlloys: async (limit = 5) => {
    const res = await alloyService.getAll(0, limit);
    return (res.data || []).sort((a, b) => b.id - a.id);
  },
  getRecentPredictions: async (limit = 5) => {
    const res = await predictionService.getMyPredictions(0, limit);
    return (res.data || []).sort((a, b) => b.id - a.id);
  },
};

// Экспорт всех сервисов
export default {
  api,
  authService,
  elementService,
  patentService,
  alloyService,
  modelService,
  predictionService,
  personService,
  roleService,
  organizationService,
  deviceService,
  adminService,
  mlService,
  statsService,
};