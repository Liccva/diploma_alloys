import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Home = () => {
  const { isAuthenticated, isAdmin, isResearcher } = useAuth();

  return (
    <div className="home-page">
      {/* Hero секция */}
      <div className="hero-section">
        <div className="hero-badge">Патентная аналитика сплавов</div>
        <h1>Metal Alloys</h1>
        <p className="hero-subtitle">
          Система хранения и анализа данных о металлических сплавах
          с возможностью прогнозирования механических свойств
        </p>

        <div className="hero-stats">
          <div className="hero-stat">
            <span className="hero-stat-value">Предел прочности</span>
            <span className="hero-stat-label">Прогнозирование σ<sub>в</sub></span>
          </div>
          <div className="hero-stat-divider"></div>
          <div className="hero-stat">
            <span className="hero-stat-value">Патентная база</span>
            <span className="hero-stat-label">Поиск и анализ</span>
          </div>
          <div className="hero-stat-divider"></div>
          <div className="hero-stat">
            <span className="hero-stat-value">ML-модели</span>
            <span className="hero-stat-label">Random Forest · XGBoost</span>
          </div>
        </div>

        <div className="cta-buttons">
          {isAuthenticated ? (
            <>
              <Link to="/dashboard" className="btn btn-primary">
                Дашборд
              </Link>
              <Link to="/alloys" className="btn btn-secondary">
                Сплавы
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" className="btn btn-primary">
                Войти
              </Link>
              <Link to="/register" className="btn btn-secondary">
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Возможности */}
      <div className="features-section">
        <h2>Возможности системы</h2>

        <div className="features-grid">
          <div className="feature-card">
            <h3>База сплавов</h3>
            <p>
              Хранение и управление данными о металлических сплавах:
              химический состав, механические свойства, типы прокатки
            </p>
            <Link to="/alloys" className="btn btn-outline btn-sm">
              Сплавы
            </Link>
          </div>

          <div className="feature-card">
            <h3>Прогнозирование</h3>
            <p>
              ML-модели Random Forest и XGBoost для прогнозирования
              предела прочности сплавов на основе состава
            </p>
            {(isAdmin || isResearcher) ? (
              <Link to="/predictions/new" className="btn btn-outline btn-sm">
                Создать прогноз
              </Link>
            ) : (
              <Link to="/login" className="btn btn-outline btn-sm">
                Войти для доступа
              </Link>
            )}
          </div>

          <div className="feature-card">
            <h3>Патенты</h3>
            <p>
              База патентной информации о сплавах с возможностью
              поиска, просмотра и привязки к составам
            </p>
            <Link to="/patents" className="btn btn-outline btn-sm">
              Патенты
            </Link>
          </div>

          {isAdmin && (
            <>
              <div className="feature-card">
                <h3>Пользователи</h3>
                <p>
                  Управление учётными записями, ролями и правами доступа
                  пользователей системы
                </p>
                <Link to="/users" className="btn btn-outline btn-sm">
                  Пользователи
                </Link>
              </div>

              <div className="feature-card">
                <h3>Администрирование</h3>
                <p>
                  Управление ML-моделями, ролями и настройками
                  системы
                </p>
                <Link to="/admin" className="btn btn-outline btn-sm">
                  Админ-панель
                </Link>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Как это работает */}
      <div className="how-it-works">
        <h2>Как это работает</h2>

        <div className="steps-grid">
          <div className="step-card">
            <div className="step-number">01</div>
            <h3>Данные о сплавах</h3>
            <p>
              Загрузите данные о химическом составе и механических
              свойствах сплавов из патентов
            </p>
          </div>

          <div className="step-arrow">→</div>

          <div className="step-card">
            <div className="step-number">02</div>
            <h3>ML-модель</h3>
            <p>
              Выберите модель машинного обучения для прогнозирования
              предела прочности
            </p>
          </div>

          <div className="step-arrow">→</div>

          <div className="step-card">
            <div className="step-number">03</div>
            <h3>Прогноз</h3>
            <p>
              Получите прогноз механических свойств для нового
              состава сплава
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;