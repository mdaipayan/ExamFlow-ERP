import React, { useEffect, useRef, useState } from "react";
import {
  createStudent,
  getStudent,
  importStudentsCsv,
  listStudentEnrollments,
  listStudents,
} from "./api/students";
import { ApiError } from "./api/client";
import { useAuth } from "./auth/AuthContext";
import type { Student, StudentCreateRequest, StudentEnrollment, StudentImportResult } from "./types/student";

type Props = {
  onBackToDashboard?: () => void;
};

const emptyForm: StudentCreateRequest = {
  registration_number: "",
  roll_number: "",
  full_name: "",
  gender: "",
  mother_name: "",
  status: "ACTIVE",
};

function statusClass(status: string): string {
  return status.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

export function StudentManagement({ onBackToDashboard }: Props) {
  const { session, logout } = useAuth();
  const [students, setStudents] = useState<Student[]>([]);
  const [selected, setSelected] = useState<Student | null>(null);
  const [enrollments, setEnrollments] = useState<StudentEnrollment[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<StudentCreateRequest>(emptyForm);
  const [error, setError] = useState("");
  const [importMessage, setImportMessage] = useState("");
  const [importErrors, setImportErrors] = useState<{ row: number; message: string }[]>([]);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function loadStudents(term = search) {
    if (!session) return;

    setLoading(true);
    setError("");

    try {
      const result = await listStudents(session.accessToken, term);
      setStudents(result);

      if (selected) {
        const fresh = result.find((student) => student.id === selected.id);
        if (fresh) setSelected(fresh);
      }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        logout();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Unable to load students.");
    } finally {
      setLoading(false);
    }
  }

  async function openStudent(student: Student) {
    if (!session) return;

    setSelected(student);
    setDetailLoading(true);
    setError("");

    try {
      const [fresh, history] = await Promise.all([
        getStudent(session.accessToken, student.id),
        listStudentEnrollments(session.accessToken, student.id),
      ]);
      setSelected(fresh);
      setEnrollments(history);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        logout();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Unable to load student details.");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadStudents("");
  }, [session?.accessToken]);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;

    setSaving(true);
    setError("");

    try {
      const created = await createStudent(session.accessToken, {
        registration_number: form.registration_number.trim(),
        roll_number: form.roll_number?.trim() || null,
        full_name: form.full_name.trim(),
        gender: form.gender?.trim() || null,
        mother_name: form.mother_name?.trim() || null,
        status: form.status || "ACTIVE",
      });
      setStudents((current) =>
        [...current.filter((item) => item.id !== created.id), created]
          .sort((a, b) => a.registration_number.localeCompare(b.registration_number)),
      );
      setForm(emptyForm);
      setShowCreate(false);
      await openStudent(created);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        logout();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Unable to create student.");
    } finally {
      setSaving(false);
    }
  }

  async function handleImport(file: File) {
    if (!session) return;

    setImporting(true);
    setImportMessage("");
    setImportErrors([]);
    setError("");

    try {
      const result: StudentImportResult = await importStudentsCsv(session.accessToken, file);
      setImportMessage(
        result.message +
          " Created: " +
          result.created +
          ", updated: " +
          result.updated +
          ".",
      );
      setImportErrors(result.errors);
      if (result.errors.length === 0) {
        await loadStudents(search);
      }
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        logout();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Unable to import students.");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function submitSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadStudents(search);
  }

  return (
    <div className="student-page">
      <section className="page-toolbar">
        <div>
          <p className="eyebrow">Student Master</p>
          <h2>Students</h2>
          <p className="page-description">
            Search students, review their academic identity, or add students to the master.
          </p>
        </div>

        <div className="toolbar-actions">
          {onBackToDashboard ? (
            <button type="button" className="secondary-button" onClick={onBackToDashboard}>
              Dashboard
            </button>
          ) : null}
          <button type="button" className="primary" onClick={() => setShowCreate((value) => !value)}>
            {showCreate ? "Close form" : "Add Student"}
          </button>
          <label className="upload-button">
            {importing ? "Importing..." : "Import CSV"}
            <input
              ref={fileRef}
              type="file"
              accept=".csv,text/csv"
              disabled={importing}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void handleImport(file);
              }}
            />
          </label>
        </div>
      </section>

      {error ? (
        <div className="error-banner page-banner" role="alert">
          {error}
        </div>
      ) : null}

      {importMessage ? (
        <div className="success-banner page-banner" role="status">
          {importMessage}
          {importErrors.length ? (
            <div className="import-errors">
              {importErrors.slice(0, 8).map((item) => (
                <div key={item.row}>Row {item.row}: {item.message}</div>
              ))}
              {importErrors.length > 8 ? (
                <div>…and {importErrors.length - 8} more.</div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {showCreate ? (
        <form className="panel student-form" onSubmit={handleCreate}>
          <div className="panel-header">
            <div>
              <h3>Add student</h3>
              <p>Create a student record in the institution master.</p>
            </div>
          </div>

          <div className="form-grid">
            <label>
              <span>Registration number *</span>
              <input
                required
                value={form.registration_number}
                onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
              />
            </label>
            <label>
              <span>Roll number</span>
              <input
                value={form.roll_number ?? ""}
                onChange={(e) => setForm({ ...form, roll_number: e.target.value })}
              />
            </label>
            <label className="wide">
              <span>Full name *</span>
              <input
                required
                minLength={2}
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </label>
            <label>
              <span>Gender</span>
              <input
                value={form.gender ?? ""}
                onChange={(e) => setForm({ ...form, gender: e.target.value })}
              />
            </label>
            <label>
              <span>Mother name</span>
              <input
                value={form.mother_name ?? ""}
                onChange={(e) => setForm({ ...form, mother_name: e.target.value })}
              />
            </label>
            <label>
              <span>Status</span>
              <select
                value={form.status ?? "ACTIVE"}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </label>
          </div>

          <div className="form-actions">
            <button type="button" className="secondary-button" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={saving}>
              {saving ? "Saving..." : "Save student"}
            </button>
          </div>
        </form>
      ) : null}

      <section className="student-layout">
        <div className="panel student-list-panel">
          <div className="panel-header student-list-header">
            <div>
              <h3>Student records</h3>
              <p>
                {students.length >= 500
                  ? "Showing the first 500 matches."
                  : students.length + " record" + (students.length === 1 ? "" : "s")}
              </p>
            </div>
            <form className="student-search" onSubmit={submitSearch}>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search registration, roll or name"
                aria-label="Search students"
              />
              <button type="submit" className="secondary-button">Search</button>
            </form>
          </div>

          {loading ? (
            <div className="list-loading">
              <div className="spinner" aria-hidden="true" />
              <span>Loading students...</span>
            </div>
          ) : students.length === 0 ? (
            <div className="empty-state">
              <strong>No students found</strong>
              <span>Try another search or import the student master CSV.</span>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Registration</th>
                    <th>Roll</th>
                    <th>Name</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr
                      key={student.id}
                      className={selected?.id === student.id ? "selected-row" : ""}
                      onClick={() => void openStudent(student)}
                    >
                      <td>{student.registration_number}</td>
                      <td>{student.roll_number ?? "—"}</td>
                      <td>
                        <strong>{student.full_name}</strong>
                        <small>{student.gender ?? "Gender not recorded"}</small>
                      </td>
                      <td>
                        <span className={"status-badge " + statusClass(student.status)}>
                          {student.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="panel student-detail">
          {!selected ? (
            <div className="detail-empty">
              <strong>Select a student</strong>
              <span>Choose a record to view identity and enrolment details.</span>
            </div>
          ) : detailLoading ? (
            <div className="detail-empty">
              <div className="spinner" aria-hidden="true" />
              <span>Loading student details...</span>
            </div>
          ) : (
            <>
              <div className="detail-heading">
                <div>
                  <p className="eyebrow">Student profile</p>
                  <h3>{selected.full_name}</h3>
                  <p>{selected.registration_number} · {selected.roll_number ?? "No roll number"}</p>
                </div>
                <span className={"status-badge " + statusClass(selected.status)}>
                  {selected.status}
                </span>
              </div>

              <div className="detail-section">
                <h4>Identity</h4>
                <dl className="detail-grid">
                  <div><dt>Registration</dt><dd>{selected.registration_number}</dd></div>
                  <div><dt>Roll number</dt><dd>{selected.roll_number ?? "—"}</dd></div>
                  <div><dt>Gender</dt><dd>{selected.gender ?? "—"}</dd></div>
                  <div><dt>Mother name</dt><dd>{selected.mother_name ?? "—"}</dd></div>
                </dl>
              </div>

              <div className="detail-section">
                <div className="section-title-row">
                  <h4>Academic enrolment</h4>
                  <span>{enrollments.length}</span>
                </div>
                {enrollments.length === 0 ? (
                  <p className="muted-text">No programme enrolment recorded.</p>
                ) : (
                  <div className="enrolment-list">
                    {enrollments.map((item) => (
                      <div className="enrolment-item" key={item.id}>
                        <strong>{item.programme_code}</strong>
                        <span>{item.programme_name}</span>
                        <small>
                          {item.admission_year} · {item.entry_type} · {item.category ?? "Category not recorded"}
                        </small>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </aside>
      </section>
    </div>
  );
}
