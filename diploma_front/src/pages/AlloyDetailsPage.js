import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { alloyService, patentService, elementService, personService } from "../services/api";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const AlloyDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin, isResearcher, user } = useAuth();

  const [alloy, setAlloy] = useState(null);
  const [elements, setElements] = useState([]);
  const [patent, setPatent] = useState(null);
  const [allElementsMap, setAllElementsMap] = useState({});
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Проверка, может ли пользователь редактировать сплав
  const canEdit = isAdmin || (user && alloy && alloy.created_by_id === user.id);

  useEffect(() => {
    fetchAlloyDetails();
  }, [id]);

  const fetchAlloyDetails = async () => {
    setLoading(true);
    setError(null);

    try {
      const [alloyRes, elementsRes, allElementsRes] = await Promise.all([
        alloyService.getById(id),
        alloyService.getElements(id),
        elementService.getAll(),
      ]);

      const alloyData = alloyRes.data;
      setAlloy(alloyData);

      // Маппируем все элементы для быстрого доступа по ID
      const elementMap = {};
      (allElementsRes.data || []).forEach((el) => {
        elementMap[el.id] = el;
      });
      setAllElementsMap(elementMap);

      // Обогащаем элементы символами
      const enrichedElements = (elementsRes.data || []).map((el) => ({
        ...el,
        symbol: elementMap[el.element_id]?.symbol || "?",
        name: elementMap[el.element_id]?.name || "Неизвестный элемент",
      }));
      setElements(enrichedElements);

      // Загружаем патент, если есть patent_id
      if (alloyData?.patent_id) {
        try {
          const patentRes = await patentService.getById(alloyData.patent_id);
          setPatent(patentRes.data);
        } catch (e) {
          console.log("Patent not found:", e);
        }
      }

      // 👈 Загружаем информацию о создателе сплава ТОЛЬКО ДЛЯ АДМИНА
      if (isAdmin && alloyData?.created_by_id) {
        try {
          const creatorRes = await personService.getById(alloyData.created_by_id);
          setCreator(creatorRes.data);
        } catch (e) {
          console.log("Creator info not found:", e);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка загрузки сплава");
      console.error("Error fetching alloy details:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Вы уверены, что хотите удалить этот сплав?")) {
      return;
    }

    try {
      await alloyService.delete(id);
      navigate("/alloys");
    } catch (err) {
      alert(err.response?.data?.detail || "Ошибка удаления сплава");
    }
  };

  // Формируем ФИО создателя (только для админа)
  const getCreatorName = () => {
    if (!creator) return "—";
    const parts = [
      creator.last_name || "",
      creator.first_name || "",
      creator.middle_name || "",
    ].filter(Boolean);
    return parts.length > 0 ? parts.join(" ") : `Пользователь #${alloy.created_by_id}`;
  };

  // Формируем роль создателя на русском (только для админа)
  const getCreatorRole = () => {
    if (!creator) return "";
    const roleName = creator.role_name?.toLowerCase() || "";
    if (roleName === "admin" || roleName === "администратор") return "Администратор";
    if (roleName === "researcher" || roleName === "исследователь") return "Исследователь";
    return creator.role_name || "";
  };

  // Формируем заголовок
  const getTitle = () => {
    if (patent) {
      return `Сплав патента ${patent.patent_number}`;
    }
    return `Сплав`;
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate("/alloys")}>
            Вернуться к списку
          </button>
        </div>
      </div>
    );
  }

  if (!alloy) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <h2>Сплав не найден</h2>
          <button className="btn btn-primary" onClick={() => navigate("/alloys")}>
            Вернуться к списку
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>{getTitle()}</h2>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={() => navigate("/alloys")}>
            ← Назад к списку
          </button>

          {/* Кнопка редактирования для админа ИЛИ создателя сплава */}
          {canEdit && (
            <>
              <button
                className="btn btn-primary"
                onClick={() => navigate(`/alloys/edit/${id}`)}
              >
                Редактировать
              </button>
              <button className="btn btn-danger" onClick={handleDelete}>
                Удалить
              </button>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h3>Основная информация</h3>

          <div className="info-grid">
            <div className="info-row">
              <span className="info-label">Номер патента:</span>
              <span className="info-value">
                {patent ? (
                  <Link to={`/patents/${patent.id}`}>
                    {patent.patent_number} — {patent.patent_name}
                  </Link>
                ) : (
                  <span className="text-muted">Не указан</span>
                )}
              </span>
            </div>

            <div className="info-row">
              <span className="info-label">Значение свойства:</span>
              <span className="info-value">
                {alloy.prop_value != null ? `${alloy.prop_value} МПа` : '—'}
              </span>
            </div>

            <div className="info-row">
              <span className="info-label">Категория:</span>
              <span className="info-value">{alloy.category || '—'}</span>
            </div>

            <div className="info-row">
              <span className="info-label">Тип прокатки:</span>
              <span className="info-value">{alloy.rolling_type || '—'}</span>
            </div>

            {alloy.temperature != null && (
              <div className="info-row">
                <span className="info-label">Температура:</span>
                <span className="info-value">{alloy.temperature}°C</span>
              </div>
            )}

            {/* 👈 Вывод создателя ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА */}
            {isAdmin && alloy.created_by_id && (
              <div className="info-row">
                <span className="info-label">Создатель:</span>
                <span className="info-value">
                  {creator ? (
                    <>
                      <Link to={`/users/${alloy.created_by_id}`}>
                        {getCreatorName()}
                      </Link>
                      <span style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>
                        ({getCreatorRole()})
                      </span>
                    </>
                  ) : (
                    <span className="text-muted">Информация недоступна</span>
                  )}
                </span>
              </div>
            )}
          </div>
        </div>

        {elements.length > 0 && (
          <div className="card-body">
            <h3>Состав сплава</h3>

            <table className="table">
              <thead>
                <tr>
                  <th>Элемент</th>
                  <th>Символ</th>
                  <th>Содержание, %</th>
                </tr>
              </thead>
              <tbody>
                {elements.map((el, idx) => (
                  <tr key={idx}>
                    <td>{el.name}</td>
                    <td><strong>{el.symbol}</strong></td>
                    <td>{el.percentage}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {elements.length === 0 && (
          <div className="card-body">
            <p className="text-muted">Состав сплава не указан</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlloyDetailsPage;