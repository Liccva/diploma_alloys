import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api, predictionService, elementService } from '../../services/api';
import useAuth from '../../context/AuthContext';
import LoadingSpinner from '../common/LoadingSpinner';
import ElementSelector from '../elements/ElementSelector';

const EPS = 0.001;
const round3 = (n) => Math.round(Number(n) * 1000) / 1000;

const uniqSorted = (arr) =>
  Array.from(new Set(arr))
    .map(x => String(x).trim())
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b));

const mapCategoryForDisplay = (categoryFromBackend) => {
  const mapping = {
    'nickel_alloy': 'Никелевый сплав',
    'titanium_alloy': 'Титановый сплав',
    'aluminum_alloy': 'Алюминиевый сплав',
    'steel_alloy': 'Сталь',
    'copper_alloy': 'Медный сплав',
    'other': 'Другой'
  };
  return mapping[categoryFromBackend] || categoryFromBackend;
};

const mapCategoryForBackend = (categoryFromFront) => {
  const mapping = {
    'Никелевый сплав': 'nickel_alloy',
    'Титановый сплав': 'titanium_alloy',
    'Алюминиевый сплав': 'aluminum_alloy',
    'Сталь': 'steel_alloy',
    'Медный сплав': 'copper_alloy',
    'Другой': 'other'
  };
  return mapping[categoryFromFront] || categoryFromFront;
};

const getModelIdByCategory = (categoryDisplayName) => {
  const mapping = {
    'Никелевый сплав': 1, 'Титановый сплав': 2, 'Алюминиевый сплав': 3,
    'Сталь': 4, 'Медный сплав': 5, 'Другой': 6
  };
  return mapping[categoryDisplayName] || 1;
};

const getCategoryByModelId = (modelId) => {
  const mapping = { 1: 'Никелевый сплав', 2: 'Титановый сплав', 3: 'Алюминиевый сплав', 4: 'Сталь', 5: 'Медный сплав', 6: 'Другой' };
  return mapping[modelId] || 'Другой';
};

const PredictionForm = ({ isEdit = false }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [formData, setFormData] = useState({ category: '', rolling_type: '', person_id: '', elements: [] });
  const [size, setSize] = useState('');
  const [originalElements, setOriginalElements] = useState([]);
  const [allElementsMap, setAllElementsMap] = useState({});
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [rollingOptions, setRollingOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState('');
  const [predictedValue, setPredictedValue] = useState(null);
  const [autoCategory, setAutoCategory] = useState(null);
  const [autoCategoryConfidence, setAutoCategoryConfidence] = useState(null);
  const [showCategoryWarning, setShowCategoryWarning] = useState(false);
  const [userSelectedCategory, setUserSelectedCategory] = useState(false);

  // Ref для блокировки повторного авто-вызова
  const autoSetBlockRef = useRef(false);

  useEffect(() => {
    if (user?.id) setFormData(prev => ({ ...prev, person_id: String(user.id) }));
  }, [user]);

  const totalPercentage = useMemo(() => {
    const sum = formData.elements.reduce((acc, el) => acc + parseFloat(el?.percentage || 0), 0);
    return round3(sum);
  }, [formData.elements]);

  const normalizeElements = useCallback((elements) =>
    elements.filter(el => el.element_id != null).map(el => ({
      element_id: parseInt(el.element_id, 10),
      percentage: round3(Number(String(el.percentage).replace(',', '.'))),
    })).filter(el => Number.isFinite(el.element_id) && Number.isFinite(el.percentage) && el.percentage >= 0 && el.percentage <= 99.999),
  []);

  const loadAllElements = useCallback(async () => {
    try {
      const response = await elementService.getAll();
      const map = {};
      (response.data || []).forEach(el => { map[el.id] = el; });
      setAllElementsMap(map);
    } catch (err) { console.error('Error loading elements', err); }
  }, []);

  const loadRollingTypes = useCallback(async () => {
    try {
      const res = await fetch('/all_rolling_types.json', { cache: 'no-store' });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setRollingOptions(uniqSorted(data.filter(r => r && String(r).trim())));
    } catch { setRollingOptions(['hot', 'cold', 'warm', 'cast', 'forged', 'unknown']); }
  }, []);

  const loadCategories = useCallback(async () => {
    try {
      const res = await fetch('/data.json', { cache: 'no-store' });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const raw = uniqSorted(data.map(x => x?.category).filter(Boolean));
      const mapping = { 'steel_alloy': 'Сталь', 'nickel_alloy': 'Никелевый сплав', 'aluminum_alloy': 'Алюминиевый сплав', 'titanium_alloy': 'Титановый сплав', 'copper_alloy': 'Медный сплав', 'other': 'Другой' };
      setCategoryOptions(raw.map(c => mapping[c] || c));
    } catch { setCategoryOptions(['Сталь', 'Никелевый сплав', 'Алюминиевый сплав', 'Титановый сплав', 'Медный сплав', 'Другой']); }
  }, []);

  const buildMlPayload = useCallback(() => {
    const elements = normalizeElements(formData.elements);
    const categoryForBackend = formData.category ? mapCategoryForBackend(formData.category) : "";
    return { ml_model_id: 2, category: categoryForBackend, rolling_type: String(formData.rolling_type).trim(), size: size ? parseFloat(size.replace(',', '.')) : null, elements };
  }, [formData, normalizeElements, size]);
const requestPrediction = useCallback(async (isAuto = false) => {
  setPredictError('');
  const elements = normalizeElements(formData.elements);
  const canPredict = String(formData.rolling_type).trim() && elements.length > 0 && Math.abs(totalPercentage - 100) < EPS;

  if (!canPredict) {
    setPredictedValue(null);
    if (!isAuto) { setAutoCategory(null); setAutoCategoryConfidence(null); setShowCategoryWarning(false); }
    return null;
  }

  try {
    setPredicting(true);
    const payload = buildMlPayload();
    const res = await api.post('/ml/predict/v2', payload);
    const val = res?.data?.prop_value;
    const detectedCategory = res?.data?.category;
    const confidence = res?.data?.confidence;

    if (val == null || Number.isNaN(Number(val))) throw new Error('Invalid response');

    const roundedValue = round3(Number(val));
    setPredictedValue(roundedValue);

    if (detectedCategory) {
      const displayCategory = mapCategoryForDisplay(detectedCategory);
      setAutoCategory(displayCategory);
      setAutoCategoryConfidence(confidence);

      if (isAuto && autoSetBlockRef.current) {
        autoSetBlockRef.current = false;
        return roundedValue;
      }

      if (isAuto && !userSelectedCategory && !formData.category) {
        autoSetBlockRef.current = true;
        setFormData(prev => ({ ...prev, category: displayCategory }));
        setShowCategoryWarning(false);
      } else if (formData.category && displayCategory !== formData.category) {
        setShowCategoryWarning(true);
      } else if (formData.category && displayCategory === formData.category) {
        setShowCategoryWarning(false);
      }
    }

    return roundedValue;
  } catch (e) {
    console.error(e);
    setPredictedValue(null);

    // Обработка ошибок ML-модели
    const detail = (e.response?.data?.detail || e.message || "").toLowerCase();

    if (detail.includes("модель не загружена") ||
        detail.includes("model not loaded") ||
        detail.includes("joblib") ||
        detail.includes("file not found") ||
        detail.includes("no such file")) {
      setPredictError("ML-модель временно недоступна. Обратитесь к администратору.");
    } else if (e.message === 'Network Error' || !e.response) {
      setPredictError("Ошибка соединения с сервером. Проверьте сеть.");
    } else {
      setPredictError(e.response?.data?.detail || e.message || "Ошибка предсказания");
    }

    return null;
  } finally {
    setPredicting(false);
  }
}, [buildMlPayload, formData.category, userSelectedCategory, normalizeElements, totalPercentage]);

  // Авто-предсказание
  useEffect(() => {
    const t = setTimeout(() => {
      if (normalizeElements(formData.elements).length > 0 && Math.abs(totalPercentage - 100) < EPS && String(formData.rolling_type).trim()) {
        requestPrediction(true);
      }
    }, 600);
    return () => clearTimeout(t);
  }, [formData.elements, totalPercentage, formData.rolling_type, size]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    if (name === 'category' && value) {
      setUserSelectedCategory(true);
      if (autoCategory && value !== autoCategory) {
        setShowCategoryWarning(true);
      } else {
        setShowCategoryWarning(false);
      }
    }
  };

  const handleElementsChange = (selectedElements) => {
    setFormData(prev => ({ ...prev, elements: selectedElements }));
    if (errors.elements) setErrors(prev => ({ ...prev, elements: '' }));
  };

  const validateForm = useCallback(() => {
    const newErrors = {};
    if (!String(formData.category).trim()) newErrors.category = 'Выберите категорию';
    if (!String(formData.rolling_type).trim()) newErrors.rolling_type = 'Выберите тип прокатки';
    if (!formData.person_id) newErrors.person_id = 'Не удалось определить пользователя';
    if (normalizeElements(formData.elements).length === 0) {
      newErrors.elements = 'Добавьте хотя бы один элемент';
    } else if (Math.abs(totalPercentage - 100) > EPS) {
      newErrors.elements = `Сумма процентов должна быть 100.000 (сейчас: ${totalPercentage.toFixed(3)})`;
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, normalizeElements, totalPercentage]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError(''); setPredictError('');
    if (!validateForm()) return;

    let finalPredictedValue = predictedValue;
    if (finalPredictedValue == null) finalPredictedValue = await requestPrediction(false);
    if (finalPredictedValue == null) { setApiError('Невозможно получить предсказание'); return; }

    setSubmitting(true);
    try {
      const modelId = getModelIdByCategory(formData.category);
      const predictionData = {
        prop_value: round3(Number(finalPredictedValue)),
        category: formData.category,
        rolling_type: String(formData.rolling_type).trim(),
        ml_model_id: modelId,
        person_id: parseInt(formData.person_id, 10),
      };
      const elements = normalizeElements(formData.elements);

      if (isEdit && id) {
        await predictionService.update(id, predictionData);
        const old = normalizeElements(originalElements);
        for (const el of old) await predictionService.removeElement(id, el.element_id).catch(() => {});
        for (const el of elements) await predictionService.addElement(id, el.element_id, el.percentage);
        alert('Прогноз обновлен');
      } else {
        const createResponse = await predictionService.create(predictionData);
        let predictionId = createResponse.data?.id;
        if (!predictionId) {
          await new Promise(r => setTimeout(r, 500));
          const userPreds = await predictionService.getByPerson(predictionData.person_id);
          predictionId = (userPreds.data || []).reduce((prev, cur) => prev.id > cur.id ? prev : cur).id;
        }
        for (const el of elements) await predictionService.addElement(predictionId, el.element_id, el.percentage);
        alert('Прогноз сохранен');
      }
      navigate('/predictions');
    } catch (err) {
      setApiError(err.response?.data?.detail || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    loadAllElements(); loadRollingTypes(); loadCategories();
    if (isEdit && id) {
      const fetchData = async () => {
        setLoading(true);
        try {
          const [predRes, elemRes] = await Promise.all([predictionService.getById(id), predictionService.getElements(id)]);
          const p = predRes.data;
          const elements = (elemRes.data || []).map(el => ({ element_id: el.element_id, percentage: el.percentage }));
          let cat = getCategoryByModelId(p?.ml_model_id);
          if (p?.category && /[а-яА-Я]/.test(p.category)) cat = p.category;
          setFormData(prev => ({ ...prev, category: cat, rolling_type: p?.rolling_type || '', person_id: p?.person_id || (user?.id ? String(user.id) : prev.person_id), elements }));
          setOriginalElements(elements);
          setPredictedValue(p?.prop_value ?? null);
          setUserSelectedCategory(true);
        } catch (err) { setApiError(err.response?.data?.detail || err.message); }
        finally { setLoading(false); }
      };
      fetchData();
    }
  }, [isEdit, id, user?.id]);

  const enrichedElements = useMemo(() => formData.elements.map(el => {
    const info = allElementsMap[el.element_id];
    return { ...el, symbol: info?.symbol || '?', name: info?.name || '', atomic_number: info?.atomic_number };
  }), [formData.elements, allElementsMap]);

  const percentageHint = useMemo(() => {
    if (normalizeElements(formData.elements).length === 0) return null;
    const diff = round3(100 - totalPercentage);
    if (Math.abs(diff) < EPS) return { type: 'success', text: 'Сумма 100.000%' };
    if (diff > 0) return { type: 'info', text: `Добавьте ещё ${diff.toFixed(3)}%` };
    return { type: 'warning', text: `Уберите ${Math.abs(diff).toFixed(3)}%` };
  }, [formData.elements, totalPercentage, normalizeElements]);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="prediction-form-container">
      {apiError && <div className="alert alert-danger">{apiError}</div>}
      <form onSubmit={handleSubmit} className="prediction-form">
        <div className="form-group">
          <label htmlFor="category">Категория</label>
          <select id="category" name="category" value={formData.category} onChange={handleInputChange} className={errors.category ? 'input-error' : ''}>
            <option value="">-- Автоопределение --</option>
            {categoryOptions.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          {autoCategory && !userSelectedCategory && !formData.category && (
            <div className="hint hint-success">Автоопределено: <strong>{autoCategory}</strong> (уверенность: {(autoCategoryConfidence * 100).toFixed(1)}%)</div>
          )}
          {showCategoryWarning && autoCategory && formData.category && autoCategory !== formData.category && (
            <div className="hint hint-warning">Модель определила категорию <strong>{autoCategory}</strong> ({(autoCategoryConfidence * 100).toFixed(1)}%). Выбранная категория: <strong>{formData.category}</strong></div>
          )}
          {errors.category && <div className="error-text">{errors.category}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="rolling_type">Тип прокатки</label>
          <select id="rolling_type" name="rolling_type" value={formData.rolling_type} onChange={handleInputChange} className={errors.rolling_type ? 'input-error' : ''}>
            <option value="">-- Выберите тип прокатки --</option>
            {rollingOptions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          {errors.rolling_type && <div className="error-text">{errors.rolling_type}</div>}
        </div>
        <div className="form-group">
          <label htmlFor="size">Размер (size)</label>
          <input id="size" type="text" value={size} onChange={e => setSize(e.target.value)} placeholder="10.0" inputMode="decimal" />
          <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>Числовое значение, опционально</div>
        </div>
        <div className="form-group">
          <label>Элементы</label>
          <ElementSelector selectedElements={formData.elements} onChange={handleElementsChange} maxTotalPercentage={100} requireExactTotal={true} disabled={submitting} />
          {percentageHint && <div className={`hint hint-${percentageHint.type}`}>{percentageHint.text}</div>}
          {errors.elements && <div className="error-text">{errors.elements}</div>}
        </div>
        {enrichedElements.length > 0 && (
          <div className="elements-summary">
            {enrichedElements.map((el, idx) => (
              <span key={`${el.element_id}-${idx}`} className="element-tag">{el.symbol} {round3(el.percentage).toFixed(1)}%</span>
            ))}
          </div>
        )}
        <div className="form-group">
          <label>Прогноз (предел прочности, МПа)</label>
          <div className="prediction-result">
            <span className="prediction-value">{predicting ? 'Вычисление...' : predictedValue != null ? round3(predictedValue).toFixed(1) : '--'}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => requestPrediction(false)} disabled={predicting}>Обновить</button>
          </div>
          {predictError && <div className="error-text">{predictError}</div>}
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={submitting || !formData.person_id}>{submitting ? 'Сохранение...' : 'Сохранить'}</button>
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/predictions')} disabled={submitting}>Отмена</button>
        </div>
      </form>
    </div>
  );
};

export default PredictionForm;