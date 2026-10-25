import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// Apply the saved or OS theme before the first render (inline scripts are blocked by the CSP).
try {
  const saved = localStorage.getItem("hea.theme");
  document.documentElement.dataset.theme = saved === "light" || saved === "dark" ? saved
    : matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
} catch { document.documentElement.dataset.theme = "dark"; }

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
