import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { personService, predictionService, modelService } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const API_BASE = 'http://localhost:8000';

const getAvatarSrc = (person) => {
  if (!person) return null;
  if (person.avatar_filename) {
    return `${API_BASE}/api/persons/${person.id}/avatar?t=${person.updated_at || Date.now()}`;
  }
  if (person.avatar_url) {
    return `${API_BASE}${person.avatar_url}?t=${person.updated_at || Date.now()}`;
  }
  return null;
};

const getInitials = (person) => {
  if (!person) return '?';
  return [
    (person.first_name || person.login || '?').charAt(0),
    (person.last_name || '').charAt(0),
  ].filter(Boolean).join('').toUpperCase() || '?';
};

const fmtDate = (d) =>
  d ? new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : '—';

const ROLE_LABELS = {
  admin: 'Администратор',
  администратор: 'Администратор',
  researcher: 'Исследователь',
  исследователь: 'Исследователь',
  guest: 'Гость',
  гость: 'Гость',
};

// Компонент AvatarView
const AvatarView = ({ person, size = 72 }) => {
  const [src, setSrc] = useState(null);
  const [err, setErr] = useState(false);
  const [avatarKey, setAvatarKey] = useState(Date.now());

  useEffect(() => {
    setErr(false);
    const newSrc = getAvatarSrc(person);
    setSrc(newSrc);
    setAvatarKey(Date.now());
  }, [person?.id, person?.avatar_filename, person?.avatar_url, person?.updated_at]);

  const initials = getInitials(person);

  const avatarStyle = {
    width: size,
    height: size,
    fontSize: Math.round(size * 0.36),
  };

  return (
    <div className="avatar-large" style={avatarStyle}>
      {(src && !err) ? (
        <img
          key={avatarKey}
          src={src}
          alt={initials}
          className="avatar-img"
          onError={() => setErr(true)}
        />
      ) : (
        <span className="avatar-initials">{initials}</span>
      )}
    </div>
  );
};

// Компонент AvatarEdit
const AvatarEdit = ({ person, onRefresh }) => {
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const doUpload = async (file) => {
    setUploading(true);
    try {
      await personService.uploadAvatar(person.id, file);
      onRefresh();
    } catch (e) {
      alert(e.response?.data?.detail || 'Ошибка загрузки');
    } finally {
      setUploading(false);
    }
  };

  const doDelete = async () => {
    if (!window.confirm('Удалить аватарку?')) return;
    try {
      await personService.deleteAvatar(person.id);
      onRefresh();
    } catch (e) {
      alert(e.response?.data?.detail || 'Ошибка');
    }
  };

  return (
    <div className="avatar-edit-container">
      <div className="avatar-edit-wrapper" onClick={() => inputRef.current?.click()}>
        <AvatarView person={person} size={80} />
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden-input"
        onChange={e => {
          const f = e.target.files[0];
          if (f) doUpload(f);
          e.target.value = '';
        }}
      />
      <div className="avatar-edit-buttons">
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? 'Загрузка...' : 'Изменить фото'}
        </button>
        {person?.avatar_filename && (
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={doDelete}
          >
            Удалить
          </button>
        )}
      </div>
    </div>
  );
};

// Компонент InfoRow
const InfoRow = ({ label, value }) => (
  <div className="info-row">
    <span className="info-label">{label}</span>
    <span className={`info-value ${!value ? 'info-value-empty' : ''}`}>
      {value || '—'}
    </span>
  </div>
);

// Главный компонент
const UserDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: currentUser, role, checkAuth } = useAuth();

  const isAdmin = role === 'admin' || role === 'администратор';
  const isOwner = currentUser?.id === parseInt(id);
  const canSeeDetails = isAdmin || isOwner;

  const [person, setPerson] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [models, setModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const p = (await personService.getById(id)).data;
      setPerson(p);

      if (canSeeDetails) {
        const [predsRes, modelsRes] = await Promise.allSettled([
          predictionService.getByPerson(id),
          modelService.getAll(),
        ]);
        if (predsRes.status === 'fulfilled') setPredictions(predsRes.value.data || []);
        if (modelsRes.status === 'fulfilled') {
          const map = {};
          (modelsRes.value.data || []).forEach(m => {
            map[m.id] = m.name;
          });
          setModels(map);
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  }, [id, canSeeDetails]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAvatarRefresh = async () => {
    await fetchData();
    if (isOwner) await checkAuth();
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="page-container">
        <div className="error-container">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <div className="form-actions">
            <button className="btn btn-primary" onClick={fetchData}>
              Повторить
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!person) {
    return (
      <div className="page-container">
        <p>Пользователь не найден</p>
      </div>
    );
  }

  const fullName = [person.last_name, person.first_name, person.middle_name]
    .filter(Boolean)
    .join(' ');
  const roleLabel = ROLE_LABELS[(person.role_name || '').toLowerCase()] || person.role_name || '—';

  const stats = {
    total: predictions.length,
    avg: predictions.length
      ? (predictions.reduce((s, p) => s + (p.prop_value || 0), 0) / predictions.length).toFixed(1)
      : 0,
  };

  return (
    <div className="page-container">
      {/* Шапка */}
      <div className="page-header">
        <h2>{isOwner ? 'Мой профиль' : 'Профиль пользователя'}</h2>
        <div className="page-header-actions">
          {isOwner && (
            <Link className="btn btn-outline" to={`/users/${id}/edit`}>
              Редактировать профиль
            </Link>
          )}
          {isAdmin && !isOwner && (
            <Link className="btn btn-outline" to={`/users/${id}/edit`}>
              Редактировать
            </Link>
          )}
        </div>
      </div>

      {/* Карточка */}
      <div className="card profile-card">
        <div className="profile-header">
          {/* Аватарка */}
          {isOwner ? (
            <AvatarEdit person={person} onRefresh={handleAvatarRefresh} />
          ) : (
            <AvatarView person={person} size={80} />
          )}

          {/* Информация */}
          <div className="profile-info">
            <h3>{fullName || person.login}</h3>
            <div className="profile-badges">
              <span className="badge badge-role">{roleLabel}</span>
              {!person.is_active && (
                <span className="badge badge-blocked">Заблокирован</span>
              )}
              {isOwner && (
                <span className="badge badge-me">● Вы</span>
              )}
            </div>

            <div className="info-grid">
              <InfoRow label="Логин" value={`@${person.login}`} />
              <InfoRow label="Email" value={canSeeDetails ? person.email : null} />
              <InfoRow label="Организация" value={person.organization_name} />
              <InfoRow label="В системе с" value={fmtDate(person.created_at)} />
              {canSeeDetails && (
                <InfoRow label="Последний вход" value={fmtDate(person.last_login)} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Статистика и прогнозы */}
      {canSeeDetails && (
        <>
          {predictions.length > 0 && (
            <div className="stats-grid">
              <div className="card stat-card">
                <div className="stat-value">{stats.total}</div>
                <div className="stat-label">прогнозов создано</div>
              </div>
              <div className="card stat-card">
                <div className="stat-value">{stats.avg}</div>
                <div className="stat-label">МПа среднее значение</div>
              </div>
            </div>
          )}

          <div className="card predictions-card">
            <div className="predictions-header">
              <h3>{isOwner ? 'Мои прогнозы' : 'Прогнозы пользователя'}</h3>
              <span className="badge badge-count">{predictions.length}</span>
              <Link className="btn btn-outline btn-sm" to="/predictions">
                Все прогнозы →
              </Link>
            </div>

            {predictions.length === 0 ? (
              <div className="empty-state">
                <p className="empty-text">
                  {isOwner ? 'У вас пока нет прогнозов' : 'Прогнозов пока нет'}
                </p>
                {isOwner && (
                  <Link className="btn btn-primary" to="/predictions/new">
                    Создать первый прогноз
                  </Link>
                )}
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
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.slice(0, 10).map(pred => (
                      <tr key={pred.id}>
                        <td>{pred.category || '—'}</td>
                        <td className="td-value">{pred.prop_value} МПа</td>
                        <td>{pred.rolling_type || '—'}</td>
                        <td className="td-muted">{models[pred.ml_model_id] || '—'}</td>
                        <td>
                          <div className="actions-group">
                            <Link
                              className="btn btn-secondary btn-sm"
                              to={`/predictions/${pred.id}`}
                            >
                              Подробнее
                            </Link>
                            {(isOwner || isAdmin) && (
                              <Link
                                className="btn btn-outline btn-sm"
                                to={`/predictions/edit/${pred.id}`}
                              >
                                Изменить
                              </Link>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {predictions.length > 10 && (
                  <div className="table-footer">
                    Показано 10 из {predictions.length} —{' '}
                    <Link to="/predictions">показать все</Link>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default UserDetailsPage;