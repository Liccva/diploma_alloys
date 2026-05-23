import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";

import {
  predictionService,
  elementService,
  modelService,
  personService,
} from "../services/api";

import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const personLabel = (p) => {
  const last = String(p?.last_name || "").trim();
  const first = String(p?.first_name || "").trim();

  const fio = `${last} ${first}`.trim();
  if (fio) return fio;
  return "—";
};

const PredictionDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAdmin, isResearcher } = useAuth();

  const [prediction, setPrediction] = useState(null);

  const [elements, setElements] = useState([]);
  const [allElements, setAllElements] = useState({});

  const [model, setModel] = useState(null);
  const [person, setPerson] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPredictionDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const fetchPredictionDetails = async () => {
    try {
      setLoading(true);
      setError("");

      // Получаем прогноз и элементы параллельно
      const [predictionRes, elementsRes] = await Promise.all([
        predictionService.getById(id),
        predictionService.getElements(id),
      ]);

      const pred = predictionRes.data;
      setPrediction(pred);

      // Справочник элементов для маппинга (symbol/name/atomic_number)
      const allElementsRes = await elementService.getAll();
      const elementMap = {};
      (allElementsRes.data || []).forEach((el) => {
        elementMap[el.id] = el;
      });
      setAllElements(elementMap);

      // Обогащаем элементы прогноза данными
      const enrichedElements = (elementsRes.data || []).map((el) => {
        // В БД: element_id
        const elementData = elementMap[el.element_id];
        return {
          ...el,
          symbol: elementData?.symbol || "?",
          name: elementData?.name || "Неизвестный элемент",
          atomic_number: elementData?.atomic_number,
        };
      });
      setElements(enrichedElements);

      // NEW: подгружаем модель и пользователя, чтобы показывать не id, а название/ФИО
      const modelId = pred?.ml_model_id;
      const personId = pred?.person_id;

      const [modelRes, personRes] = await Promise.all([
        modelId != null ? modelService.getById(modelId).catch(() => null) : Promise.resolve(null),
        personId != null ? personService.getById(personId).catch(() => null) : Promise.resolve(null),
      ]);

      setModel(modelRes?.data ?? null);
      setPerson(personRes?.data ?? null);
    } catch (err) {
      console.error("Error fetching prediction details:", err);
      setError(err.response?.data?.detail || err.message || "Ошибка загрузки прогноза");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Вы уверены, что хотите удалить этот прогноз?")) return;

    try {
      await predictionService.delete(id);
      alert("Прогноз успешно удалён!");
      navigate("/predictions");
    } catch (err) {
      alert(err.response?.data?.detail || "Ошибка удаления прогноза");
    }
  };

  const totalPercentage = useMemo(() => {
    return (elements || []).reduce((sum, el) => sum + (Number(el?.percentage) || 0), 0);
  }, [elements]);

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="prediction-details-page">
        <div className="error-container">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate("/predictions")}>
            Вернуться к прогнозам
          </button>
        </div>
      </div>
    );
  }

  if (!prediction) {
    return (
      <div className="prediction-details-page">
        <div className="not-found">
          <h2>Прогноз не найден</h2>
          <button className="btn btn-primary" onClick={() => navigate("/predictions")}>
            Вернуться к прогнозам
          </button>
        </div>
      </div>
    );
  }

  const modelTitle =
    model?.name ||
    (prediction?.ml_model_id != null ? `Модель #${prediction.ml_model_id}` : "—");

  const userTitle =
    personLabel(person) ||
    (prediction?.person_id != null ? `Пользователь #${prediction.person_id}` : "—");

  return (
    <div className="prediction-details-page">
      <div className="details-header">
        <h1>Прогноз #{prediction.id}</h1>

        <div className="details-actions">
          <button className="btn btn-secondary" onClick={() => navigate("/predictions")}>
            Назад
          </button>

          {(isAdmin || isResearcher) && (
            <Link to={`/predictions/edit/${id}`} className="btn btn-primary">
              Редактировать
            </Link>
          )}

          {(isAdmin || isResearcher) && (
            <button className="btn btn-danger" onClick={handleDelete}>
              Удалить
            </button>
          )}
        </div>
      </div>

      <div className="details-card">
        <div className="details-section">
          <h2>Информация</h2>

          <div className="info-grid">


            <div className="info-item">
              <span className="label">Предел прочности</span>
              <span className="value highlight">{prediction.prop_value} МПа</span>
            </div>

            <div className="info-item">
              <span className="label">Категория</span>
              <span className="value category-badge">{prediction.category}</span>
            </div>

            <div className="info-item">
              <span className="label">Тип прокатки</span>
              <span className="value">{prediction.rolling_type}</span>
            </div>

            <div className="info-item">
              <span className="label">ML модель</span>
              <span className="value">{modelTitle}</span>

            </div>

            <div className="info-item">
              <span className="label">Пользователь</span>
              <span className="value">{userTitle}</span>
            </div>
          </div>
        </div>

        {elements.length > 0 ? (
          <div className="details-section">
            <h2>Состав</h2>

            <div className="composition-summary">
              <p>
                Всего элементов: <strong>{elements.length}</strong>
              </p>
              <p>
                Сумма процентов: <strong>{totalPercentage.toFixed(2)}%</strong>
              </p>
            </div>

            <table className="details-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Элемент</th>
                  <th>Символ</th>
                  <th>Атомный №</th>
                  <th>Процент</th>
                </tr>
              </thead>

              <tbody>
                {elements.map((el, idx) => (
                  <tr key={`${el.element_id}-${idx}`}>
                    <td>{idx + 1}</td>
                    <td>
                      <Link to={`/elements/${el.element_id}`}>{el.name}</Link>
                    </td>
                    <td>
                      <strong className="element-symbol">{el.symbol}</strong>
                    </td>
                    <td>{el.atomic_number || "—"}</td>
                    <td>
                      <div className="percentage-bar-container">
                        <div className="percentage-bar" style={{ width: `${el.percentage}%` }} />
                        <span className="percentage-text">{el.percentage}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>

              <tfoot>
                <tr>
                  <td colSpan={4} className="text-end">
                    <strong>Всего:</strong>
                  </td>
                  <td>
                    <strong>{totalPercentage.toFixed(2)}%</strong>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <div className="details-section">
            <h2>Состав</h2>
            <div className="empty-state">
              <p className="text-muted">Элементы не добавлены к этому прогнозу.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PredictionDetailsPage;
