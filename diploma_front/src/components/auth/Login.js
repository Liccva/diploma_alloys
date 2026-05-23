import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const Login = () => {
  const [loginValue, setLoginValue] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const validateForm = () => {
    const newErrors = {};
    let isValid = true;

    if (!loginValue.trim()) {
      newErrors.login = "Введите логин";
      isValid = false;
    }

    if (!password) {
      newErrors.password = "Введите пароль";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };
  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");
    setErrors({});

    if (!validateForm()) {
      setFormError("Заполните все поля");
      return;
    }

    setLoading(true);

    try {
      await login(loginValue, password);

      if (rememberMe) {
        localStorage.setItem("rememberedLogin", loginValue);
      } else {
        localStorage.removeItem("rememberedLogin");
      }

      navigate("/dashboard");
    } catch (err) {
      const detail = (err.message || err.response?.data?.detail || "").toLowerCase();

      if (detail.includes("деактивирован") ||
          detail.includes("disabled") ||
          detail.includes("is not active") ||
          detail.includes("аккаунт деактивирован")) {
        setFormError("Аккаунт деактивирован. Обратитесь к администратору.");
      } else if (detail.includes("неверный пароль") ||
                 detail.includes("invalid password") ||
                 detail.includes("incorrect password")) {
        setFormError("Неверный пароль.");
      } else if (detail.includes("не найден") ||
                 detail.includes("not found") ||
                 detail.includes("пользователь не найден")) {
        setFormError("Пользователь не найден.");
      } else {
        setFormError(detail || "Неверный логин или пароль.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e, field) => {
    const value = e.target.value;
    if (field === "login") {
      setLoginValue(value);
    } else {
      setPassword(value);
    }

    if (errors[field]) {
      setErrors({ ...errors, [field]: "" });
    }
    if (formError) {
      setFormError("");
    }
  };

  React.useEffect(() => {
    const remembered = localStorage.getItem("rememberedLogin");
    if (remembered) {
      setLoginValue(remembered);
      setRememberMe(true);
    }
  }, []);

  return (
    <div className="auth-wrapper">
      <div className="login-container">
        <div className="form-header">
          <h2>Добро пожаловать!</h2>
          <p>Войдите в свой аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label htmlFor="login">Логин</label>
            <div className="input-wrapper">
              <input
                type="text"
                id="login"
                value={loginValue}
                onChange={(e) => handleInputChange(e, "login")}
                placeholder="Введите ваш логин"
                required
                maxLength={50}
                className={errors.login ? "error" : ""}
                disabled={loading}
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
                value={password}
                onChange={(e) => handleInputChange(e, "password")}
                placeholder="Введите ваш пароль"
                required
                className={errors.password ? "error" : ""}
                disabled={loading}
              />
            </div>
            {errors.password && <div className="field-error">{errors.password}</div>}
          </div>

          <div className="remember-me">
            <label>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                disabled={loading}
              />
              Запомнить меня
            </label>
            <Link to="/forgot-password" className="forgot-password">
              Забыли пароль?
            </Link>
          </div>

          {formError && <div className="form-error">{formError}</div>}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            data-testid="login-button"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Вход...
              </>
            ) : (
              "Войти"
            )}
          </button>
        </form>

        <div className="form-footer">
          <p>
            Нет аккаунта?{" "}
            <Link to="/register">Зарегистрироваться</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;