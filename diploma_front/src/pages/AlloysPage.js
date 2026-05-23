import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { alloyService, patentService, personService } from "../services/api";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const normalizeLogin = (s) => String(s || "").trim().toLowerCase();

// Для отображения — сохраняем регистр как в БД
const splitAuthorsRaw = (authorsName) =>
  String(authorsName || "")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

// Для проверок прав — нормализуем
const splitAuthorsNorm = (authorsName) => splitAuthorsRaw(authorsName).map(normalizeLogin);

const buildPerson = (p) => {
  const id = p?.id;
  const login = p?.login ?? p?.Login ?? p?.username ?? "";
  const firstName = p?.firstName ?? p?.firstname ?? p?.first_name ?? "";
  const lastName = p?.lastName ?? p?.lastname ?? p?.last_name ?? "";
  return { id, login, firstName, lastName };
};

const personLabelFI = (person) => {
  const last = String(person?.lastName || "").trim();
  const first = String(person?.firstName || "").trim();
  const fio = `${last} ${first}`.trim();
  return fio || String(person?.login || "").trim() || "Неизвестно";
};

const AlloysPage = () => {
  const [alloys, setAlloys] = useState([]);
  const [filteredAlloys, setFilteredAlloys] = useState([]);

  const [patentsById, setPatentsById] = useState({});
  const [peopleByLogin, setPeopleByLogin] = useState({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("all");
  const [filterPatent, setFilterPatent] = useState("all");

  const navigate = useNavigate();
  const { isAdmin, isResearcher, user } = useAuth();
  const myLogin = useMemo(() => normalizeLogin(user?.login), [user?.login]);
  const myUserId = useMemo(() => user?.id, [user?.id]);

  const canCreateAlloy = () => isAdmin || isResearcher;

  const authorsDisplayFromDb = (authorsName) => {
    const rawTokens = splitAuthorsRaw(authorsName);
    if (rawTokens.length === 0) return "—";

    return rawTokens
      .map((tokenRaw) => {
        const person = peopleByLogin[normalizeLogin(tokenRaw)];
        if (!person) return tokenRaw;
        return `${personLabelFI(person)} (${person.id})`;
      })
      .join(", ");
  };

  // Исследователь может редактировать только сплавы по патенту, где он среди авторов
  // ИЛИ сплавы, которые он создал (created_by_id === user.id)
  const canEditAlloy = (alloy) => {
    if (isAdmin) return true;
    if (!isResearcher) return false;

    // Если пользователь создатель сплава — можно редактировать
    if (alloy?.created_by_id === myUserId) return true;

    const pid = alloy?.patent_id;
    if (!pid) return false;

    const patent = patentsById[pid];
    if (!patent) return false;

    const authorsNorm = splitAuthorsNorm(patent?.authors_name);
    return authorsNorm.includes(myLogin);
  };

  // Удаление "своих" сплавов = те же правила, что и редактирование
  const canDeleteAlloy = (alloy) => {
    if (isAdmin) return true;
    return canEditAlloy(alloy);
  };

  const categories = useMemo(() => {
    const set = new Set((alloys || []).map((a) => String(a?.category || "").trim()).filter(Boolean));
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [alloys]);

  const patentOptions = useMemo(() => {
    const ids = new Set((alloys || []).map((a) => a?.patent_id).filter(Boolean));
    return Array.from(ids)
      .map((id) => ({
        id: Number(id),
        name: patentsById[id]?.patent_name || `Патент #${id}`,
        number: patentsById[id]?.patent_number || `#${id}`,
      }))
      .sort((a, b) => String(a.name).localeCompare(String(b.name)));
  }, [alloys, patentsById]);

  const fetchAlloys = async () => {
    try {
      setLoading(true);
      setError("");

      const [alloysRes, patentsRes, peopleRes] = await Promise.all([
        alloyService.getAll(0, 100000),
        patentService.getAll(0, 100000),
        personService.getAll(0, 100000),
      ]);

      const alloysData = Array.isArray(alloysRes.data) ? alloysRes.data : [];
      const patentsData = Array.isArray(patentsRes.data) ? patentsRes.data : [];
      const peopleData = Array.isArray(peopleRes.data) ? peopleRes.data : [];

      const pMap = {};
      patentsData.forEach((p) => {
        if (p?.id != null) pMap[p.id] = p;
      });
      setPatentsById(pMap);

      const byLogin = {};
      peopleData
        .map(buildPerson)
        .filter((p) => String(p.login || "").trim())
        .forEach((p) => {
          byLogin[normalizeLogin(p.login)] = p;
        });
      setPeopleByLogin(byLogin);

      setAlloys(alloysData);
      setFilteredAlloys(alloysData);
    } catch (e) {
      console.error("Error loading alloys:", e);
      setError(e.response?.data?.detail || e.message || "Не удалось загрузить сплавы");
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...(alloys || [])];
    const term = String(searchTerm || "").trim().toLowerCase();

    if (term) {
      filtered = filtered.filter((alloy) => {
        const pid = alloy?.patent_id;
        const pat = pid ? patentsById[pid] : null;

        const patentText = pat
          ? `${pat.patent_name || ""} ${pat.patent_number || ""} ${pat.authors_name || ""} ${authorsDisplayFromDb(
              pat.authors_name
            )}`.toLowerCase()
          : "";

        return (
          String(alloy?.category || "").toLowerCase().includes(term) ||
          String(alloy?.rolling_type || "").toLowerCase().includes(term) ||
          String(alloy?.prop_value ?? "").toLowerCase().includes(term) ||
          String(alloy?.id ?? "").toLowerCase().includes(term) ||
          patentText.includes(term)
        );
      });
    }

    if (filterCategory !== "all") {
      filtered = filtered.filter((a) => a?.category === filterCategory);
    }

    if (filterPatent !== "all") {
      if (filterPatent === "no") {
        filtered = filtered.filter((a) => !a?.patent_id);
      } else {
        const pid = parseInt(filterPatent, 10);
        filtered = filtered.filter((a) => Number(a?.patent_id) === pid);
      }
    }

    setFilteredAlloys(filtered);
  };

  useEffect(() => {
    fetchAlloys();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    applyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm, filterCategory, filterPatent, alloys, patentsById, peopleByLogin]);

  const clearFilters = () => {
    setSearchTerm("");
    setFilterCategory("all");
    setFilterPatent("all");
  };

  const handleCreateAlloy = () => navigate("/alloys/new");

  const handleDeleteAlloy = async (alloy) => {
    if (!canDeleteAlloy(alloy)) {
      alert("У вас нет прав для удаления этого сплава");
      return;
    }

    if (!window.confirm("Вы уверены, что хотите удалить этот сплав?")) return;

    try {
      await alloyService.delete(alloy.id);
      setAlloys((prev) => prev.filter((a) => a.id !== alloy.id));
      setFilteredAlloys((prev) => prev.filter((a) => a.id !== alloy.id));
    } catch (err) {
      alert(err.response?.data?.detail || "Ошибка удаления сплава");
      console.error("Delete error:", err);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="alloys-page">
      <div className="page-header">
        <h2>Сплавы</h2>
        {canCreateAlloy() && (
          <button className="btn btn-primary" onClick={handleCreateAlloy}>
            Добавить сплав
          </button>
        )}
      </div>

      {error && (
        <div className="error-container">
          <h2>Ошибка</h2>
          <p>{error}</p>
          <button onClick={fetchAlloys} className="btn btn-primary">
            Повторить
          </button>
        </div>
      )}

      {!error && (
        <div className="alloys-filters">
          <div className="search-box">
            <input
              type="text"
              placeholder="Поиск (категория, прокатка, прочность, патент)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="filter-select">
            <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
              <option value="all">Все категории</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-select">
            <select value={filterPatent} onChange={(e) => setFilterPatent(e.target.value)}>
              <option value="all">Все патенты</option>
              <option value="no">Без патента</option>
              {patentOptions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.number} — {p.name}
                </option>
              ))}
            </select>
          </div>

          {(searchTerm || filterCategory !== "all" || filterPatent !== "all") && (
            <button className="btn btn-outline" onClick={clearFilters}>
              Сбросить
            </button>
          )}
        </div>
      )}

      {!error && filteredAlloys.length === 0 && (
        <div className="empty-state">
          <h3>Сплавы не найдены.</h3>
          {canCreateAlloy() && (
            <button className="btn btn-primary mt-2" onClick={handleCreateAlloy}>
              Создать первый сплав
            </button>
          )}
        </div>
      )}

      {!error && filteredAlloys.length > 0 && (
        <div className="table-container">
          <table className="table data-table">
            <thead>
              <tr>
                <th style={{ width: 120 }}>Номер патента</th>
                <th>Категория</th>
                <th style={{ width: 170 }}>Предел прочности</th>
                <th style={{ width: 150 }}>Тип прокатки</th>
                <th>Название патента</th>
                <th style={{ width: 260 }}>Действия</th>
              </tr>
            </thead>

            <tbody>
              {filteredAlloys.map((alloy) => {
                const pid = alloy?.patent_id;
                const patent = pid ? patentsById[pid] : null;
                const editable = canEditAlloy(alloy);

                return (
                  <tr key={alloy.id}>
                    <td>
                      {patent?.patent_number ? (
                        <Link to={`/patents/${pid}`} className="patent-link">
                          {patent.patent_number}
                        </Link>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>{alloy.category || "—"}</td>
                    <td>{alloy.prop_value ? `${alloy.prop_value} МПа` : "—"}</td>
                    <td>{alloy.rolling_type || "—"}</td>
                    <td>
                      {patent ? (
                        <>
                          <div>
                            <Link to={`/patents/${pid}`}>
                              {patent.patent_name || `Патент #${pid}`}
                            </Link>
                          </div>
                          {String(patent?.authors_name || "").trim() && (
                            <div className="text-muted" style={{ fontSize: 12 }}>
                              Авторы: {authorsDisplayFromDb(patent.authors_name)}
                            </div>
                          )}
                        </>
                      ) : (
                        "Не указан"
                      )}
                    </td>
                    <td className="actions">
                      <Link to={`/alloys/${alloy.id}`} className="btn btn-secondary btn-sm">
                        Просмотр
                      </Link>
                      {editable && (
                        <>
                          {" "}
                          <Link to={`/alloys/edit/${alloy.id}`} className="btn btn-outline btn-sm">
                            Изменить
                          </Link>
                        </>
                      )}
                      {canDeleteAlloy(alloy) && (
                        <>
                          {" "}
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDeleteAlloy(alloy)}
                          >
                            Удалить
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default AlloysPage;