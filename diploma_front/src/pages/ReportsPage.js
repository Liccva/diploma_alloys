import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  personService,
  roleService,
  predictionService,
  alloyService,
  patentService,
  modelService,
  elementService,
  organizationService,
} from "../services/api";

const API_BASE = 'http://localhost:8000';

const getField = (obj, keys) => {
  for (const k of keys) {
    if (obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
};

const groupCount = (items, keyFn) => {
  const map = new Map();
  for (const it of items || []) {
    const key = keyFn(it);
    const k = String(key ?? "").trim() || "(пусто)";
    map.set(k, (map.get(k) || 0) + 1);
  }
  return Array.from(map.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
};

const TabBtn = ({ active, onClick, children, disabled }) => (
  <button type="button" className={`admin-tab ${active ? "active" : ""}`} onClick={onClick} disabled={disabled}>
    {children}
  </button>
);

export default function ReportsPage() {
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();

  const userId = user?.id;

  const [tab, setTab] = useState(isAdmin ? "summary" : "my");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [roles, setRoles] = useState([]);
  const [persons, setPersons] = useState([]);
  const [predictions, setPredictions] = useState([]);
  const [alloys, setAlloys] = useState([]);
  const [patents, setPatents] = useState([]);
  const [models, setModels] = useState([]);
  const [elements, setElements] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [myPredictions, setMyPredictions] = useState([]);

  const loadAdminData = async () => {
    const [r, p, a, pa, m, el, orgs] = await Promise.all([
      roleService.getAll(),
      personService.getAll().catch(() => ({ data: [] })),
      alloyService.getAll(),
      patentService.getAll(),
      modelService.getAll(),
      elementService.getAll(),
      organizationService.getAll().catch(() => ({ data: [] })),
    ]);

    setRoles(r.data || []);
    setPersons(p.data || []);
    setAlloys(a.data || []);
    setPatents(pa.data || []);
    setModels(m.data || []);
    setElements(el.data || []);
    setOrganizations(orgs.data || []);

    try {
      const pr = await predictionService.getMyPredictions(0, 100000);
      setPredictions(pr.data || []);
    } catch (e) {
      console.error("Error loading predictions:", e);
      setPredictions([]);
    }
  };

  const loadMyPredictions = async () => {
    if (!userId) {
      setMyPredictions([]);
      return;
    }
    try {
      const res = await predictionService.getByPerson(userId);
      setMyPredictions(res.data || []);
    } catch (e) {
      console.error("Error loading my predictions:", e);
      setMyPredictions([]);
    }
  };

  useEffect(() => {
    if (!isAdmin && tab === "summary") setTab("my");
  }, [isAdmin, tab]);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        await loadMyPredictions();
        if (isAdmin) {
          await loadAdminData();
        } else {
          const m = await modelService.getAll();
          setModels(m.data || []);
        }
      } catch (e) {
        setError(e.response?.data?.detail || e.message || "Ошибка загрузки отчётов");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, [isAdmin, userId]);

  const roleIdToName = useMemo(() => {
    const map = new Map();
    for (const r of roles || []) map.set(String(r.id), r.name);
    return map;
  }, [roles]);

  const modelIdToName = useMemo(() => {
    const map = new Map();
    for (const m of models || []) map.set(String(m.id), m.name);
    return map;
  }, [models]);

  const personIdToUser = useMemo(() => {
    const map = new Map();
    for (const p of persons || []) map.set(String(p.id), p);
    return map;
  }, [persons]);

  const getOrgName = (user) => {
    if (!user) return '';
    if (user.organization_name && typeof user.organization_name === 'string') return user.organization_name.trim();
    if (user.organization_id && organizations.length > 0) {
      const org = organizations.find(o => o.id === user.organization_id);
      if (org) return org.name || '';
    }
    if (user.organization) {
      if (typeof user.organization === 'string') return user.organization.trim();
      if (user.organization.name) return user.organization.name.trim();
    }
    return '';
  };

  const adminTotals = useMemo(() => {
    if (!isAdmin) return null;
    return {
      users: persons.length, roles: roles.length, elements: elements.length,
      predictions: predictions.length, alloys: alloys.length,
      patents: patents.length, models: models.length,
    };
  }, [isAdmin, persons, roles, elements, predictions, alloys, patents, models]);

  const usersByRole = useMemo(() => {
    if (!isAdmin) return [];
    return groupCount(persons, (u) => {
      const rid = getField(u, ["role_id", "roleid"]);
      return roleIdToName.get(String(rid)) || "-";
    });
  }, [isAdmin, persons, roleIdToName]);

  const predictionsByCategory = useMemo(() => {
    if (!isAdmin) return [];
    return groupCount(predictions, (p) => getField(p, ["category"]));
  }, [isAdmin, predictions]);

  const predictionsByRolling = useMemo(() => {
    if (!isAdmin) return [];
    return groupCount(predictions, (p) => getField(p, ["rolling_type", "rollingtype"]));
  }, [isAdmin, predictions]);

  const predictionsByModel = useMemo(() => {
    if (!isAdmin) return [];
    return groupCount(predictions, (p) => {
      const mid = getField(p, ["ml_model_id", "mlmodelid", "mlmodel_id"]);
      return modelIdToName.get(String(mid)) || "-";
    });
  }, [isAdmin, predictions, modelIdToName]);

  const mostActiveUsers = useMemo(() => {
    if (!isAdmin) return [];
    const counts = new Map();
    for (const p of predictions || []) {
      const pid = getField(p, ["person_id", "personid"]);
      const key = String(pid ?? "");
      if (!key) continue;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return Array.from(counts.entries())
      .map(([personId, count]) => {
        const u = personIdToUser.get(String(personId));
        const rid = getField(u, ["role_id", "roleid"]);
        return {
          personId, count,
          login: u?.login || "-",
          name: [u?.last_name, u?.first_name].filter(Boolean).join(" ") || u?.login || "-",
          organization: getOrgName(u),
          role: roleIdToName.get(String(rid)) || "-",
        };
      })
      .sort((a, b) => b.count - a.count || a.login.localeCompare(b.login))
      .slice(0, 10);
  }, [isAdmin, predictions, personIdToUser, roleIdToName, organizations]);

  const orgsByPredictions = useMemo(() => {
    if (!isAdmin) return [];
    return groupCount(predictions, (p) => {
      const pid = getField(p, ["person_id", "personid"]);
      const u = personIdToUser.get(String(pid));
      return getOrgName(u) || "(пусто)";
    }).slice(0, 10);
  }, [isAdmin, predictions, personIdToUser, organizations]);

  const myPredictionsSorted = useMemo(() => {
    const arr = [...(myPredictions || [])];
    arr.sort((a, b) => (Number(b.id) || 0) - (Number(a.id) || 0));
    return arr;
  }, [myPredictions]);

  const myByCategory = useMemo(() => groupCount(myPredictions, (p) => getField(p, ["category"])), [myPredictions]);
  const myByRolling = useMemo(() => groupCount(myPredictions, (p) => getField(p, ["rolling_type", "rollingtype"])), [myPredictions]);

  // Скачать PDF
  const handleDownloadPdf = async () => {
  const token = localStorage.getItem('access_token');
  if (!token) { alert('Необходимо авторизоваться'); return; }

  try {
    const response = await fetch(`${API_BASE}/api/reports/download-pdf`, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (!response.ok) {
      if (response.status === 401) { alert('Сессия истекла. Войдите заново.'); return; }
      throw new Error('Ошибка скачивания');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().slice(0, 10);
    link.download = `Otchet_AlloyVault_${timestamp}.html`; // ← .html вместо .pdf
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (e) {
    alert('Не удалось скачать отчёт. Попробуйте позже.');
  }
};

  // Печать
  const handlePrint = () => {
    const originalTitle = document.title;
    const timestamp = new Date().toISOString().slice(0, 10);
    document.title = `Otchet_Alloys_${timestamp}`;
    window.print();
    setTimeout(() => { document.title = originalTitle; }, 100);
  };

  if (loading) {
    return (
      <div className="reports-page">
        <div className="page-header"><h2>Отчёты</h2></div>
        <div className="info-message"><p>Загрузка...</p></div>
      </div>
    );
  }

  return (
    <div className="reports-page">
      <div className="page-header">
        <h2>Отчёты</h2>
        <div className="page-header-actions">
          <button className="btn btn-primary btn-sm" onClick={handleDownloadPdf}>
            Скачать отчет
          </button>
          <button className="btn btn-secondary btn-sm" onClick={handlePrint}>
            Печать
          </button>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="admin-tabs">
        {isAdmin && <TabBtn active={tab === "summary"} onClick={() => setTab("summary")}>Сводка</TabBtn>}
        <TabBtn active={tab === "my"} onClick={() => setTab("my")}>Мои предсказания</TabBtn>
      </div>

      {/* SUMMARY (admin only) */}
      {isAdmin && tab === "summary" && adminTotals && (
        <>
          <div className="data-card">
            <h3>Сводка системы</h3>
            <div className="stats-cards">
              <div className="stat-card"><p className="stat-number">{adminTotals.users}</p><h3>Пользователи</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.roles}</p><h3>Роли</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.elements}</p><h3>Элементы</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.predictions}</p><h3>Прогнозы</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.alloys}</p><h3>Сплавы</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.patents}</p><h3>Патенты</h3></div>
              <div className="stat-card"><p className="stat-number">{adminTotals.models}</p><h3>ML модели</h3></div>
            </div>
          </div>

          <div className="reports-grid">
            <div className="data-card">
              <h3>Пользователи по ролям</h3>
              <table className="table">
                <thead><tr><th>Роль</th><th>Кол-во</th></tr></thead>
                <tbody>
                  {usersByRole.length > 0 ? usersByRole.map(r => (
                    <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>
                  )) : <tr><td colSpan={2} className="text-muted">Нет данных</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="data-card">
              <h3>Топ организаций по прогнозам</h3>
              <table className="table">
                <thead><tr><th>Организация</th><th>Прогнозов</th></tr></thead>
                <tbody>
                  {orgsByPredictions.length > 0 ? orgsByPredictions.map(r => (
                    <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>
                  )) : <tr><td colSpan={2} className="text-muted">Нет данных</td></tr>}
                </tbody>
              </table>
            </div>
          </div>

          <div className="data-card">
            <h3>Самые активные пользователи</h3>
            <table className="table">
              <thead><tr><th>Пользователь</th><th>Организация</th><th>Роль</th><th>Прогнозов</th></tr></thead>
              <tbody>
                {mostActiveUsers.length > 0 ? mostActiveUsers.map(u => (
                  <tr key={u.personId}>
                    <td><button className="btn-link" type="button" onClick={() => navigate(`/users/${u.personId}`)}>{u.name || u.login}</button></td>
                    <td>{u.organization || '—'}</td>
                    <td>{u.role}</td>
                    <td>{u.count}</td>
                  </tr>
                )) : <tr><td colSpan={4} className="text-muted">Нет данных</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="reports-grid-3">
            <div className="data-card">
              <h3>Прогнозы по категориям</h3>
              <table className="table">
                <thead><tr><th>Категория</th><th>Кол-во</th></tr></thead>
                <tbody>
                  {predictionsByCategory.slice(0, 8).map(r => (
                    <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>
                  ))}
                  {predictionsByCategory.length === 0 && <tr><td colSpan={2} className="text-muted">Нет данных</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="data-card">
              <h3>Прогнозы по прокатке</h3>
              <table className="table">
                <thead><tr><th>Тип</th><th>Кол-во</th></tr></thead>
                <tbody>
                  {predictionsByRolling.slice(0, 8).map(r => (
                    <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>
                  ))}
                  {predictionsByRolling.length === 0 && <tr><td colSpan={2} className="text-muted">Нет данных</td></tr>}
                </tbody>
              </table>
            </div>
            <div className="data-card">
              <h3>Прогнозы по моделям</h3>
              <table className="table">
                <thead><tr><th>Модель</th><th>Кол-во</th></tr></thead>
                <tbody>
                  {predictionsByModel.slice(0, 8).map(r => (
                    <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>
                  ))}
                  {predictionsByModel.length === 0 && <tr><td colSpan={2} className="text-muted">Нет данных</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* MY PREDICTIONS */}
      {tab === "my" && (
        <>
          <div className="data-card">
            <h3>Мои предсказания</h3>
            <p className="text-muted">Всего: {myPredictionsSorted.length}</p>
            <table className="table">
              <thead><tr><th>ID</th><th>Категория</th><th>Прокатка</th><th>Значение</th><th>ML модель</th><th></th></tr></thead>
              <tbody>
                {myPredictionsSorted.slice(0, 30).map(p => {
                  const mid = getField(p, ["ml_model_id", "mlmodelid", "mlmodel_id"]);
                  return (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>{getField(p, ["category"]) || "-"}</td>
                      <td>{getField(p, ["rolling_type", "rollingtype"]) || "-"}</td>
                      <td>{getField(p, ["prop_value", "propvalue"]) ?? "-"}</td>
                      <td>{modelIdToName.get(String(mid)) || "-"}</td>
                      <td><button className="btn btn-outline btn-sm" type="button" onClick={() => navigate(`/predictions/${p.id}`)}>Открыть</button></td>
                    </tr>
                  );
                })}
                {myPredictionsSorted.length === 0 && <tr><td colSpan={6} className="text-muted">Пока нет предсказаний</td></tr>}
              </tbody>
            </table>
          </div>

          {myPredictions.length > 0 && (
            <div className="data-card">
              <h3>Аналитика моих предсказаний</h3>
              <div className="reports-grid">
                <div>
                  <h4>По категориям</h4>
                  <table className="table">
                    <thead><tr><th>Категория</th><th>Кол-во</th></tr></thead>
                    <tbody>{myByCategory.map(r => <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>)}</tbody>
                  </table>
                </div>
                <div>
                  <h4>По типу прокатки</h4>
                  <table className="table">
                    <thead><tr><th>Тип</th><th>Кол-во</th></tr></thead>
                    <tbody>{myByRolling.map(r => <tr key={r.name}><td>{r.name}</td><td>{r.count}</td></tr>)}</tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}