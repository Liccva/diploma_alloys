import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { alloyService, patentService } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import ElementSelector from "../elements/ElementSelector";
import LoadingSpinner from "../common/LoadingSpinner";

const EPS = 0.001;
const round3 = (n) => Math.round((Number(n) || 0) * 1000) / 1000;

const AlloyForm = ({ isEdit = false }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAdmin, isResearcher, user } = useAuth();

  // Получаем patent_id из URL параметров
  const preselectedPatentId = searchParams.get("patent_id") || "";

  const [formData, setFormData] = useState({
    prop_value: "",
    temperature: "",
    category: "",
    rolling_type: "",
    patent_id: preselectedPatentId,
    elements: [],
  });

  const [originalElements, setOriginalElements] = useState([]);
  const [patents, setPatents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const totalPercentage = useMemo(() => {
    const sum = (formData.elements || []).reduce(
      (acc, el) => acc + (parseFloat(el?.percentage || 0) || 0), 0
    );
    return round3(sum);
  }, [formData.elements]);

  const canUseForm = useMemo(() => isAdmin || isResearcher, [isAdmin, isResearcher]);

  useEffect(() => {
    if (!canUseForm) {
      alert("У вас нет прав для создания/редактирования сплавов");
      navigate("/alloys");
      return;
    }
    fetchPatents();
    if (isEdit && id) fetchAlloyData();
  }, [canUseForm, isEdit, id]);

  const fetchPatents = async () => {
    try {
        // Используем специализированный эндпоинт для формы сплава
        const res = await patentService.getForAlloy();
        setPatents(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
        console.error("Error fetching patents:", err);
        // Fallback: если новый эндпоинт не работает, пробуем старый
        try {
            const fallbackRes = await patentService.getAll(0, 500);
            setPatents(Array.isArray(fallbackRes.data) ? fallbackRes.data : []);
        } catch (fallbackErr) {
            console.error("Fallback also failed:", fallbackErr);
            setPatents([]);
        }
    }
};

  const fetchAlloyData = async () => {
    setLoading(true);
    try {
      const [alloyRes, elementsRes] = await Promise.all([
        alloyService.getById(id),
        alloyService.getElements(id),
      ]);

      const alloyData = alloyRes.data || {};
      setFormData({
        prop_value: alloyData.prop_value ?? "",
        temperature: alloyData.temperature ?? "",   // ← подгружаем
        category: alloyData.category ?? "",
        rolling_type: alloyData.rolling_type ?? "",
        patent_id: alloyData.patent_id ?? "",
        elements: (elementsRes.data || []).map((el) => ({
          element_id: el.element_id,
          percentage: el.percentage ?? "",
        })),
      });

      setOriginalElements(elementsRes.data || []);
    } catch (err) {
      console.error("Error fetching alloy data:", err);
      alert("Не удалось загрузить данные сплава");
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const handleElementsChange = (selectedElements) => {
    setFormData((prev) => ({ ...prev, elements: selectedElements || [] }));
  };

  const validateForm = () => {
    const newErrors = {};
    const prop = Number(String(formData.prop_value).replace(",", "."));
    if (!Number.isFinite(prop) || prop <= 0) {
      newErrors.prop_value = "Значение свойства должно быть положительным числом";
    }
    // Температура не обязательна, но если введена – должна быть числом
    if (formData.temperature !== "" && formData.temperature !== null) {
      const temp = Number(String(formData.temperature).replace(",", "."));
      if (!Number.isFinite(temp)) {
        newErrors.temperature = "Температура должна быть числом";
      }
    }
    if (!String(formData.category || "").trim()) {
      newErrors.category = "Категория обязательна";
    }
    if (!formData.patent_id) {
      newErrors.patent_id = "Необходимо выбрать патент";
    }
    if (Math.abs(totalPercentage - 100) > EPS) {
      newErrors.elements = `Сумма процентов должна быть 100.000% (сейчас: ${totalPercentage.toFixed(3)}%)`;
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const normalizeElements = (elements) => {
    return (elements || [])
      .filter((el) => el?.element_id)
      .map((el) => ({
        element_id: parseInt(el.element_id, 10),
        percentage: round3(Number(String(el.percentage).replace(",", "."))),
      }))
      .filter((el) => Number.isFinite(el.element_id) && Number.isFinite(el.percentage));
  };

  const buildAlloyData = () => {
    const data = {
      prop_value: round3(Number(String(formData.prop_value).replace(",", "."))),
      category: String(formData.category || "").trim(),
      rolling_type: String(formData.rolling_type || "").trim(),
      patent_id: parseInt(formData.patent_id, 10),
    };
    // Температура – передаём только если введена
    if (formData.temperature !== "" && formData.temperature !== null) {
      data.temperature = round3(Number(String(formData.temperature).replace(",", ".")));
    }
    return data;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    try {
      const alloyData = buildAlloyData();

      if (isEdit) {
        // Обновляем основные данные сплава
        await alloyService.update(id, alloyData);

        // Обновляем элементы: удаляем старые, добавляем новые
        const newElements = normalizeElements(formData.elements);
        const oldElements = normalizeElements(originalElements);

        for (const el of oldElements) {
          await alloyService.removeElement(id, el.element_id);
        }
        for (const el of newElements) {
          await alloyService.addElement(id, el.element_id, el.percentage);
        }
      } else {
        // Создаём сплав, затем добавляем элементы
        const createRes = await alloyService.create(alloyData);
        const newId = createRes.data?.id;

        if (!newId) {
          throw new Error("Не удалось получить ID созданного сплава");
        }

        const elements = normalizeElements(formData.elements);
        for (const el of elements) {
          await alloyService.addElement(newId, el.element_id, el.percentage);
        }
      }

      navigate("/alloys");
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Ошибка сохранения";
      alert(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="alloy-form-container">
      <h2>{isEdit ? "Редактирование сплава" : "Создание сплава"}</h2>

      <form onSubmit={handleSubmit} className="form-card">
        {/* Предел прочности */}
        <div className="form-group">
          <label htmlFor="prop_value">Предел прочности (МПа)</label>
          <input
            type="number"
            id="prop_value"
            name="prop_value"
            value={formData.prop_value}
            onChange={handleInputChange}
            className={`form-control ${errors.prop_value ? "error" : ""}`}
            placeholder="например: 123.456"
            disabled={submitting}
            step="0.001"
          />
          {errors.prop_value && <span className="error-message">{errors.prop_value}</span>}
        </div>

        {/* Температура */}
        <div className="form-group">
          <label htmlFor="temperature">Температура (°C)</label>
          <input
            type="number"
            id="temperature"
            name="temperature"
            value={formData.temperature}
            onChange={handleInputChange}
            className={`form-control ${errors.temperature ? "error" : ""}`}
            placeholder="например: 950"
            disabled={submitting}
            step="0.1"
          />
          {errors.temperature && <span className="error-message">{errors.temperature}</span>}
        </div>

        {/* Категория */}
        <div className="form-group">
          <label htmlFor="category">Категория</label>
          <input
            type="text"
            id="category"
            name="category"
            value={formData.category}
            onChange={handleInputChange}
            className={`form-control ${errors.category ? "error" : ""}`}
            placeholder="Введите категорию"
            disabled={submitting}
          />
          {errors.category && <span className="error-message">{errors.category}</span>}
        </div>

        {/* Тип прокатки */}
        <div className="form-group">
          <label htmlFor="rolling_type">Тип прокатки</label>
          <input
            type="text"
            id="rolling_type"
            name="rolling_type"
            value={formData.rolling_type}
            onChange={handleInputChange}
            className="form-control"
            disabled={submitting}
            placeholder="Введите тип прокатки"
          />
        </div>

        {/* Патент */}
        <div className="form-group">
          <label htmlFor="patent_id">Патент</label>
          <select
            id="patent_id"
            name="patent_id"
            value={formData.patent_id}
            onChange={handleInputChange}
            className={`form-control ${errors.patent_id ? "error" : ""}`}
            disabled={submitting}
          >
            <option value="">Выберите патент</option>
            {patents.map((p) => (
              <option key={p.id} value={p.id}>
                {p.patent_name || `Патент #${p.id}`} ({p.patent_number})
              </option>
            ))}
          </select>
          {errors.patent_id && <span className="error-message">{errors.patent_id}</span>}
        </div>

        {/* Элементы */}
        <div className="form-section">
          <ElementSelector
            selectedElements={formData.elements}
            onChange={handleElementsChange}
            maxTotalPercentage={100}
            requireExactTotal={true}
            disabled={submitting}
          />
          <div className="form-hint">
            Сумма процентов: {totalPercentage.toFixed(3)}% / 100.000%
          </div>
          {errors.elements && <span className="error-message">{errors.elements}</span>}
        </div>

        {/* Кнопки */}
        <div className="form-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate("/alloys")}
            disabled={submitting}
          >
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "Сохранение..." : isEdit ? "Обновить" : "Создать"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default AlloyForm;