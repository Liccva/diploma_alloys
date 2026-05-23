import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { alloyService, predictionService, patentService } from "../services/api";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const Dashboard = () => {
  const [stats, setStats] = useState({
    alloys: 0,
    predictions: 0,
    patents: 0,
    loading: true,
  });

  const [recentAlloys, setRecentAlloys] = useState([]);
  const [recentPredictions, setRecentPredictions] = useState([]);
  const [error, setError] = useState("");

  const { isAdmin, isResearcher, user } = useAuth();
  const myUserId = useMemo(() => user?.id, [user?.id]);

  const filterPredictionsByRole = useCallback((list) => {
    const arr = Array.isArray(list) ? list : [];

    if (isResearcher && !isAdmin) {
      return arr.filter((p) => p?.person_id === myUserId);
    }

    return arr;
  }, [isAdmin, isResearcher, myUserId]);

  const fetchData = useCallback(async () => {
    setError("");

    try {
      const [alloysRes, patentsRes, predictionsRes] = await Promise.all([
        alloyService.getAll(),
        patentService.getAll(),
        predictionService.getMyPredictions(),
      ]);

      console.log('ALLOYS:', alloysRes.data?.length);
      console.log('PATENTS:', patentsRes.data?.length);
      console.log('PREDICTIONS:', predictionsRes.data?.length);

      const alloysData = alloysRes.data || [];
      const patentsData = patentsRes.data || [];
      const predictionsData = predictionsRes.data || [];

      const predictionsFiltered = filterPredictionsByRole(predictionsData);

      // Статистика
      setStats({
        alloys: alloysData.length,
        predictions: predictionsFiltered.length,
        patents: patentsData.length,
        loading: false,
      });

      // Последние сплавы
      const sortedAlloys = [...alloysData]
        .sort((a, b) => b.id - a.id)
        .slice(0, 5);
      setRecentAlloys(sortedAlloys);

      // Последние прогнозы
      const sortedPredictions = [...predictionsFiltered]
        .sort((a, b) => b.id - a.id)
        .slice(0, 5);
      setRecentPredictions(sortedPredictions);

    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      setError("Ошибка загрузки данных");
      setStats(prev => ({ ...prev, loading: false }));
    }
  }, [filterPredictionsByRole]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const refreshData = () => {
    setStats(prev => ({ ...prev, loading: true }));
    fetchData();
  };

  if (stats.loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Дашборд</h1>
        <button className="btn btn-secondary btn-sm" onClick={refreshData}>
          Обновить
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="stats-cards">
        <div className="stat-card">
          <div className="stat-number">{stats.alloys}</div>
          <h3>Сплавы</h3>
          <Link className="stat-link" to="/alloys">
            Перейти к сплавам →
          </Link>
        </div>

        <div className="stat-card">
          <div className="stat-number">{stats.predictions}</div>
          <h3>Прогнозы</h3>
          <Link className="stat-link" to="/predictions">
            Перейти к прогнозам →
          </Link>
        </div>

        <div className="stat-card">
          <div className="stat-number">{stats.patents}</div>
          <h3>Патенты</h3>
          <Link className="stat-link" to="/patents">
            Перейти к патентам →
          </Link>
        </div>
      </div>

      <div className="dashboard-sections">
        {/* Быстрые действия */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Быстрые действия</h2>
          </div>

          <div className="quick-actions">
            <Link to="/alloys/new" className="btn btn-secondary">
              Добавить сплав
            </Link>

            {(isAdmin || isResearcher) && (
              <Link to="/predictions/new" className="btn btn-primary">
                Создать прогноз
              </Link>
            )}

            {isAdmin && (
              <Link to="/users" className="btn btn-outline">
                Управление пользователями
              </Link>
            )}
          </div>
        </div>

        {/* Последние сплавы */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Последние сплавы</h2>
            <Link className="view-all" to="/alloys">
              Все →
            </Link>
          </div>

          <div className="recent-items">
            {recentAlloys.length === 0 ? (
              <div className="info-message">
                <p>Нет данных</p>
              </div>
            ) : (
              recentAlloys.map((a) => (
                <div key={a.id} className="recent-item">
                  <Link className="item-title" to={`/alloys/${a.id}`}>
                    Сплав #{a.id}
                  </Link>
                  <div className="item-details">
                    <span className="category-badge">{a.category || '—'}</span>
                    <span className="item-value">
                      {a.prop_value != null ? `${a.prop_value} МПа` : '—'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Последние прогнозы */}
        <div className="dashboard-section">
          <div className="section-header">
            <h2>Последние прогнозы</h2>
            <Link className="view-all" to="/predictions">
              Все →
            </Link>
          </div>

          <div className="recent-items">
            {recentPredictions.length === 0 ? (
              <div className="info-message">
                <p>
                  {isResearcher && !isAdmin
                    ? "У вас пока нет прогнозов"
                    : "Нет данных"}
                </p>
              </div>
            ) : (
              recentPredictions.map((p) => (
                <div key={p.id} className="recent-item">
                  <Link className="item-title" to={`/predictions/${p.id}`}>
                    Прогноз #{p.id}
                  </Link>
                  <div className="item-details">
                    <span className="category-badge">{p.category || '—'}</span>
                    <span className="item-value">
                      {p.prop_value != null ? `${p.prop_value} МПа` : '—'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Администрирование */}
        {isAdmin && (
          <div className="dashboard-section">
            <div className="section-header">
              <h2>Администрирование</h2>
            </div>
            <div className="action-buttons">
              <Link to="/users" className="btn btn-outline">
                Пользователи
              </Link>
              <Link to="/admin" className="btn btn-outline">
                Админ-панель
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;