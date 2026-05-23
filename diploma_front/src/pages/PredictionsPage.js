import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { predictionService, personService, modelService } from "../services/api";
import LoadingSpinner from "../components/common/LoadingSpinner";
import { useAuth } from "../context/AuthContext";

const PredictionsPage = () => {
  const [predictions, setPredictions] = useState([]);
  const [filteredPredictions, setFilteredPredictions] = useState([]);
  const [users, setUsers] = useState({});
  const [models, setModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterUser, setFilterUser] = useState("all");

  const { isAdmin, isResearcher, user } = useAuth();
  const hasAccess = isAdmin || isResearcher;

  const fetchPredictions = useCallback(async () => {
    if (!user || !hasAccess) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const predictionsRes = await predictionService.getMyPredictions();
      const predictionsData = predictionsRes.data || [];

      const modelsRes = await modelService.getAll();
      const modelsMap = {};
      (modelsRes.data || []).forEach(m => {
        modelsMap[m.id] = m.name;
      });
      setModels(modelsMap);

      if (isAdmin && predictionsData.length > 0) {
        try {
          const usersRes = await personService.getAll();
          const usersMap = {};
          (usersRes.data || []).forEach(u => {
            usersMap[u.id] = u;
          });
          setUsers(usersMap);
        } catch (e) {
          console.log('Cannot load users:', e.message);
        }
      }

      setPredictions(predictionsData);
      setFilteredPredictions(predictionsData);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Ошибка загрузки прогнозов");
    } finally {
      setLoading(false);
    }
  }, [user, hasAccess, isAdmin]);

  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  useEffect(() => {
    let filtered = [...predictions];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(p =>
        (p.category || '').toLowerCase().includes(term) ||
        (p.rolling_type || '').toLowerCase().includes(term) ||
        (p.prop_value !== null && p.prop_value !== undefined && p.prop_value.toString().includes(term)) ||
        p.id.toString().includes(term) ||
        (p.ml_model_id && p.ml_model_id.toString().includes(term))
      );
    }

    if (filterCategory !== "all") {
      filtered = filtered.filter(p => p.category === filterCategory);
    }

    if (filterUser !== "all" && isAdmin) {
      filtered = filtered.filter(p => p.person_id === parseInt(filterUser));
    }

    setFilteredPredictions(filtered);
  }, [searchTerm, filterCategory, filterUser, predictions, isAdmin]);

  const canEdit = (prediction) => isAdmin || (isResearcher && prediction.person_id === user?.id);
  const canDelete = (prediction) => isAdmin || (isResearcher && prediction.person_id === user?.id);
  const canView = (prediction) => isAdmin || (isResearcher && prediction.person_id === user?.id);

  const handleDelete = async (id) => {
    if (!window.confirm("Удалить прогноз?")) return;
    try {
      await predictionService.delete(id);
      setPredictions(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      alert(e.response?.data?.detail || e.message || "Ошибка удаления");
    }
  };

  const getCategories = () => {
    const cats = new Set(predictions.map(p => p.category).filter(Boolean));
    return Array.from(cats).sort();
  };

  const getUserFullName = (userId) => {
    const u = users[userId];
    if (!u) return `Пользователь #${userId}`;
    const parts = [u.last_name, u.first_name, u.middle_name].filter(Boolean);
    if (parts.length > 0) return parts.join(' ');
    return u.login || `Пользователь #${userId}`;
  };

  const getUserOptions = () => {
    const ids = new Set(predictions.map(p => p.person_id).filter(id => id));
    return Array.from(ids)
      .map(id => ({
        id,
        name: getUserFullName(id)
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  };

  const clearFilters = () => {
    setSearchTerm("");
    setFilterCategory("all");
    setFilterUser("all");
  };

  const getModelName = (modelId) => {
    if (!modelId) return "Не выбрана";
    return models[modelId] || `Модель #${modelId}`;
  };

  if (loading) return <LoadingSpinner />;

  if (!hasAccess) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h2>Прогнозы</h2>
        </div>
        <div className="empty-state">
          <h3>Доступ запрещен</h3>
          <p>У вас нет прав для просмотра прогнозов.</p>
          {!user ? (
            <Link to="/login" className="btn btn-primary">
              Войти в систему
            </Link>
          ) : (
            <p className="text-muted">Обратитесь к администратору для получения прав исследователя.</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Прогнозы</h2>
        <Link to="/predictions/new" className="btn btn-primary">
          Создать прогноз
        </Link>
      </div>

      {predictions.length === 0 ? (
        <div className="empty-state">
          <h3>Прогнозов нет</h3>
          <Link to="/predictions/new" className="btn btn-primary">
            Создать первый прогноз
          </Link>
        </div>
      ) : (
        <>
          {/* Исправленная структура фильтров — как в PatentsPage */}
          <div className="predictions-filters">
            <input
              type="text"
              placeholder="Поиск по прогнозам..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />

            <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)}>
              <option value="all">Все категории</option>
              {getCategories().map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>

            {isAdmin && getUserOptions().length > 0 && (
              <select value={filterUser} onChange={e => setFilterUser(e.target.value)}>
                <option value="all">Все пользователи</option>
                {getUserOptions().map(u => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            )}

            {(searchTerm || filterCategory !== "all" || filterUser !== "all") && (
              <button className="btn btn-outline btn-sm" onClick={clearFilters}>
                Сбросить
              </button>
            )}
          </div>

          {error && <div className="form-error">{error}</div>}

          <div className="table-info">
            Показано: <strong>{filteredPredictions.length}</strong> из {predictions.length}
          </div>

          {filteredPredictions.length === 0 ? (
            <div className="empty-state">
              <p>Ничего не найдено</p>
              <button className="btn btn-primary" onClick={clearFilters}>
                Сбросить фильтры
              </button>
            </div>
          ) : (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Категория</th>
                    <th>Значение</th>
                    <th>Тип прокатки</th>
                    <th>Модель</th>
                    {isAdmin && <th>Создатель</th>}
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPredictions.map(p => {
                    const creatorFullName = getUserFullName(p.person_id);
                    return (
                      <tr key={p.id}>
                        <td>{p.category || '—'}</td>
                        <td>
                          <strong>{p.prop_value ?? '—'}</strong>
                          {p.prop_value != null && ' МПа'}
                        </td>
                        <td>{p.rolling_type || '—'}</td>
                        <td>{getModelName(p.ml_model_id)}</td>
                        {isAdmin && (
                          <td>
                            <Link to={`/users/${p.person_id}`}>
                              {creatorFullName}
                            </Link>
                          </td>
                        )}
                        <td>
                          <div className="actions-group">
                            {canView(p) && (
                              <Link to={`/predictions/${p.id}`} className="btn btn-secondary btn-sm">
                                Просмотр
                              </Link>
                            )}
                            {canEdit(p) && (
                              <Link to={`/predictions/edit/${p.id}`} className="btn btn-outline btn-sm">
                                Изменить
                              </Link>
                            )}
                            {canDelete(p) && (
                              <button className="btn btn-danger btn-sm" onClick={() => handleDelete(p.id)}>
                                Удалить
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default PredictionsPage;