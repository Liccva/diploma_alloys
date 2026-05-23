import React, { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { patentService, alloyService } from "../services/api";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const fmtDate = (d) => {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
};

const CATEGORY_LABELS = {
  steel: "Сталь",
  aluminum_alloy: "Алюминиевый сплав",
  titanium_alloy: "Титановый сплав",
  copper_alloy: "Медный сплав",
  nickel_based_superalloy: "Суперсплав (никель)",
  cobalt_based_alloy: "Сплав кобальта",
  magnesium_alloy: "Магниевый сплав",
  cast_iron: "Чугун",
  other: "Прочее",
};

const catLabel = (c) => CATEGORY_LABELS[c] || c || "—";

const PatentDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, role, isAuthenticated } = useAuth();

  const isAdmin = role === "admin" || role === "администратор";
  const isResearcher = role === "researcher" || role === "исследователь";

  const [patent, setPatent] = useState(null);
  const [alloys, setAlloys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Проверка, может ли пользователь редактировать патент
  const canEdit = isAuthenticated && (
    isAdmin || (isResearcher && patent?.authors?.some((a) => a.person_id === user?.id))
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Загружаем патент и связанные сплавы
      const [patentRes, alloysRes] = await Promise.all([
        patentService.getById(id),
        alloyService.getByPatent(id),
      ]);

      setPatent(patentRes.data);
      setAlloys(alloysRes.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDelete = async () => {
    if (!canEdit) {
      alert("У вас нет прав для удаления этого патента");
      return;
    }

    if (!window.confirm("Удалить патент? Это действие нельзя отменить.")) return;
    try {
      await patentService.delete(id);
      navigate("/patents");
    } catch (err) {
      alert(err.response?.data?.detail || "Ошибка удаления");
    }
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <h2>Ошибка загрузки</h2>
          <p>{error}</p>
          <div className="form-actions">
            <button className="btn btn-secondary" onClick={() => navigate("/patents")}>← Назад</button>
            <button className="btn btn-primary" onClick={fetchData}>Повторить</button>
          </div>
        </div>
      </div>
    );
  }

  if (!patent) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <h3>Патент не найден</h3>
          <button className="btn btn-secondary" onClick={() => navigate("/patents")}>← К списку</button>
        </div>
      </div>
    );
  }

  const sortedAuthors = [...(patent.authors || [])].sort((a, b) => (a.author_order ?? 0) - (b.author_order ?? 0));

  return (
    <div className="page-container">
      {/* Шапка */}
      <div className="page-header">
        <button className="btn btn-secondary" onClick={() => navigate("/patents")}>
          ← Назад
        </button>
        <div className="page-header-info">
          <div className="patent-number">
            {patent.patent_number}{patent.country ? ` · ${patent.country}` : ""}
          </div>
          <h2>{patent.patent_name}</h2>
        </div>
        {canEdit && (
          <div className="page-header-actions">
            <Link className="btn btn-outline" to={`/patents/edit/${patent.id}`}>Редактировать</Link>
            <button className="btn btn-danger" onClick={handleDelete}>Удалить</button>
          </div>
        )}
      </div>

      {/* Основная информация + авторы */}
      <div className="details-grid">
        <div className="card">
          <div className="card-header">
            <h3>Основная информация</h3>
          </div>
          <div className="card-body">
            <div className="info-row">
              <span className="info-label">Правообладатель:</span>
              <span className="info-value">{patent.assignee || '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">IPC код:</span>
              <span className="info-value">{patent.ipc_code || '—'}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Категория:</span>
              <span className="info-value">{catLabel(patent.category)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Дата подачи:</span>
              <span className="info-value">{fmtDate(patent.filing_date)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Дата выдачи:</span>
              <span className="info-value">{fmtDate(patent.issue_date)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Добавлен:</span>
              <span className="info-value">{fmtDate(patent.created_at)}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h3>Авторы патента</h3>
          </div>
          <div className="card-body">
            {sortedAuthors.length === 0 ? (
              <p className="text-muted">Авторы не указаны</p>
            ) : (
              <ol className="authors-list">
                {sortedAuthors.map((a) => (
                  <li key={a.id}>
                    {a.author_name}
                    {a.person_id && (
                      <span className="badge badge-registered">● зарегистрирован</span>
                    )}
                    {a.person_id === user?.id && (
                      <span className="badge badge-me" style={{ marginLeft: 8, background: "#4caf50", color: "white" }}>
                        Вы
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>

      {/* Описание */}
      {patent.description && (
        <div className="card">
          <div className="card-header">
            <h3>Описание</h3>
          </div>
          <div className="card-body">
            <p className="patent-description">{patent.description}</p>
          </div>
        </div>
      )}

    {/* Сплавы, связанные с патентом */}
<div className="card">
  <div className="card-header">
    <h3>Сплавы патента</h3>
    {alloys.length > 0 && (
      <span className="badge badge-count">{alloys.length}</span>
    )}
  </div>
  <div className="card-body">
    {alloys.length === 0 ? (
      <div className="empty-alloys-inline">
        <p className="text-muted">Сплавы не найдены</p>
        {canEdit && (
          <Link to={`/alloys/new?patent_id=${patent.id}`} className="btn btn-primary btn-sm btn-add-alloy">
            + Добавить сплав
          </Link>
        )}
      </div>
    ) : (
      <>
        <table className="table">
          <thead>
            <tr>
              <th>Значение</th>
              <th>Категория</th>
              <th>Тип прокатки</th>
              <th>Температура</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {alloys.map((alloy) => (
              <tr key={alloy.id}>
                <td>
                  <strong>{alloy.prop_value != null ? `${alloy.prop_value} МПа` : '—'}</strong>
                </td>
                <td>
                  <span className="category-badge">{alloy.category || '—'}</span>
                </td>
                <td>{alloy.rolling_type || '—'}</td>
                <td>{alloy.temperature != null ? `${alloy.temperature}°C` : '—'}</td>
                <td>
                  <Link className="btn btn-secondary btn-sm" to={`/alloys/${alloy.id}`}>
                    Подробнее
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {canEdit && (
          <div className="alloys-actions">
            <Link to={`/alloys/new?patent_id=${patent.id}`} className="btn btn-primary btn-sm btn-add-alloy">
              + Добавить сплав
            </Link>
          </div>
        )}
      </>
    )}
  </div>
</div>

      {/* PDF */}
      <div className="card">
        <div className="card-header">
          <h3>PDF документ</h3>
        </div>
        <div className="card-body">
          {patent.pdf_filename ? (
            <div className="pdf-row">
              <span className="pdf-icon">📄</span>
              <div className="pdf-info">
                <div className="pdf-name">{patent.pdf_filename}</div>
                <div className="pdf-meta">PDF документ патента</div>
              </div>
              <a
                href={`http://localhost:8000/api/patents/${id}/pdf`}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary"
              >
                Открыть
              </a>
              {canEdit && (
                <button
                  className="btn btn-danger"
                  onClick={async () => {
                    if (!window.confirm("Удалить PDF файл?")) return;
                    try {
                      await patentService.deletePdf(id);
                      fetchData();
                    } catch (e) {
                      alert(e.response?.data?.detail || "Ошибка");
                    }
                  }}
                >
                  Удалить
                </button>
              )}
            </div>
          ) : (
            <p className="text-muted">
              PDF не загружен{canEdit ? ". Вы можете добавить его при редактировании." : "."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default PatentDetailsPage;