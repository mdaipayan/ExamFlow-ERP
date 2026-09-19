import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { ApiError } from "./api/client";
import { AuthProvider, useAuth } from "./auth/AuthContext";
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

function LoadingScreen() {
  return (
    <div className="auth-page">
      <div className="loading-card">
        <div className="brand auth-brand">ExamFlow <span>ERP</span></div>
        <div className="spinner" aria-hidden="true" />
        <p>Checking your session...</p>
      </div>
    </div>
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
          <>
            <section className="welcome">
              <div>
                <h2>What do you need to do now?</h2>
                <p>Continue the current examination workflow from where you stopped.</p>
              </div>
              <button type="button" className="primary">Continue</button>
            </section>

            <section className="stats">
              <div className="card">
                <span>Active Examination</span>
                <strong>Not created yet</strong>
              </div>
              <div className="card">
                <span>Marks awaiting check</span>
                <strong>0</strong>
              </div>
              <div className="card">
                <span>Issues need attention</span>
                <strong>0</strong>
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
                {["Create Examination", "Upload Students", "Upload Marks", "Review Results"].map((label) => (
                  <button className="action" type="button" key={label}>{label}</button>
                ))}
              </div>
            </section>
          </>
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
