import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { modelService, personService, roleService, organizationService } from "../services/api";
import { useAuth } from "../context/AuthContext";

const ORG_NONE = "__NO_ORG__";

export default function AdminPanel() {
  const navigate = useNavigate();
  const { isAdmin } = useAuth();

  const [tab, setTab] = useState("models");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [models, setModels] = useState([]);
  const [roles, setRoles] = useState([]);
  const [persons, setPersons] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [newModel, setNewModel] = useState({ name: "", description: "" });
  const [newRole, setNewRole] = useState({ name: "", description: "" });
  const [orgFilter, setOrgFilter] = useState("");
  const [userSearch, setUserSearch] = useState("");
  const [bulkRoleId, setBulkRoleId] = useState("");
  const [bulkApplying, setBulkApplying] = useState(false);
  const [progressText, setProgressText] = useState("");

  const safeTrim = (v) => String(v ?? "").trim();

  useEffect(() => {
    if (!isAdmin) {
      navigate("/");
    }
  }, [isAdmin, navigate]);

  const reloadAll = async () => {
    setLoading(true);
    setError("");
    try {
      const [m, r, p, orgs] = await Promise.all([
        modelService.getAll(),
        roleService.getAll(),
        personService.getAll(),
        organizationService.getAll().catch(() => ({ data: [] })), // Если организации не загрузятся — пустой массив
      ]);

      setModels(m.data || []);
      setRoles(r.data || []);
      setPersons(p.data || []);
      setOrganizations(orgs.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка загрузки данных");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin) {
      reloadAll();
    }
  }, [isAdmin]);

  // Получаем название организации
  const getOrgName = (user) => {
    if (!user) return '';

    // Если есть organization_name как строка
    if (user.organization_name && typeof user.organization_name === 'string') {
      return user.organization_name.trim();
    }

    // Если есть organization_id — ищем в загруженных организациях
    if (user.organization_id && organizations.length > 0) {
      const org = organizations.find(o => o.id === user.organization_id);
      if (org) return org.name || '';
    }

    // Если organization — объект
    if (user.organization) {
      if (typeof user.organization === 'string') return user.organization.trim();
      if (user.organization.name) return user.organization.name.trim();
    }

    return '';
  };

  // Список уникальных организаций из данных пользователей
  const orgOptions = useMemo(() => {
    const orgSet = new Set();

    // Сначала добавляем организации из сервиса
    organizations.forEach(org => {
      if (org.name?.trim()) {
        orgSet.add(org.name.trim());
      }
    });

    // Затем из данных пользователей
    (persons || []).forEach(u => {
      const orgName = getOrgName(u);
      if (orgName) {
        orgSet.add(orgName);
      }
    });

    return Array.from(orgSet).sort((a, b) => a.localeCompare(b));
  }, [persons, organizations]);

  const filteredPersons = useMemo(() => {
    let list = persons || [];
    const org = safeTrim(orgFilter);

    if (org === ORG_NONE) {
      list = list.filter(p => !getOrgName(p));
    } else if (org) {
      list = list.filter(p => getOrgName(p) === org);
    }

    const q = safeTrim(userSearch).toLowerCase();
    if (q) {
      list = list.filter(u => {
        const fullName = [u.last_name, u.first_name, u.middle_name].filter(Boolean).join(" ").toLowerCase();
        const login = (u.login || "").toLowerCase();
        const idStr = String(u.id || "");
        return fullName.includes(q) || login.includes(q) || idStr.includes(q);
      });
    }

    return list;
  }, [persons, orgFilter, userSearch]);

  const createModel = async () => {
    if (!newModel.name.trim()) return;
    setLoading(true);
    setError("");
    try {
      await modelService.create({
        name: safeTrim(newModel.name),
        description: safeTrim(newModel.description),
      });
      setNewModel({ name: "", description: "" });
      await reloadAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка создания модели");
    } finally {
      setLoading(false);
    }
  };

  const deleteModel = async (id) => {
    if (!window.confirm(`Удалить модель #${id}?`)) return;
    setLoading(true);
    setError("");
    try {
      await modelService.delete(id);
      await reloadAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка удаления модели");
    } finally {
      setLoading(false);
    }
  };

  const createRole = async () => {
    if (!newRole.name.trim()) return;
    setLoading(true);
    setError("");
    try {
      await roleService.create({
        name: safeTrim(newRole.name),
        description: safeTrim(newRole.description),
      });
      setNewRole({ name: "", description: "" });
      await reloadAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка создания роли");
    } finally {
      setLoading(false);
    }
  };

  const deleteRole = async (id) => {
    if (!window.confirm(`Удалить роль #${id}?`)) return;
    setLoading(true);
    setError("");
    try {
      await roleService.delete(id);
      await reloadAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка удаления роли");
    } finally {
      setLoading(false);
    }
  };

  const updateUserRole = async (personId, newRoleId) => {
    if (!newRoleId) return;
    setLoading(true);
    setError("");
    try {
      await personService.update(personId, { role_id: Number(newRoleId) });
      await reloadAll();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Ошибка смены роли");
    } finally {
      setLoading(false);
    }
  };

  const applyRoleToFilteredUsers = async () => {
    if (!bulkRoleId) {
      alert("Выберите роль для массового назначения");
      return;
    }

    const targets = filteredPersons;
    if (targets.length === 0) {
      alert("Нет пользователей, подходящих под фильтры");
      return;
    }

    if (!window.confirm(`Назначить роль выбранным пользователям? (${targets.length} чел.)`)) return;

    setBulkApplying(true);
    setError("");
    setProgressText("Начинаем...");

    const failed = [];
    for (let i = 0; i < targets.length; i++) {
      const u = targets[i];
      setProgressText(`Обновление ${i + 1}/${targets.length}: ${u.login}`);

      try {
        if (Number(u.role_id) === Number(bulkRoleId)) continue;
        await personService.update(u.id, { role_id: Number(bulkRoleId) });
      } catch (e) {
        failed.push({
          id: u.id,
          login: u.login,
          error: e.response?.data?.detail || e.message,
        });
      }
    }

    await reloadAll();

    if (failed.length > 0) {
      setError(`Не обновлено: ${failed.length}. Первый: ${failed[0].login} - ${failed[0].error}`);
    }

    setProgressText("");
    setBulkApplying(false);
  };

  const resetUserFilters = () => {
    setOrgFilter("");
    setUserSearch("");
  };

  const isBusy = loading || bulkApplying;

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Админ-панель</h2>
        <button className="btn btn-secondary btn-sm" onClick={reloadAll} disabled={isBusy}>
          Обновить
        </button>
      </div>

      <div className="admin-tabs">
        <button
          className={`admin-tab ${tab === "models" ? "active" : ""}`}
          onClick={() => setTab("models")}
          disabled={isBusy}
        >
          Модели
        </button>
        <button
          className={`admin-tab ${tab === "roles" ? "active" : ""}`}
          onClick={() => setTab("roles")}
          disabled={isBusy}
        >
          Роли
        </button>
        <button
          className={`admin-tab ${tab === "users" ? "active" : ""}`}
          onClick={() => setTab("users")}
          disabled={isBusy}
        >
          Пользователи
        </button>
      </div>

      {error && <div className="form-error">{error}</div>}

      {bulkApplying && (
        <div className="notice notice-info">{progressText || "Выполняется..."}</div>
      )}

      {/* Models Tab */}
      {tab === "models" && (
        <div className="data-card">
          <h3>Управление моделями</h3>

          <div className="form-row">
            <input
              className="form-control"
              placeholder="Название модели"
              value={newModel.name}
              onChange={e => setNewModel(p => ({ ...p, name: e.target.value }))}
              disabled={isBusy}
            />
            <input
              className="form-control"
              placeholder="Описание"
              value={newModel.description}
              onChange={e => setNewModel(p => ({ ...p, description: e.target.value }))}
              disabled={isBusy}
            />
            <button className="btn btn-primary btn-sm" onClick={createModel} disabled={isBusy || !newModel.name.trim()}>
              Создать
            </button>
          </div>

          {models.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Описание</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {models.map(m => (
                  <tr key={m.id}>
                    <td>{m.id}</td>
                    <td>{m.name}</td>
                    <td>{m.description || '—'}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => deleteModel(m.id)} disabled={isBusy}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted">Нет моделей</p>
          )}
        </div>
      )}

      {/* Roles Tab */}
      {tab === "roles" && (
        <div className="data-card">
          <h3>Управление ролями</h3>

          <div className="form-row">
            <input
              className="form-control"
              placeholder="Название роли"
              value={newRole.name}
              onChange={e => setNewRole(p => ({ ...p, name: e.target.value }))}
              disabled={isBusy}
            />
            <input
              className="form-control"
              placeholder="Описание"
              value={newRole.description}
              onChange={e => setNewRole(p => ({ ...p, description: e.target.value }))}
              disabled={isBusy}
            />
            <button className="btn btn-primary btn-sm" onClick={createRole} disabled={isBusy || !newRole.name.trim()}>
              Создать
            </button>
          </div>

          {roles.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Название</th>
                  <th>Описание</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {roles.map(r => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>{r.name}</td>
                    <td>{r.description || '—'}</td>
                    <td>
                      <button className="btn btn-danger btn-sm" onClick={() => deleteRole(r.id)} disabled={isBusy}>
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted">Нет ролей</p>
          )}
        </div>
      )}

      {/* Users Tab */}
      {tab === "users" && (
        <div className="data-card">
          <h3>Управление пользователями</h3>

          <div className="form-row">
            <select
              className="form-control"
              value={orgFilter}
              onChange={e => setOrgFilter(e.target.value)}
              disabled={isBusy}
            >
              <option value="">Все организации</option>
              <option value={ORG_NONE}>Без организации</option>
              {orgOptions.map(org => (
                <option key={org} value={org}>{org}</option>
              ))}
            </select>

            <input
              className="form-control"
              placeholder="Поиск по имени или логину"
              value={userSearch}
              onChange={e => setUserSearch(e.target.value)}
              disabled={isBusy}
            />

            <button className="btn btn-secondary btn-sm" onClick={resetUserFilters} disabled={isBusy}>
              Сбросить
            </button>
          </div>

          <div className="form-row">
            <select
              className="form-control"
              value={bulkRoleId}
              onChange={e => setBulkRoleId(e.target.value)}
              disabled={isBusy}
            >
              <option value="">Массово назначить роль...</option>
              {roles.map(r => (
                <option key={r.id} value={String(r.id)}>{r.name}</option>
              ))}
            </select>

            <button
              className="btn btn-primary btn-sm"
              onClick={applyRoleToFilteredUsers}
              disabled={isBusy || !bulkRoleId || filteredPersons.length === 0}
            >
              Применить ({filteredPersons.length})
            </button>
          </div>

          {filteredPersons.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Организация</th>
                  <th>Роль</th>
                </tr>
              </thead>
              <tbody>
                {filteredPersons.map(u => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td>{u.login}</td>
                    <td>
                      {[u.last_name, u.first_name, u.middle_name].filter(Boolean).join(" ") || '—'}
                    </td>
                    <td>{getOrgName(u) || '—'}</td>
                    <td>
                      <select
                        className="form-control"
                        value={String(u.role_id || "")}
                        onChange={e => updateUserRole(u.id, e.target.value)}
                        disabled={isBusy}
                      >
                        <option value="">Без роли</option>
                        {roles.map(r => (
                          <option key={r.id} value={String(r.id)}>{r.name}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted">Нет пользователей</p>
          )}
        </div>
      )}
    </div>
  );
}