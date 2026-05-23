import React, { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";

const publicApi = axios.create({
  baseURL: "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
});

const Register = () => {
  const [loadingData, setLoadingData] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    middle_name: "",
    email: "",
    organization: "",
    login: "",
    password: "",
    confirmPassword: "",
  });

  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const checkApi = async () => {
      try {
        setLoadingData(true);
        setLoadError("");
        await publicApi.get("/roles/");
        if (!cancelled) setLoadingData(false);
      } catch (err) {
        if (!cancelled) {
          setLoadError("Ошибка подключения к серверу: " + err.message);
          setLoadingData(false);
        }
      }
    };
    checkApi();
    return () => { cancelled = true; };
  }, []);

  const validate = () => {
    const e = {};
    if (!form.first_name.trim() || form.first_name.trim().length < 2)
      e.first_name = "Имя: минимум 2 символа";
    if (!form.last_name.trim() || form.last_name.trim().length < 2)
      e.last_name = "Фамилия: минимум 2 символа";
    if (!form.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim()))
      e.email = "Введите корректный email";
    const l = form.login.trim();
    if (!l || l.length < 3 || l.length > 20)
      e.login = "Логин: от 3 до 20 символов";
    if (!form.password || form.password.length < 6)
      e.password = "Пароль: минимум 6 символов";
    if (!form.confirmPassword)
      e.confirmPassword = "Повторите пароль";
    else if (form.password !== form.confirmPassword)
      e.confirmPassword = "Пароли не совпадают";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (errors[name]) setErrors((p) => ({ ...p, [name]: "" }));
    if (formError) setFormError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!validate()) return;

    setLoading(true);
    try {
      const researcherRoleId = 2;

      const body = {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        login: form.login.trim(),
        password: form.password,
        role_id: researcherRoleId,
      };

      if (form.middle_name.trim()) body.middle_name = form.middle_name.trim();
      if (form.organization.trim()) body.organization = form.organization.trim();

      await publicApi.post("/persons/", body);

      alert("Аккаунт успешно создан! Теперь вы можете войти.");
      navigate("/login");
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d) => `${d.loc?.join(".")}: ${d.msg}`).join("; ")
        : typeof detail === "string"
        ? detail
        : err.message || "Ошибка регистрации";
      setFormError(msg);
      console.error("Register error:", err.response?.data || err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="login-container register-container">
        <div className="form-header">
          <div className="form-header-icon"></div>
          <h2>Регистрация</h2>
          <p>Создайте аккаунт для работы с системой</p>
        </div>

        {loadError && (
          <div className="form-error">
            {loadError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="last_name">Фамилия</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="last_name"
                name="last_name"
                placeholder="Введите фамилию"
                value={form.last_name}
                onChange={handleChange}
                maxLength={50}
                disabled={loading}
                className={errors.last_name ? "error" : ""}
              />
            </div>
            {errors.last_name && <div className="field-error">{errors.last_name}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="first_name">Имя</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="first_name"
                name="first_name"
                placeholder="Введите имя"
                value={form.first_name}
                onChange={handleChange}
                maxLength={50}
                disabled={loading}
                className={errors.first_name ? "error" : ""}
              />
            </div>
            {errors.first_name && <div className="field-error">{errors.first_name}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="middle_name">Отчество</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="middle_name"
                name="middle_name"
                placeholder="Введите отчество (необязательно)"
                value={form.middle_name}
                onChange={handleChange}
                maxLength={50}
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <div className="input-wrapper">
              <input
                type="email"
                id="email"
                name="email"
                placeholder="example@mail.com"
                value={form.email}
                onChange={handleChange}
                maxLength={100}
                disabled={loading}
                className={errors.email ? "error" : ""}
              />
            </div>
            {errors.email && <div className="field-error">{errors.email}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="organization">Организация</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="organization"
                name="organization"
                placeholder="Введите название организации (необязательно)"
                value={form.organization}
                onChange={handleChange}
                maxLength={200}
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="login">Логин</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="login"
                name="login"
                placeholder="От 3 до 20 символов"
                value={form.login}
                onChange={handleChange}
                maxLength={20}
                disabled={loading}
                className={errors.login ? "error" : ""}
              />
            </div>
            {errors.login && <div className="field-error">{errors.login}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Пароль</label>
            <div className="input-wrapper">
              <input
                type="password"
                id="password"
                name="password"
                placeholder="Минимум 6 символов"
                value={form.password}
                onChange={handleChange}
                disabled={loading}
                className={errors.password ? "error" : ""}
              />
            </div>
            {errors.password && <div className="field-error">{errors.password}</div>}
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Подтверждение пароля</label>
            <div className="input-wrapper">
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                placeholder="Повторите пароль"
                value={form.confirmPassword}
                onChange={handleChange}
                disabled={loading}
                className={errors.confirmPassword ? "error" : ""}
              />
            </div>
            {errors.confirmPassword && <div className="field-error">{errors.confirmPassword}</div>}
          </div>

          {formError && <div className="form-error">{formError}</div>}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || loadingData}
          >
            {loading ? "Регистрация..." : "Зарегистрироваться"}
          </button>
        </form>

        <div className="form-footer">
          <p>
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;