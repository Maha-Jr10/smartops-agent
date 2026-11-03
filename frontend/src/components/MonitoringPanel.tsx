"use client";

import { useState } from "react";

type MonTab = "grafana" | "mlflow" | "evidently";

const TABS: { id: MonTab; label: string; url: string; hint: string }[] = [
  {
    id: "grafana",
    label: "Grafana",
    url: "http://localhost:3002",
    hint: "Métriques live : latence P50/P95, requêtes, appels outils",
  },
  {
    id: "mlflow",
    label: "MLflow",
    url: "http://localhost:5000",
    hint: "Expériences d'évaluation, paramètres, artefacts",
  },
  {
    id: "evidently",
    label: "Evidently",
    url: "http://localhost:8000/report/drift",
    hint: "Rapport de dérive des données (traces JSONL)",
  },
];

export default function MonitoringPanel() {
  const [active, setActive] = useState<MonTab>("grafana");
  const tab = TABS.find(t => t.id === active)!;

  return (
    <div className="mon-shell">
      {/* Sub-tab bar */}
      <div className="mon-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setActive(t.id)}
            className={`mon-tab ${active === t.id ? "mon-tab-active" : ""}`}
          >
            <span className="mon-tab-dot" style={{ background: TAB_COLOR[t.id] }} />
            {t.label}
          </button>
        ))}
        <a
          href={tab.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mon-open-btn"
          title={`Ouvrir ${tab.label} dans un nouvel onglet`}
        >
          <IconExternalLink />
          <span>Ouvrir</span>
        </a>
      </div>

      {/* Hint */}
      <div className="mon-hint">{tab.hint}</div>

      {/* iframes — one per service, shown/hidden to preserve state */}
      <div className="mon-frames">
        {TABS.map(t => (
          <iframe
            key={t.id}
            src={t.url}
            className={`mon-iframe ${active === t.id ? "mon-iframe-visible" : "mon-iframe-hidden"}`}
            title={t.label}
            allow="fullscreen"
          />
        ))}
      </div>

      <style>{`
        .mon-shell {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: var(--bg-page);
        }

        /* ── Sub-tabs ─────────────────────────────────────── */
        .mon-tabs {
          display: flex;
          align-items: center;
          gap: 2px;
          padding: 8px max(16px, env(safe-area-inset-left, 0px));
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }
        .mon-tab {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 6px 14px;
          border-radius: 7px;
          font-size: 13px;
          font-weight: 500;
          color: var(--fg-secondary);
          background: none;
          border: none;
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
        }
        .mon-tab:hover { background: var(--bg-hover); color: var(--fg-primary); }
        .mon-tab-active {
          background: var(--accent-subtle);
          color: var(--accent);
        }
        .mon-tab-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .mon-open-btn {
          margin-left: auto;
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 5px 12px;
          border-radius: 7px;
          border: 1px solid var(--border);
          background: var(--bg-input);
          color: var(--fg-secondary);
          font-size: 12px;
          text-decoration: none;
          transition: background 0.15s, color 0.15s;
          flex-shrink: 0;
        }
        .mon-open-btn:hover { background: var(--bg-hover); color: var(--fg-primary); }

        /* ── Hint ─────────────────────────────────────────── */
        .mon-hint {
          padding: 6px max(16px, env(safe-area-inset-left, 0px));
          font-size: 12px;
          color: var(--fg-muted);
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }

        /* ── iframes ──────────────────────────────────────── */
        .mon-frames {
          flex: 1;
          position: relative;
          overflow: hidden;
        }
        .mon-iframe {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          border: none;
          background: var(--bg-page);
        }
        .mon-iframe-visible { display: block; }
        .mon-iframe-hidden  { display: none; }
      `}</style>
    </div>
  );
}

const TAB_COLOR: Record<MonTab, string> = {
  grafana:   "#f46800",
  mlflow:    "#0194e2",
  evidently: "#7c3aed",
};

function IconExternalLink() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/>
      <line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  );
}
