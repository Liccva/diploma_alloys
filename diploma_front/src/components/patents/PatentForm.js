import React, { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { patentService, personService } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import LoadingSpinner from "../common/LoadingSpinner";

const toDateInput = (iso) => (!iso ? "" : iso.slice(0, 10));
const toISO = (d) => (!d ? null : new Date(d).toISOString());

const EMPTY = {
  patent_number: "", patent_name: "", country: "RU",
  assignee: "", ipc_code: "", category: "",
  description: "", filing_date: "", issue_date: "",
};
const COUNTRIES = ["RU", "US", "DE", "FR", "GB", "JP", "CN", "KR", ""];

// ========== AuthorInput ==========
const AuthorInput = ({ onAdd, currentCount, disabled }) => {
  const [mode, setMode] = useState("external");
  const [name, setName] = useState("");
  const [order, setOrder] = useState("");
  const [users, setUsers] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loadingUsers, setLoadingUsers] = useState(false);

  useEffect(() => {
    if (mode !== "platform") return;
    setLoadingUsers(true);
    personService.getAll()
      .then((r) => setUsers(r.data || []))
      .catch(() => setUsers([]))
      .finally(() => setLoadingUsers(false));
  }, [mode]);

  const handleAdd = () => {
    const ord = parseInt(order, 10) || currentCount + 1;
    if (mode === "external") {
      if (!name.trim()) return;
      onAdd({ author_name: name.trim(), author_order: ord, person_id: null });
      setName(""); setOrder("");
    } else {
      if (!selectedId) return;
      const u = users.find((x) => String(x.id) === selectedId);
      if (!u) return;
      onAdd({
        author_name: `${u.last_name || ""} ${u.first_name || ""}`.trim(),
        author_order: ord,
        person_id: u.id,
      });
      setSelectedId(""); setOrder("");
    }
  };

  return (
    <div className="author-input-section">
      <div className="mode-toggle">
        {["external", "platform"].map((m) => (
          <button key={m} type="button"
            className={`btn btn-sm ${mode === m ? "btn-primary" : "btn-outline"}`}
            onClick={() => setMode(m)}>
            {m === "external" ? "Сторонний автор" : "Из системы"}
          </button>
        ))}
      </div>
      <div className="author-input-fields">
        {mode === "external" ? (
          <div className="form-group" style={{ flex: "1 1 200px", margin: 0 }}>
            <label>Имя автора</label>
            <input type="text" className="form-control" placeholder="Иванов А.И." value={name}
              onChange={(e) => setName(e.target.value)} maxLength={200} disabled={disabled}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAdd())} />
          </div>
        ) : (
          <div className="form-group" style={{ flex: "1 1 200px", margin: 0 }}>
            <label>Пользователь</label>
            <select className="form-control" value={selectedId} onChange={(e) => setSelectedId(e.target.value)}
              disabled={disabled || loadingUsers}>
              <option value="">— выберите —</option>
              {users.map((u) => (
                <option key={u.id} value={String(u.id)}>
                  {u.last_name} {u.first_name} ({u.login || u.email})
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="form-group" style={{ width: 100, margin: 0 }}>
          <label>Порядок</label>
          <input type="number" className="form-control" min={1} placeholder={currentCount + 1}
            value={order} onChange={(e) => setOrder(e.target.value)} disabled={disabled} />
        </div>
        <button type="button" className="btn btn-outline btn-add-author" onClick={handleAdd}
          disabled={disabled || (mode === "external" ? !name.trim() : !selectedId)}>
          + Добавить
        </button>
      </div>
    </div>
  );
};

// ========== AuthorRow ==========
const AuthorRow = ({ author, index, onDelete }) => (
  <div className="author-row">
    <span className="author-order">
      {author.author_order || index + 1}
    </span>
    <span className="author-name">{author.author_name}</span>
    {author.person_id && (
      <span className="author-registered">в системе</span>
    )}
    {onDelete && (
      <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>✕</button>
    )}
  </div>
);

// ========== PdfDropZone ==========
const PdfDropZone = ({ currentFile, patentId, onFile, onDelete, canDelete }) => {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const doUpload = async (file) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Можно загружать только PDF файлы"); return;
    }
    setUploading(true);
    try { await onFile(file); }
    catch (e) { alert(e.response?.data?.detail || "Ошибка загрузки"); }
    finally { setUploading(false); }
  };

  if (currentFile) return (
    <div className="pdf-file-info">
      <span className="pdf-icon">📄</span>
      <div className="pdf-details">
        <div className="pdf-name">{currentFile}</div>
        {patentId && (
          <a href={`http://localhost:8000/api/patents/${patentId}/pdf`}
            target="_blank" rel="noreferrer" className="pdf-link">
            Открыть PDF ↗
          </a>
        )}
      </div>
      {canDelete && (
        <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>
          Удалить файл
        </button>
      )}
    </div>
  );

  return (
    <div
      className={`pdf-dropzone ${dragging ? "dragging" : ""} ${uploading ? "uploading" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) doUpload(f); }}
      onClick={() => inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf"
        onChange={(e) => { const f = e.target.files[0]; if (f) doUpload(f); e.target.value = ""; }} />
      {uploading ? (
        <div className="pdf-dropzone-hint">Загрузка...</div>
      ) : (
        <>
          <div className="pdf-dropzone-icon">📁</div>
          <div className="pdf-dropzone-text">Перетащите PDF сюда</div>
          <div className="pdf-dropzone-hint">или нажмите для выбора файла</div>
        </>
      )}
    </div>
  );
};

// ========== Field ==========
const Field = ({ label, required, error, children }) => (
  <div className="form-group">
    <label>
      {label}{required && <span className="required-star">*</span>}
    </label>
    {children}
    {error && <div className="field-error">{error}</div>}
  </div>
);

// ========== PatentForm ==========
const PatentForm = ({ isEdit }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, role } = useAuth();

  const isAdmin = role === "admin" || role === "администратор";
  const isResearcher = role === "researcher" || role === "исследователь";
  const canEditAuthors = isAdmin || isResearcher;

  const [form, setForm] = useState(EMPTY);
  const [authors, setAuthors] = useState([]);
  const [pdfFile, setPdfFile] = useState(null);
  const [pendingPdf, setPendingPdf] = useState(null);

  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const fetchPatent = useCallback(async () => {
    if (!isEdit || !id) return;
    setLoading(true);
    try {
      const p = (await patentService.getById(id)).data;
      setForm({
        patent_number: p.patent_number || "",
        patent_name: p.patent_name || "",
        country: p.country || "RU",
        assignee: p.assignee || "",
        ipc_code: p.ipc_code || "",
        category: p.category || "",
        description: p.description || "",
        filing_date: toDateInput(p.filing_date),
        issue_date: toDateInput(p.issue_date),
      });
      setAuthors((p.authors || []).map((a) => ({
        id: a.id,
        author_name: a.author_name,
        author_order: a.author_order,
        person_id: a.person_id || null,
      })));
      setPdfFile(p.pdf_filename || null);
    } catch (err) {
      setError(err.response?.data?.detail || "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, [isEdit, id]);

  useEffect(() => { fetchPatent(); }, [fetchPatent]);

  const validate = () => {
    const e = {};
    if (!form.patent_number.trim()) e.patent_number = "Введите номер патента";
    if (!form.patent_name.trim()) e.patent_name = "Введите название патента";
    setFieldErrors(e);
    return !Object.keys(e).length;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
    if (fieldErrors[name]) setFieldErrors((p) => ({ ...p, [name]: "" }));
    if (error) setError(null);
  };

  const handleAddAuthorLocal = (author) => {
    setAuthors((prev) => [...prev, { ...author, author_order: author.author_order || prev.length + 1 }]);
  };
  const handleRemoveAuthorLocal = (idx) => {
    setAuthors((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleAddAuthorApi = async (author) => {
    try {
      await patentService.addAuthor(id, author.author_name, author.author_order, author.person_id);
      fetchPatent();
    } catch (e) { alert(e.response?.data?.detail || "Ошибка добавления автора"); }
  };
  const handleDeleteAuthorApi = async (authorId, name) => {
    if (!window.confirm(`Удалить автора "${name}"?`)) return;
    try { await patentService.deleteAuthor(authorId); fetchPatent(); }
    catch (e) { alert(e.response?.data?.detail || "Ошибка"); }
  };

  const handlePdfUpload = async (file) => {
    if (!isEdit) {
      setPendingPdf(file);
      setPdfFile(file.name);
      return;
    }
    const res = await patentService.uploadPdf(id, file);
    setPdfFile(res.data.pdf_filename);
  };

  const handlePdfDelete = async () => {
    if (!isEdit) { setPendingPdf(null); setPdfFile(null); return; }
    if (!window.confirm("Удалить PDF файл?")) return;
    await patentService.deletePdf(id);
    setPdfFile(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true); setError(null);

    const payload = {
      patent_number: form.patent_number.trim(),
      patent_name: form.patent_name.trim(),
      country: form.country || null,
      assignee: form.assignee.trim() || null,
      ipc_code: form.ipc_code.trim() || null,
      category: form.category.trim() || null,
      description: form.description.trim() || null,
      filing_date: toISO(form.filing_date),
      issue_date: toISO(form.issue_date),
    };

    try {
      if (isEdit) {
        await patentService.update(id, payload);
        navigate(`/patents/${id}`);
        return;
      }

      const res = await patentService.createWithAuthors({
        ...payload,
        authors: authors.map((a, idx) => ({
          author_name: a.author_name,
          author_order: a.author_order || idx + 1,
          person_id: a.person_id || null,
        })),
      });

      const newId = res.data?.id;

      if (newId && pendingPdf) {
        try { await patentService.uploadPdf(newId, pendingPdf); }
        catch (pdfErr) { console.warn("PDF upload failed:", pdfErr); }
      }

      navigate(newId ? `/patents/${newId}` : "/patents");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join("; ")
          : typeof detail === "string" ? detail : err.message || "Ошибка сохранения"
      );
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="patent-form-container">
      <div className="page-header">
        <h2>{isEdit ? "Редактирование патента" : "Новый патент"}</h2>
      </div>

      {error && <div className="form-error">{error}</div>}

      <form onSubmit={handleSubmit} noValidate>
        {/* ===== ОСНОВНАЯ ИНФОРМАЦИЯ ===== */}
        <div className="form-section-block">
          <h3 className="form-section-title">Основная информация</h3>

          <div className="form-grid">
            <div>
              <Field label="Номер патента" required error={fieldErrors.patent_number}>
                <input type="text" className={`form-control ${fieldErrors.patent_number ? "error" : ""}`}
                  name="patent_number" value={form.patent_number}
                  onChange={handleChange} maxLength={50} disabled={saving}
                  placeholder="RU2024XXXX" />
              </Field>
            </div>
            <div>
              <Field label="Страна">
                <select className="form-control" name="country" value={form.country} onChange={handleChange} disabled={saving}>
                  {COUNTRIES.map((c) => <option key={c} value={c}>{c || "— не указана —"}</option>)}
                </select>
              </Field>
            </div>
          </div>

          <Field label="Название патента" required error={fieldErrors.patent_name}>
            <input type="text" className={`form-control ${fieldErrors.patent_name ? "error" : ""}`}
              name="patent_name" value={form.patent_name}
              onChange={handleChange} maxLength={500} disabled={saving}
              placeholder="Полное название патента" />
          </Field>

          <Field label="Правообладатель">
            <input type="text" className="form-control" name="assignee" value={form.assignee}
              onChange={handleChange} maxLength={300} disabled={saving}
              placeholder="Название организации" />
          </Field>

          <div className="form-grid">
            <Field label="IPC код">
              <input type="text" className="form-control" name="ipc_code" value={form.ipc_code}
                onChange={handleChange} maxLength={50} disabled={saving} placeholder="C22C38/00" />
            </Field>
            <Field label="Категория">
              <input type="text" className="form-control" name="category" value={form.category}
                onChange={handleChange} maxLength={100} disabled={saving}
                placeholder="Автоматически по IPC" />
            </Field>
          </div>

          <div className="form-grid">
            <Field label="Дата подачи">
              <input type="date" className="form-control" name="filing_date" value={form.filing_date}
                onChange={handleChange} disabled={saving} />
            </Field>
            <Field label="Дата выдачи">
              <input type="date" className="form-control" name="issue_date" value={form.issue_date}
                onChange={handleChange} disabled={saving} />
            </Field>
          </div>

          <Field label="Описание">
            <textarea className="form-control" name="description" value={form.description}
              onChange={handleChange} disabled={saving} rows={4}
              placeholder="Краткое описание изобретения" />
          </Field>
        </div>

        {/* ===== АВТОРЫ ===== */}
        <div className="form-section-block">
          <h3 className="form-section-title">Авторы патента</h3>

          {authors.length === 0 && (
            <p className="text-muted" style={{ marginBottom: 12 }}>
              {isEdit ? "Авторы не добавлены" : "Список авторов пуст"}
            </p>
          )}

          {authors.map((a, idx) => (
            <AuthorRow key={a.id || idx} author={a} index={idx}
              onDelete={canEditAuthors ? (
                isEdit
                  ? () => handleDeleteAuthorApi(a.id, a.author_name)
                  : () => handleRemoveAuthorLocal(idx)
              ) : null}
            />
          ))}

          {canEditAuthors && (
            <>
              <AuthorInput
                onAdd={isEdit ? handleAddAuthorApi : handleAddAuthorLocal}
                currentCount={authors.length}
                disabled={saving}
              />
              {!isAdmin && isResearcher && !isEdit && (
                <p className="form-hint-text">
                  Вы будете автоматически добавлены как соавтор.
                </p>
              )}
            </>
          )}
        </div>

        {/* ===== PDF ===== */}
        <div className="form-section-block">
          <h3 className="form-section-title">PDF документ</h3>

          <PdfDropZone
            currentFile={pdfFile}
            patentId={isEdit ? id : null}
            onFile={handlePdfUpload}
            onDelete={handlePdfDelete}
            canDelete={canEditAuthors}
          />
          {!isEdit && pendingPdf && (
            <p className="form-hint-text">
              📎 PDF будет загружен автоматически после создания патента.
            </p>
          )}
          <p className="form-hint-text">Поддерживаются только PDF файлы</p>
        </div>

        {/* ===== КНОПКИ ===== */}
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" disabled={saving}
            onClick={() => navigate(isEdit ? `/patents/${id}` : "/patents")}>
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Сохранение..." : isEdit ? "Сохранить изменения" : "Создать патент"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PatentForm;