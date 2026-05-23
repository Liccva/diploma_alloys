import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { personService, roleService, organizationService } from '../services/api';
import LoadingSpinner from '../components/common/LoadingSpinner';

const ROLE_LABELS = {
  'admin': 'Администратор',
  'администратор': 'Администратор',
  'researcher': 'Исследователь',
  'исследователь': 'Исследователь',
  'guest': 'Гость',
  'гость': 'Гость',
};

const getRoleClass = (name) => {
  const n = (name || '').toLowerCase();
  if (n === 'admin' || n === 'администратор') return 'role-badge role-admin';
  if (n === 'researcher' || n === 'исследователь') return 'role-badge role-researcher';
  if (n === 'guest' || n === 'гость') return 'role-badge role-guest';
  return 'role-badge role-default';
};

const Avatar = ({ person, size = 40 }) => {
  const [src, setSrc] = useState(null);

  useEffect(() => {
    if (person.avatar_filename) {
      setSrc(personService.getAvatarUrl(person.id) + '?t=' + Date.now());
    }
  }, [person]);

  const initials = [
    (person.first_name || person.login || '').charAt(0),
    (person.last_name || '').charAt(0),
  ].filter(Boolean).join('').toUpperCase() || '?';

  const avatarStyle = {
    width: size,
    height: size,
    fontSize: size * 0.36,
  };

  return (
    <div className="avatar" style={avatarStyle}>
      {src ? (
        <img
          src={src}
          alt=""
          className="avatar-img"
          onError={() => setSrc(null)}
        />
      ) : (
        <span className="avatar-initials">{initials}</span>
      )}
    </div>
  );
};

const UsersListPage = () => {
  const { user: currentUser, role } = useAuth();
  const navigate = useNavigate();

  const isAdmin = role === 'admin' || role === 'администратор';

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [roles, setRoles] = useState([]);
  const [orgs, setOrgs] = useState([]);

  useEffect(() => {
    const loadMappings = async () => {
      try {
        const [rolesRes, orgsRes] = await Promise.all([
          roleService.getAll(),
          organizationService.getAll()
        ]);
        setRoles(rolesRes.data || []);
        setOrgs(orgsRes.data || []);
      } catch (err) {
        console.error('Error loading mappings:', err);
      }
    };
    loadMappings();
  }, []);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await personService.getAll();
      setUsers(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Ошибка загрузки пользователей');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const getRoleName = (user) => {
    if (user.role_name) return user.role_name;
    if (user.role_id && roles.length > 0) {
      const role = roles.find(r => r.id === user.role_id);
      return role ? role.name : null;
    }
    return null;
  };

  const getOrgName = (user) => {
    if (user.organization_name) return user.organization_name;
    if (user.organization_id && orgs.length > 0) {
      const org = orgs.find(o => o.id === user.organization_id);
      return org ? org.name : null;
    }
    return null;
  };

  const q = search.toLowerCase();
  const filtered = users.filter(u => {
    if (!q) return true;
    const roleName = getRoleName(u) || '';
    const orgName = getOrgName(u) || '';
    return (
      u.login?.toLowerCase().includes(q) ||
      u.first_name?.toLowerCase().includes(q) ||
      u.last_name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      roleName.toLowerCase().includes(q) ||
      orgName.toLowerCase().includes(q)
    );
  });

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Пользователи системы</h2>
        {isAdmin && (
          <Link className="btn btn-primary" to="/register">+ Добавить</Link>
        )}
      </div>

      <div className="search-box">
        <input
          type="text"
          placeholder="Поиск по имени, логину, роли, организации..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      {filtered.length === 0 ? (
        <div className="empty-state">
          <p>{search ? 'Ничего не найдено' : 'Список пуст'}</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th className="col-avatar"></th>
                <th>Пользователь</th>
                <th>Роль</th>
                <th>Организация</th>
                <th>Статус</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(u => {
                const fullName = [u.last_name, u.first_name].filter(Boolean).join(' ');
                const roleName = getRoleName(u);
                const orgName = getOrgName(u);
                const roleClass = getRoleClass(roleName);
                const isMe = currentUser?.id === u.id;

                return (
                  <tr
                    key={u.id}
                    className="table-row-clickable"
                    onClick={() => navigate(`/users/${u.id}`)}
                  >
                    <td onClick={e => e.stopPropagation()}>
                      <Avatar person={u} />
                    </td>
                    <td>
                      <div className="user-name">
                        {fullName || u.login}
                        {isMe && <span className="badge-me">Вы</span>}
                      </div>
                      <div className="user-login">@{u.login}</div>
                    </td>
                    <td>
                      {roleName ? (
                        <span className={roleClass}>
                          {ROLE_LABELS[roleName.toLowerCase()] || roleName}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="text-muted">
                      {orgName || '—'}
                    </td>
                    <td>
                      {u.is_active !== false ? (
                        <span className="status-active">Активен</span>
                      ) : (
                        <span className="status-blocked">Заблокирован</span>
                      )}
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div className="actions-group">
                        <Link className="btn btn-secondary btn-sm" to={`/users/${u.id}`}>
                          Просмотр
                        </Link>
                        {isAdmin && (
                          <Link className="btn btn-outline btn-sm" to={`/users/${u.id}/edit`}>
                            Изменить
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="table-footer">
            Показано: {filtered.length} из {users.length}
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersListPage;

