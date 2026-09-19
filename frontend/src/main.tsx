import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { getDashboard } from "./api/dashboard";
import { ApiError } from "./api/client";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import type { DashboardData } from "./types/dashboard";
import { StudentManagement } from "./StudentManagement";
import "./styles.css";

const navItems = [
  "Dashboard",
  "Students",
  "Courses",
  "Examinations",
  "Marks & Results",
  "Reports",
  "Administration",
];

const actionToModule: Record<string, string> = {
  CREATE_EXAMINATION: "Examinations",
  OPEN_EXAMINATION: "Examinations",
  OPEN_MARKS: "Marks & Results",
  OPEN_RESULTS: "Marks & Results",
  OPEN_SCRUTINY: "Marks & Results",
  OPEN_REPORTS: "Reports",
};

function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }

    setSubmitting(true);
    try {
      await login(email, password);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand auth-brand">ExamFlow <span>ERP</span></div>
        <p className="eyebrow">Examination Office</p>
        <h1>Sign in</h1>
        <p className="auth-subtitle">
          Use your Examination Office account to continue.
        </p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@institution.edu"
              disabled={submitting}
            />
          </label>

          <label>
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              disabled={submitting}
            />
          </label>

          {error ? <div className="error-banner" role="alert">{error}</div> : null}

          <button className="primary auth-submit" type="submit" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="auth-footer">
          Your session is verified by the ExamFlow API.
        </p>
      </div>
    </div>
  );
}

function LoadingScreen({ message = "Checking your session..." }: { message?: string }) {
  return (
    <div className="auth-page">
      <div className="loading-card">
        <div className="brand auth-brand">ExamFlow <span>ERP</span></div>
        <div className="spinner" aria-hidden="true" />
        <p>{message}</p>
      </div>
    </div>
  );
}

function Dashboard({
  onNavigate,
}: {
  onNavigate: (module: string) => void;
}) {
  const { session, logout } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    if (!session) return;

    setLoading(true);
    setError("");

    try {
      const result = await getDashboard(session.accessToken);
      setData(result);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        logout();
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [session?.accessToken]);

  if (loading && !data) {
    return (
      <section className="dashboard-loading">
        <div className="spinner" aria-hidden="true" />
        <p>Loading examination office data...</p>
      </section>
    );
  }

  if (error && !data) {
    return (
      <section className="panel dashboard-error">
        <h2>Dashboard unavailable</h2>
        <p>{error}</p>
        <button type="button" className="secondary-button" onClick={() => void loadDashboard()}>
          Try again
        </button>
      </section>
    );
  }

  const metrics = data?.metrics;
  const current = data?.current_examination;
  const workflow = data?.workflow;
  const issues = (metrics?.validation_errors ?? 0) + (metrics?.validation_warnings ?? 0);

  const welcomeContext = current
    ? current.programme_code + " · Semester " + current.semester_number + " · " + current.term_label
    : "There is no active examination yet.";

  return (
    <>
      <section className="welcome">
        <div>
          <p className="eyebrow">
            {data?.institution.name ?? "Examination Office"}
          </p>
          <h2>What do you need to do now?</h2>
          <p>{welcomeContext}</p>
        </div>
        <button
          type="button"
          className="primary"
          onClick={() => onNavigate(actionToModule[workflow?.action ?? ""] ?? "Examinations")}
        >
          {workflow?.label ?? "Create examination"}
        </button>
      </section>

      {error ? (
        <div className="inline-notice" role="status">
          {error}
        </div>
      ) : null}

      <section className="stats">
        <div className="card">
          <span>Current Examination</span>
          <strong>{current?.name ?? "Not created yet"}</strong>
          <small>{current?.status ?? "SETUP"}</small>
        </div>
        <div className="card">
          <span>Marks Recorded</span>
          <strong>{metrics?.marks_recorded.toLocaleString() ?? "0"}</strong>
          <small>{metrics?.registered_students.toLocaleString() ?? "0"} registered students</small>
        </div>
        <div className={issues > 0 ? "card attention" : "card"}>
          <span>Issues Need Attention</span>
          <strong>{issues.toLocaleString()}</strong>
          <small>
            {(metrics?.validation_errors ?? 0).toLocaleString()} errors ·{" "}
            {(metrics?.validation_warnings ?? 0).toLocaleString()} warnings
          </small>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Current workflow</h3>
            <p>Follow the examination process without hunting through technical screens.</p>
          </div>
          {loading ? <span className="refreshing">Refreshing…</span> : null}
        </div>

        <div className="workflow-strip">
          <div className="workflow-current">
            <span>Next action</span>
            <strong>{workflow?.label ?? "Create examination"}</strong>
            {current ? (
              <small>{current.name} · {current.status}</small>
            ) : (
              <small>Set up your first examination.</small>
            )}
          </div>

          <div className="workflow-stats">
            <div>
              <span>Active examinations</span>
              <strong>{metrics?.active_examinations.toLocaleString() ?? "0"}</strong>
            </div>
            <div>
              <span>Pending review</span>
              <strong>{metrics?.pending_result_review.toLocaleString() ?? "0"}</strong>
            </div>
            <div>
              <span>Pending approval</span>
              <strong>{metrics?.pending_result_approval.toLocaleString() ?? "0"}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>Quick actions</h3>
            <p>Common tasks for the examination office.</p>
          </div>
        </div>
        <div className="actions">
          <button className="action" type="button" onClick={() => onNavigate("Examinations")}>
            Create Examination
          </button>
          <button className="action" type="button" onClick={() => onNavigate("Students")}>
            Upload Students
          </button>
          <button className="action" type="button" onClick={() => onNavigate("Marks & Results")}>
            Upload Marks
          </button>
          <button className="action" type="button" onClick={() => onNavigate("Marks & Results")}>
            Review Results
          </button>
        </div>
      </section>
    </>
  );
}

function AppShell() {
  const { session, logout } = useAuth();
  const [active, setActive] = useState("Dashboard");

  if (!session) return <LoginScreen />;

  const primaryRole = session.user.roles[0] ?? "User";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">ExamFlow <span>ERP</span></div>
        <div className="env-badge">STAGING</div>

        <nav aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              key={item}
              type="button"
              className={active === item ? "nav-item active" : "nav-item"}
              onClick={() => setActive(item)}
            >
              {item}
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          Simple examination management
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Examination Office</p>
            <h1>{active}</h1>
          </div>

          <div className="account-area">
            <div className="user-chip">
              <strong>{session.user.full_name}</strong>
              <span>{primaryRole}</span>
            </div>
            <button type="button" className="secondary-button" onClick={logout}>
              Sign out
            </button>
          </div>
        </header>

        {active === "Dashboard" ? (
          <Dashboard onNavigate={setActive} />
        ) : active === "Students" ? (
          <StudentManagement onBackToDashboard={() => setActive("Dashboard")} />
        ) : (
          <section className="panel empty">
            <h2>{active}</h2>
            <p>This module will be connected to the ExamFlow API in the next implementation step.</p>
          </section>
        )}
      </main>
    </div>
  );
}

function App() {
  const { isInitializing, isAuthenticated } = useAuth();

  if (isInitializing) return <LoadingScreen />;
  return isAuthenticated ? <AppShell /> : <LoginScreen />;
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
);
