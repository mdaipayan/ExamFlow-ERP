import React, { useState } from "react";
import { createRoot } from "react-dom/client";
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

function App() {
  const [active, setActive] = useState("Dashboard");

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">ExamFlow <span>ERP</span></div>
        <div className="env-badge">STAGING</div>
        <nav>
          {navItems.map((item) => (
            <button
              key={item}
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
          <div className="user-chip">Demo User</div>
        </header>

        {active === "Dashboard" ? (
          <>
            <section className="welcome">
              <div>
                <h2>What do you need to do now?</h2>
                <p>Continue the current examination workflow from where you stopped.</p>
              </div>
              <button className="primary">Continue</button>
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
                  <button className="action" key={label}>{label}</button>
                ))}
              </div>
            </section>
          </>
        ) : (
          <section className="panel empty">
            <h2>{active}</h2>
            <p>This module will be built next. The navigation shell is intentionally kept simple.</p>
          </section>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
