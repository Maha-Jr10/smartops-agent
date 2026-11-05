"use client";

import { useState } from "react";

type MonTab = "grafana" | "mlflow" | "evidently";

const _grafana  = process.env.NEXT_PUBLIC_GRAFANA_URL ?? "http://localhost:3002";
const _mlflow   = process.env.NEXT_PUBLIC_MLFLOW_URL  ?? "http://localhost:5000";
const _api      = process.env.NEXT_PUBLIC_API_URL     ?? "http://localhost:8000";

const TABS: { id: MonTab; label: string; url: string; hint: string }[] = [
  {
    id: "grafana",
    label: "Grafana",
    url: _grafana,
    hint: "Métriques live : latence P50/P95, requêtes, appels outils",
  },
  {
    id: "mlflow",
    label: "MLflow",
    url: _mlflow,
    hint: "Expériences d'évaluation, paramètres, artefacts",
  },
  {
    id: "evidently",
    label: "Evidently",
    url: `${_api}/report/drift`,
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

      {/* Placeholder — external services block iframe embedding (X-Frame-Options: SAMEORIGIN) */}
      <div className="mon-frames">
        {TABS.map(t => (
          <div
            key={t.id}
            className="mon-placeholder"
            style={{ display: active === t.id ? "flex" : "none" }}
          >
            <div className="mon-placeholder-inner">
              <div className="mon-placeholder-icon" style={{ color: TAB_COLOR[t.id] }}>
                <IconExternalLink size={32} />
              </div>
              <p className="mon-placeholder-title">{t.label}</p>
              <p className="mon-placeholder-desc">{t.hint}</p>
              <a
                href={t.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mon-placeholder-btn"
                style={{ background: TAB_COLOR[t.id] }}
              >
                <IconExternalLink size={14} />
                Ouvrir {t.label}
              </a>
            </div>
          </div>
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

        /* ── Placeholder (services block iframe embedding) ── */
        .mon-placeholder {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-page);
        }
        .mon-placeholder-inner {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 12px;
          text-align: center;
          padding: 32px;
          max-width: 360px;
        }
        .mon-placeholder-icon { opacity: 0.7; }
        .mon-placeholder-title {
          font-size: 17px;
          font-weight: 600;
          color: var(--fg-primary);
          margin: 0;
        }
        .mon-placeholder-desc {
          font-size: 13px;
          color: var(--fg-muted);
          margin: 0;
        }
        .mon-placeholder-btn {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          margin-top: 8px;
          padding: 10px 20px;
          border-radius: 8px;
          color: #fff;
          font-size: 14px;
          font-weight: 500;
          text-decoration: none;
          transition: opacity 0.15s;
        }
        .mon-placeholder-btn:hover { opacity: 0.85; }
      `}</style>
    </div>
  );
}

const TAB_COLOR: Record<MonTab, string> = {
  grafana:   "#f46800",
  mlflow:    "#0194e2",
  evidently: "#7c3aed",
};

function IconExternalLink({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/>
      <line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  );
}
