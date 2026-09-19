import React from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 960, margin: "40px auto", padding: 24 }}>
      <h1>ExamFlow ERP</h1>
      <p>Simple Examination Management for Every Institution</p>
      <p>Foundation MVP</p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
