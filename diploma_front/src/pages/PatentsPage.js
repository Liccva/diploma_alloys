import React, { useEffect, useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { patentService, alloyService } from "../services/api";
import { useAuth } from "../context/AuthContext";
import LoadingSpinner from "../components/common/LoadingSpinner";

const fmtDate = (d) => d ? new Date(d).toLocaleDateString("ru-RU") : "—";
const catLabel = (c) => c || "—";

const PatentsPage = () => {
  const navigate = useNavigate();
  const { role, isAuthenticated, user } = useAuth();

  const isAdmin      = role === "admin"      || role === "администратор";
  const isResearcher = role === "researcher" || role === "исследователь";
  const canCreate    = isAuthenticated && (isAdmin || isResearcher);

  const [patents, setPatents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [search, setSearch]   = useState("");

  const canEditPatent = (patent) => {
    if (isAdmin) return true;
    if (!isResearcher) return false;
    if (patent.authors && Array.isArray(patent.authors)) {
      return patent.authors.some(author => author.person_id === user?.id);
    }
    return false;
  };

  const canDeletePatent = canEditPatent;

  const fetchPatents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await patentService.getAll(0, 1000);
      const patentsData = Array.isArray(res.data) ? res.data : [];

      if (isResearcher && !isAdmin && patentsData.length > 0) {
        const patentsWithAuthors = await Promise.all(
          patentsData.map(async (patent) => {
            try {
              const authorsRes = await patentService.getAuthors(patent.id);
              return { ...patent, authors: authorsRes.data || [] };
            } catch (e) {
              return { ...patent, authors: [] };
            }
          })
        );
        setPatents(patentsWithAuthors);
      } else {
        setPatents(patentsData);
      }
    } catch (err) {
      if (err.message === 'Network Error' || !err.response) {
        setError("Ошибка загрузки данных. Проверьте соединение с сервером.");
      } else {
        setError(err.response?.data?.detail || err.message || "Ошибка загрузки");
      }
    } finally {
      setLoading(false);
    }
  }, [isAdmin, isResearcher]);

  useEffect(() => { fetchPatents(); }, [fetchPatents]);

  const handleDelete = async (patent) => {
    if (!canDeletePatent(patent)) {
      alert("У вас нет прав для удаления этого патента");
      return;
    }

    if (!window.confirm(`Удалить патент "${patent.patent_name}"? Это действие нельзя отменить.`)) return;

    try {
      // Проверяем наличие связанных сплавов
      try {
        const alloysRes = await alloyService.getByPatent(patent.id);
        const linkedAlloys = alloysRes.data || [];

        if (linkedAlloys.length > 0) {
          alert(
            `Невозможно удалить патент: существуют связанные сплавы (${linkedAlloys.length} шт.).\n` +
            `Сначала удалите или переназначьте сплавы.`
          );
          return;
        }
      } catch (checkErr) {
        // Если не удалось проверить (сетевая ошибка) — предупреждаем
        if (checkErr.message === 'Network Error' || !checkErr.response) {
          alert("Не удалось проверить связанные сплавы. Проверьте соединение с сервером.");
          return;
        }
        // Если другая ошибка — продолжаем (может, эндпоинт не работает)
        console.warn("Не удалось проверить связанные сплавы:", checkErr);
      }

      await patentService.delete(patent.id);
      setPatents(prev => prev.filter(p => p.id !== patent.id));
      alert("Патент успешно удалён");
    } catch (err) {
      if (err.message === 'Network Error' || !err.response) {
        alert("Ошибка соединения с сервером. Проверьте сеть.");
      } else {
        const detail = err.response?.data?.detail || "";
        if (detail.toLowerCase().includes("связан") || detail.toLowerCase().includes("foreign key") || detail.toLowerCase().includes("constraint")) {
          alert("Невозможно удалить патент: существуют связанные сплавы. Сначала удалите или переназначьте сплавы.");
        } else {
          alert(detail || "Ошибка удаления патента");
        }
      }
    }
  };

  const q = search.toLowerCase();
  const filtered = patents.filter((p) =>
    !q ||
    p.patent_name?.toLowerCase().includes(q) ||
    p.patent_number?.toLowerCase().includes(q) ||
    p.assignee?.toLowerCase().includes(q) ||
    p.ipc_code?.toLowerCase().includes(q)
  );

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container">
      <div className="page-header">
        <h2>Патенты</h2>
        {canCreate && <Link className="btn btn-primary" to="/patents/new">Новый патент</Link>}
      </div>

      <div className="patents-filters">
        <input
          type="text"
          placeholder="Поиск по названию, номеру, правообладателю..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && (
        <div className="form-error">
          {error}
          <button className="btn btn-sm btn-outline" onClick={fetchPatents} style={{ marginLeft: 12 }}>
            Повторить
          </button>
        </div>
      )}

      {!error && filtered.length === 0 && (
        <div className="empty-state">
          <p>{search ? "По вашему запросу ничего не найдено" : "Список патентов пуст"}</p>
        </div>
      )}

      {!error && filtered.length > 0 && (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Номер</th>
                <th>Название</th>
                <th>Правообладатель</th>
                <th>Категория</th>
                <th>Выдан</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => {
                const canEdit = canEditPatent(p);
                return (
                  <tr key={p.id}>
                    <td>{p.patent_number}</td>
                    <td>
                      <Link to={`/patents/${p.id}`} className="patent-link">
                        {p.patent_name}
                      </Link>
                    </td>
                    <td>{p.assignee || "—"}</td>
                    <td>{catLabel(p.category)}</td>
                    <td>{fmtDate(p.issue_date)}</td>
                    <td className="actions">
                      <Link className="btn btn-secondary btn-sm" to={`/patents/${p.id}`}>
                        Просмотр
                      </Link>
                      {canEdit && (
                        <>
                          <Link className="btn btn-outline btn-sm" to={`/patents/edit/${p.id}`}>
                            Изменить
                          </Link>
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleDelete(p)}
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
          <div className="pagination-info">
            Показано: {filtered.length} из {patents.length}
          </div>
        </div>
      )}
    </div>
  );
};

export default PatentsPage;