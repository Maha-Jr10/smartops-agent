"use client";

import { useEffect, useState } from "react";
import { fetchDriftReport, fetchMonitoringStatus, type MonitoringStatus } from "@/lib/api";

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
  const [monStatus, setMonStatus] = useState<MonitoringStatus | null>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [driftBlobUrl, setDriftBlobUrl] = useState<string | null>(null);
  const [driftFetched, setDriftFetched] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const s = await fetchMonitoringStatus();
        if (!cancelled) setMonStatus(s);
      } catch { /* silent — panel still works without status */ }
    }
    poll();
    const id = setInterval(poll, 60_000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (active !== "evidently" || driftFetched) return;
    let cancelled = false;
    setDriftLoading(true);
    fetchDriftReport().then(html => {
      if (cancelled) return;
      setDriftFetched(true);
      setDriftLoading(false);
      if (html) {
        const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
        setDriftBlobUrl(prev => { if (prev) URL.revokeObjectURL(prev); return url; });
      }
    }).catch(() => { if (!cancelled) { setDriftFetched(true); setDriftLoading(false); } });
    return () => { cancelled = true; };
  }, [active, driftFetched]);

  return (
    <div className="mon-shell">
      {/* Drift alert banner */}
      {monStatus?.status === "drift_detected" && (
        <div className="mon-alert">
          <IconAlert />
          <span>
            <strong>Dérive détectée</strong>
            {monStatus.drifted_columns && monStatus.drifted_columns.length > 0
              ? ` — colonnes : ${monStatus.drifted_columns.join(", ")}`
              : ""}
            {monStatus.last_run ? ` (${new Date(monStatus.last_run).toLocaleString("fr-FR")})` : ""}
          </span>
          <button
            onClick={() => setActive("evidently")}
            className="mon-alert-link"
            style={{ background: "none", border: "none", cursor: "pointer" }}
          >
            Voir rapport
          </button>
        </div>
      )}

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

      {/* Frames */}
      <div className="mon-frames">
        {/* Evidently — served as a blob URL to bypass auth requirement */}
        <div style={{ display: active === "evidently" ? "flex" : "none", position: "absolute", inset: 0, flexDirection: "column" }}>
          {driftLoading && (
            <div className="mon-placeholder" style={{ position: "absolute", inset: 0 }}>
              <div className="mon-placeholder-inner">
                <p className="mon-placeholder-desc">Chargement du rapport…</p>
              </div>
            </div>
          )}
          {!driftLoading && driftFetched && !driftBlobUrl && (
            <div className="mon-placeholder" style={{ position: "absolute", inset: 0 }}>
              <div className="mon-placeholder-inner">
                <div className="mon-placeholder-icon" style={{ color: TAB_COLOR.evidently }}><IconExternalLink size={32} /></div>
                <p className="mon-placeholder-title">Evidently</p>
                <p className="mon-placeholder-desc">Rapport non disponible. Injectez des données de démonstration depuis les paramètres admin.</p>
              </div>
            </div>
          )}
          {driftBlobUrl && (
            <iframe
              key={driftBlobUrl}
              src={driftBlobUrl}
              sandbox="allow-scripts"
              className="mon-iframe mon-iframe-visible"
              title="Rapport de dérive Evidently"
            />
          )}
        </div>

        {/* Grafana and MLflow — placeholder (X-Frame-Options: SAMEORIGIN blocks iframe) */}
        {(["grafana", "mlflow"] as MonTab[]).map(t => (
          <div
            key={t}
            className="mon-placeholder"
            style={{ display: active === t ? "flex" : "none" }}
          >
            <div className="mon-placeholder-inner">
              <div className="mon-placeholder-icon" style={{ color: TAB_COLOR[t] }}>
                <IconExternalLink size={32} />
              </div>
              <p className="mon-placeholder-title">{TABS.find(x => x.id === t)!.label}</p>
              <p className="mon-placeholder-desc">{TABS.find(x => x.id === t)!.hint}</p>
              <a
                href={TABS.find(x => x.id === t)!.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mon-placeholder-btn"
                style={{ background: TAB_COLOR[t] }}
              >
                <IconExternalLink size={14} />
                Ouvrir {TABS.find(x => x.id === t)!.label}
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

        /* ── Drift alert banner ───────────────────────────── */
        .mon-alert {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 9px max(16px, env(safe-area-inset-left, 0px));
          background: #fef3c7;
          border-bottom: 1px solid #f59e0b;
          color: #92400e;
          font-size: 13px;
          flex-shrink: 0;
        }
        @media (prefers-color-scheme: dark) {
          .mon-alert { background: #451a03; border-color: #b45309; color: #fcd34d; }
        }
        .mon-alert-link {
          margin-left: auto;
          font-size: 12px;
          font-weight: 600;
          color: inherit;
          text-decoration: underline;
          white-space: nowrap;
        }
      `}</style>
    </div>
  );
}

const TAB_COLOR: Record<MonTab, string> = {
  grafana:   "#f46800",
  mlflow:    "#0194e2",
  evidently: "#7c3aed",
};

function IconAlert() {
  return (
    <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  );
}

function IconExternalLink({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      <polyline points="15 3 21 3 21 9"/>
      <line x1="10" y1="14" x2="21" y2="3"/>
    </svg>
  );
}
