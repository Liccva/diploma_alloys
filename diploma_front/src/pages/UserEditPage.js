import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { personService, roleService, authService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import LoadingSpinner from '../components/common/LoadingSpinner';

const Field = ({ label, required, error, children }) => (
  <div className="form-group">
    <label>
      {label}
      {required && <span className="required-star">*</span>}
    </label>
    {children}
    {error && <div className="field-error">{error}</div>}
  </div>
);

const Notice = ({ type, children }) => (
  <div className={`notice notice-${type}`}>
    {children}
  </div>
);

const UserEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user: currentUser, role, checkAuth } = useAuth();

  const personId = parseInt(id);
  const isAdmin  = role === 'admin' || role === 'администратор';
  const isOwner  = currentUser?.id === personId;

  const [form, setForm] = useState({
    first_name: '', last_name: '', middle_name: '',
    email: '', login: '', organization: '',
    role_id: '',
  });
  const [pwdForm, setPwdForm] = useState({ old_password: '', new_password: '', confirm: '' });
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingPwd, setSavingPwd] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [error, setError] = useState('');
  const [pwdError, setPwdError] = useState('');
  const [pwdSuccess, setPwdSuccess] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    if (!isAdmin && !isOwner) { navigate('/'); return; }
    fetchData();
  }, [id]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [userRes, rolesRes] = await Promise.allSettled([
        personService.getById(id),
        roleService.getAll(),
      ]);

      if (rolesRes.status === 'fulfilled') setRoles(rolesRes.value.data || []);

      if (userRes.status === 'fulfilled') {
        const u = userRes.value.data;
        setIsActive(u.is_active !== false);
        setForm({
          first_name: u.first_name || '',
          last_name: u.last_name || '',
          middle_name: u.middle_name || '',
          email: u.email || '',
          login: u.login || '',
          organization: u.organization_name || '',
          role_id: String(u.role_id || ''),
        });
      } else {
        setError('Пользователь не найден');
      }
    } catch {
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const validate = () => {
    const e = {};
    if (!form.first_name.trim()) e.first_name = 'Введите имя';
    if (!form.last_name.trim()) e.last_name = 'Введите фамилию';
    if (!form.email.trim()) e.email = 'Введите email';
    if (isAdmin && !form.role_id) e.role_id = 'Выберите роль';
    setFieldErrors(e);
    return !Object.keys(e).length;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    setFieldErrors(prev => ({ ...prev, [name]: '' }));
    setError('');
  };

  const handleRoleChange = (e) => {
    setForm(prev => ({ ...prev, role_id: e.target.value }));
    setFieldErrors(prev => ({ ...prev, role_id: '' }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true); setError('');
    try {
      const payload = {
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        middle_name: form.middle_name.trim() || undefined,
        email: form.email.trim() || undefined,
        login: form.login.trim() || undefined,
      };

      if (isAdmin) {
        payload.role_id = parseInt(form.role_id);
        if (form.organization.trim()) payload.organization = form.organization.trim();
        await personService.update(id, payload);
      } else {
        if (form.organization.trim()) payload.organization = form.organization.trim();
        await personService.updateProfile(id, payload);
        await checkAuth();
      }

      navigate(`/users/${id}`);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : err.message || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (pwdForm.new_password !== pwdForm.confirm) { setPwdError('Пароли не совпадают'); return; }
    if (pwdForm.new_password.length < 6) { setPwdError('Минимум 6 символов'); return; }
    setSavingPwd(true); setPwdError(''); setPwdSuccess('');
    try {
      await authService.changePassword(pwdForm.old_password, pwdForm.new_password);
      setPwdSuccess('Пароль успешно изменён');
      setPwdForm({ old_password: '', new_password: '', confirm: '' });
    } catch (err) {
      const d = err.response?.data?.detail;
      setPwdError(typeof d === 'string' ? d : 'Ошибка смены пароля');
    } finally {
      setSavingPwd(false);
    }
  };

  const handleDeactivate = async () => {
    const msg = isOwner
      ? 'Деактивировать свой аккаунт? Вы больше не сможете войти в систему.'
      : 'Деактивировать пользователя? Он потеряет доступ к системе.';
    if (!window.confirm(msg)) return;
    setDeactivating(true);
    try {
      await personService.deactivate(id);
      if (isOwner) {
        await authService.logout();
        navigate('/login');
      } else {
        setIsActive(false);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Ошибка деактивации');
    } finally {
      setDeactivating(false);
    }
  };

  const handleActivate = async () => {
    if (!window.confirm('Активировать аккаунт пользователя?')) return;
    setDeactivating(true);
    try {
      await personService.activate(id);
      setIsActive(true);
    } catch (err) {
      alert(err.response?.data?.detail || 'Ошибка активации');
    } finally {
      setDeactivating(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="user-edit-page">
      <div className="page-header">
        <button className="btn btn-secondary btn-back" onClick={() => navigate(`/users/${id}`)}>
          ← Назад
        </button>
        <h2>
          {isOwner && !isAdmin ? 'Редактирование профиля' : 'Редактирование пользователя'}
        </h2>
      </div>

      {/* Основные данные */}
      <div className="card">
        <div className="section-label">Личные данные</div>

        {error && <Notice type="error">{error}</Notice>}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-grid">
            <Field label="Фамилия" required error={fieldErrors.last_name}>
              <input type="text" className="form-control" name="last_name" value={form.last_name}
                onChange={handleChange} disabled={saving} maxLength={50} />
            </Field>

            <Field label="Имя" required error={fieldErrors.first_name}>
              <input type="text" className="form-control" name="first_name" value={form.first_name}
                onChange={handleChange} disabled={saving} maxLength={50} />
            </Field>

            <Field label="Отчество">
              <input type="text" className="form-control" name="middle_name" value={form.middle_name}
                onChange={handleChange} disabled={saving} maxLength={50} />
            </Field>

            <Field label="Email" required error={fieldErrors.email}>
              <input type="email" className="form-control" name="email" value={form.email}
                onChange={handleChange} disabled={saving} maxLength={100} />
            </Field>

            {(isAdmin || isOwner) && (
              <Field label="Логин">
                <input type="text" className="form-control" name="login" value={form.login}
                  onChange={handleChange} disabled={saving} maxLength={20} />
              </Field>
            )}

            <Field label="Организация">
              <input type="text" className="form-control" name="organization" value={form.organization}
                onChange={handleChange} disabled={saving} maxLength={200}
                placeholder="Название организации" />
            </Field>

            {isAdmin && (
              <Field label="Роль" required error={fieldErrors.role_id}>
                <select className="form-control" name="role_id" value={form.role_id}
                  onChange={handleRoleChange} disabled={saving}>
                  <option value="">— выберите —</option>
                  {roles.map(r => (
                    <option key={r.id} value={String(r.id)}>{r.name}</option>
                  ))}
                </select>
              </Field>
            )}
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary"
              onClick={() => navigate(`/users/${id}`)} disabled={saving}>
              Отмена
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        </form>
      </div>

      {/* Смена пароля */}
      {isOwner && (
        <div className="card">
          <div className="section-label">Смена пароля</div>

          {pwdError && <Notice type="error">{pwdError}</Notice>}
          {pwdSuccess && <Notice type="success">{pwdSuccess}</Notice>}

          <form onSubmit={handlePasswordChange} noValidate>
            <Field label="Текущий пароль">
              <input type="password" className="form-control" value={pwdForm.old_password}
                onChange={e => setPwdForm(p => ({ ...p, old_password: e.target.value }))}
                disabled={savingPwd} />
            </Field>
            <Field label="Новый пароль">
              <input type="password" className="form-control" value={pwdForm.new_password}
                onChange={e => setPwdForm(p => ({ ...p, new_password: e.target.value }))}
                disabled={savingPwd} />
            </Field>
            <Field label="Повторите новый пароль">
              <input type="password" className="form-control" value={pwdForm.confirm}
                onChange={e => setPwdForm(p => ({ ...p, confirm: e.target.value }))}
                disabled={savingPwd} />
            </Field>
            <div className="form-actions">
              <button type="submit" className="btn btn-primary" disabled={savingPwd}>
                {savingPwd ? 'Сохранение...' : 'Изменить пароль'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Статус аккаунта */}
      {(isOwner || isAdmin) && (
        <div className={`card status-card ${isActive ? 'active' : 'inactive'}`}>
          <div className={`status-title ${isActive ? 'active' : 'inactive'}`}>
            Статус аккаунта
          </div>

          <div className={`status-indicator ${isActive ? 'active' : 'inactive'}`}>
            {isActive ? 'Аккаунт активен' : 'Аккаунт деактивирован'}
          </div>

          {isActive ? (
            <>
              <p className="status-description">
                {isOwner
                  ? 'После деактивации вы потеряете доступ к системе. Восстановить аккаунт может только администратор.'
                  : 'Пользователь потеряет доступ к системе. Для восстановления нажмите «Активировать».'
                }
              </p>
              <button className="btn btn-danger"
                onClick={handleDeactivate} disabled={deactivating}>
                {deactivating ? 'Деактивация...'
                  : isOwner ? 'Деактивировать мой аккаунт' : 'Деактивировать пользователя'}
              </button>
            </>
          ) : (
            <>
              <p className="status-description">
                {isOwner
                  ? 'Ваш аккаунт деактивирован. Обратитесь к администратору для восстановления.'
                  : 'Пользователь не может войти в систему. Нажмите «Активировать» для восстановления доступа.'
                }
              </p>
              {isAdmin && (
                <button className="btn btn-primary"
                  onClick={handleActivate} disabled={deactivating}>
                  {deactivating ? 'Активация...' : 'Активировать аккаунт'}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default UserEditPage;