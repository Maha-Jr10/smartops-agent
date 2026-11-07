"use client";

import { useState, useEffect } from "react";
import { fetchHealth, fetchOpenRouterKeyStatus, updateOpenRouterKey, fetchModelStatus, updateModel, seedDemoData, deleteSeedData, type HealthStatus, type OpenRouterKeyStatus, type ModelStatus } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import ChatPanel from "@/components/ChatPanel";
import ApprovalsPanel from "@/components/ApprovalsPanel";
import MonitoringPanel from "@/components/MonitoringPanel";

type Tab = "chat" | "approvals" | "monitoring";

export default function Home() {
  const [tab, setTab] = useState<Tab>("chat");
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [apiDown, setApiDown] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [orStatus, setOrStatus] = useState<OpenRouterKeyStatus | null>(null);
  const [orInput, setOrInput] = useState("");
  const [orSaving, setOrSaving] = useState(false);
  const [orMsg, setOrMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [modelSelected, setModelSelected] = useState("");
  const [modelSaving, setModelSaving] = useState(false);
  const [modelMsg, setModelMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [seedLoading, setSeedLoading] = useState<"seed" | "delete" | null>(null);
  const [seedMsg, setSeedMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const { profile, role, signOut } = useAuth();
  const isAdmin = role === "admin";

  async function openSettings() {
    setOrInput("");
    setOrMsg(null);
    setModelMsg(null);
    setShowSettings(true);
    try {
      const [s, m] = await Promise.all([fetchOpenRouterKeyStatus(), fetchModelStatus()]);
      setOrStatus(s);
      setModelStatus(m);
      setModelSelected(m.current);
    } catch {
      setOrStatus(null);
      setModelStatus(null);
    }
  }

  async function saveModel() {
    if (!modelSelected) return;
    setModelSaving(true);
    setModelMsg(null);
    try {
      await updateModel(modelSelected);
      setModelMsg({ ok: true, text: "Modèle mis à jour." });
    } catch (err) {
      setModelMsg({ ok: false, text: err instanceof Error ? err.message : "Erreur inconnue" });
    } finally {
      setModelSaving(false);
    }
  }

  async function handleSeedData(action: "seed" | "delete") {
    setSeedLoading(action);
    setSeedMsg(null);
    try {
      if (action === "seed") {
        const r = await seedDemoData();
        setSeedMsg({ ok: true, text: `${r.seeded_traces} traces injectées. Rapport Evidently : ${r.report === "generated" ? "généré" : "dépendances manquantes"}.` });
      } else {
        await deleteSeedData();
        setSeedMsg({ ok: true, text: "Données de démo supprimées." });
      }
    } catch (err) {
      setSeedMsg({ ok: false, text: err instanceof Error ? err.message : "Erreur inconnue" });
    } finally {
      setSeedLoading(null);
    }
  }

  async function saveOrKey() {
    if (!orInput.trim()) return;
    setOrSaving(true);
    setOrMsg(null);
    try {
      await updateOpenRouterKey(orInput.trim());
      setOrMsg({ ok: true, text: "Clé mise à jour avec succès." });
      setOrInput("");
      const s = await fetchOpenRouterKeyStatus();
      setOrStatus(s);
    } catch (err) {
      setOrMsg({ ok: false, text: err instanceof Error ? err.message : "Erreur inconnue" });
    } finally {
      setOrSaving(false);
    }
  }

  useEffect(() => {
    const check = async () => {
      try {
        setHealth(await fetchHealth());
        setApiDown(false);
      } catch {
        setApiDown(true);
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app-shell">
      {/* ── Header ───────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-logo">SO</span>
          <div>
            <p className="brand-name">SmartOps</p>
            <p className="brand-sub">Assistant Smartara</p>
          </div>
        </div>

        {/* Desktop nav */}
        <nav className="header-nav desktop-only">
          <button
            onClick={() => setTab("chat")}
            className={`nav-item ${tab === "chat" ? "nav-active" : ""}`}
          >
            <IconChat />
            Conversation
          </button>
          <button
            onClick={() => setTab("approvals")}
            className={`nav-item ${tab === "approvals" ? "nav-active" : ""}`}
          >
            <IconApproval />
            Approbations
          </button>
          {isAdmin && (
            <button
              onClick={() => setTab("monitoring")}
              className={`nav-item ${tab === "monitoring" ? "nav-active" : ""}`}
            >
              <IconMonitoring />
              Monitoring
            </button>
          )}
        </nav>

        <div className="header-status">
          <span className={`status-dot ${apiDown ? "dot-down" : "dot-up"}`} />
          <span className="status-label">
            {apiDown ? "Hors ligne" : health ? `v${health.version}` : "…"}
          </span>
          {health && !apiDown && (
            <span className="status-env">{health.env}</span>
          )}
          {profile && (
            <>
              <span className="user-name">{profile.display_name || profile.email}</span>
              {isAdmin && (
                <button className="signout-btn" onClick={openSettings} title="Paramètres admin">
                  <IconGear />
                </button>
              )}
              <button className="signout-btn" onClick={signOut} title="Déconnexion">
                <IconSignOut />
              </button>
            </>
          )}
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────────── */}
      <main className="app-body">
        {tab === "chat" ? <ChatPanel /> : tab === "approvals" ? <ApprovalsPanel /> : <MonitoringPanel />}
      </main>

      {/* ── Mobile bottom nav ────────────────────────────────── */}
      <nav className="mobile-nav mobile-only">
        <button
          onClick={() => setTab("chat")}
          className={`mobile-tab ${tab === "chat" ? "mobile-tab-active" : ""}`}
        >
          <IconChat />
          <span>Chat</span>
        </button>
        <button
          onClick={() => setTab("approvals")}
          className={`mobile-tab ${tab === "approvals" ? "mobile-tab-active" : ""}`}
        >
          <IconApproval />
          <span>Approbations</span>
        </button>
        {isAdmin && (
          <button
            onClick={() => setTab("monitoring")}
            className={`mobile-tab ${tab === "monitoring" ? "mobile-tab-active" : ""}`}
          >
            <IconMonitoring />
            <span>Monitoring</span>
          </button>
        )}
      </nav>

      {/* ── Admin settings modal ─────────────────────────────── */}
      {showSettings && (
        <div className="modal-backdrop" onClick={() => setShowSettings(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">Paramètres admin</span>
              <button className="modal-close" onClick={() => setShowSettings(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p className="modal-label">Modèle OpenRouter</p>
              {modelStatus ? (
                <select
                  className="modal-select"
                  value={modelSelected}
                  onChange={e => { setModelSelected(e.target.value); setModelMsg(null); }}
                >
                  {modelStatus.models.map(m => (
                    <option key={m.id} value={m.id}>{m.label}</option>
                  ))}
                </select>
              ) : (
                <p className="modal-status">Chargement…</p>
              )}
              {modelMsg && (
                <p className={`modal-msg ${modelMsg.ok ? "msg-ok" : "msg-err"}`}>{modelMsg.text}</p>
              )}
              <div className="modal-actions" style={{ marginBottom: 8 }}>
                <button
                  className="btn-primary"
                  onClick={saveModel}
                  disabled={!modelSelected || modelSaving || modelSelected === modelStatus?.current}
                >
                  {modelSaving ? "Enregistrement…" : "Appliquer le modèle"}
                </button>
              </div>

              <hr className="modal-sep" />

              <p className="modal-label">Clé API OpenRouter</p>
              {orStatus && (
                <p className="modal-status">
                  {orStatus.has_key === "true"
                    ? <>Clé active : <code>{orStatus.masked}</code></>
                    : "Aucune clé configurée"}
                </p>
              )}
              <input
                className="modal-input"
                type="password"
                placeholder="sk-or-..."
                value={orInput}
                onChange={e => setOrInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") saveOrKey(); }}
              />
              {orMsg && (
                <p className={`modal-msg ${orMsg.ok ? "msg-ok" : "msg-err"}`}>{orMsg.text}</p>
              )}
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setShowSettings(false)}>Fermer</button>
                <button className="btn-primary" onClick={saveOrKey} disabled={!orInput.trim() || orSaving}>
                  {orSaving ? "Enregistrement…" : "Mettre à jour la clé"}
                </button>
              </div>

              <hr className="modal-sep" />

              <p className="modal-label">Données de démonstration</p>
              <p className="modal-status">Injecte des traces fictives pour alimenter le rapport Evidently et les métriques Grafana.</p>
              {seedMsg && (
                <p className={`modal-msg ${seedMsg.ok ? "msg-ok" : "msg-err"}`}>{seedMsg.text}</p>
              )}
              <div className="modal-actions">
                <button
                  className="btn-secondary"
                  onClick={() => handleSeedData("delete")}
                  disabled={seedLoading !== null}
                >
                  {seedLoading === "delete" ? "Suppression…" : "Supprimer"}
                </button>
                <button
                  className="btn-primary"
                  onClick={() => handleSeedData("seed")}
                  disabled={seedLoading !== null}
                >
                  {seedLoading === "seed" ? "Injection…" : "Injecter données démo"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        /* ── Layout ──────────────────────────────────── */
        .app-shell {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: var(--bg-page);
        }
        .app-header {
          display: flex;
          align-items: center;
          gap: 24px;
          height: 56px;
          padding-inline: max(16px, env(safe-area-inset-left, 0px)) max(16px, env(safe-area-inset-right, 0px));
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          position: sticky;
          top: env(safe-area-inset-top, 0px);
          z-index: 20;
          flex-shrink: 0;
        }
        .app-body {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        /* ── Brand ───────────────────────────────────── */
        .header-brand {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
        }
        .brand-logo {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: var(--accent);
          color: #fff;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.04em;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .brand-name {
          font-size: 14px;
          font-weight: 600;
          color: var(--fg-primary);
          line-height: 1.2;
        }
        .brand-sub {
          font-size: 11px;
          color: var(--fg-muted);
          line-height: 1.2;
        }

        /* ── Header nav (desktop) ────────────────────── */
        .header-nav {
          display: flex;
          align-items: center;
          gap: 2px;
          flex: 1;
        }
        .nav-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 7px;
          font-size: 13px;
          font-weight: 500;
          color: var(--fg-secondary);
          background: none;
          border: none;
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
        }
        .nav-item:hover { background: var(--bg-hover); color: var(--fg-primary); }
        .nav-active {
          background: var(--accent-subtle) !important;
          color: var(--accent) !important;
        }

        /* ── Status ──────────────────────────────────── */
        .header-status {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-shrink: 0;
          margin-left: auto;
        }
        .status-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .dot-up { background: #10b981; }
        .dot-down { background: #ef4444; }
        .status-label {
          font-size: 12px;
          color: var(--fg-secondary);
          font-variant-numeric: tabular-nums;
        }
        .status-env {
          font-size: 11px;
          color: var(--fg-muted);
          background: var(--bg-hover);
          padding: 2px 7px;
          border-radius: 4px;
        }

        /* ── Mobile nav ──────────────────────────────── */
        .mobile-nav {
          display: flex;
          border-top: 1px solid var(--border);
          background: var(--bg-surface);
          flex-shrink: 0;
          padding-bottom: max(0px, env(safe-area-inset-bottom, 0px));
        }
        .mobile-tab {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 3px;
          padding: 10px 0;
          font-size: 11px;
          font-weight: 500;
          color: var(--fg-muted);
          background: none;
          border: none;
          cursor: pointer;
        }
        .mobile-tab-active { color: var(--accent); }

        /* ── Admin settings modal ───────────────────────── */
        .modal-backdrop {
          position: fixed; inset: 0; z-index: 100;
          background: rgba(0,0,0,.45);
          display: flex; align-items: center; justify-content: center;
          padding: 16px;
        }
        .modal-box {
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: 14px;
          width: 100%; max-width: 420px;
          box-shadow: 0 20px 60px rgba(0,0,0,.25);
        }
        .modal-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 16px 20px 0;
        }
        .modal-title { font-size: 15px; font-weight: 600; color: var(--fg-primary); }
        .modal-close {
          background: none; border: none; cursor: pointer;
          color: var(--fg-muted); font-size: 16px; padding: 4px;
          border-radius: 6px; line-height: 1;
        }
        .modal-close:hover { background: var(--bg-hover); color: var(--fg-primary); }
        .modal-body { padding: 16px 20px 20px; display: flex; flex-direction: column; gap: 10px; }
        .modal-label { font-size: 12px; font-weight: 500; color: var(--fg-secondary); }
        .modal-status { font-size: 12px; color: var(--fg-muted); }
        .modal-status code { font-family: monospace; color: var(--fg-secondary); }
        .source-tag {
          font-size: 10px; padding: 1px 6px; border-radius: 4px;
          background: var(--bg-hover); color: var(--fg-muted);
        }
        .modal-sep { border: none; border-top: 1px solid var(--border); margin: 4px 0 8px; }
        .modal-select {
          width: 100%; padding: 9px 12px; border-radius: 8px;
          border: 1px solid var(--border); background: var(--bg-input);
          color: var(--fg-primary); font-size: 13px;
          box-sizing: border-box; cursor: pointer;
        }
        .modal-select:focus { outline: none; border-color: var(--border-focus); }
        .modal-input {
          width: 100%; padding: 9px 12px; border-radius: 8px;
          border: 1px solid var(--border); background: var(--bg-input);
          color: var(--fg-primary); font-size: 13px; font-family: monospace;
          box-sizing: border-box;
        }
        .modal-input:focus { outline: none; border-color: var(--border-focus); }
        .modal-msg { font-size: 12px; }
        .msg-ok { color: #10b981; }
        .msg-err { color: #ef4444; }
        .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 4px; }
        .btn-secondary {
          padding: 7px 14px; border-radius: 8px; font-size: 13px;
          border: 1px solid var(--border); background: none;
          color: var(--fg-secondary); cursor: pointer;
        }
        .btn-secondary:hover { background: var(--bg-hover); }
        .btn-primary {
          padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 500;
          border: none; background: var(--accent); color: #fff; cursor: pointer;
        }
        .btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
        .btn-primary:disabled { opacity: .5; cursor: default; }

        /* ── User / sign-out ─────────────────────────── */
        .user-name {
          font-size: 12px;
          color: var(--fg-secondary);
          max-width: 120px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .signout-btn {
          background: none;
          border: none;
          cursor: pointer;
          color: var(--fg-muted);
          display: flex;
          align-items: center;
          padding: 4px;
          border-radius: 5px;
          transition: color .15s, background .15s;
        }
        .signout-btn:hover { color: var(--fg-primary); background: var(--bg-hover); }

        /* ── Visibility helpers ──────────────────────── */
        .desktop-only { display: flex; }
        .mobile-only  { display: none; }
        @media (max-width: 639px) {
          .desktop-only { display: none; }
          .mobile-only  { display: flex; }
          /* Slim the header down — hide verbose text, keep icons */
          .brand-sub  { display: none; }
          .user-name  { display: none; }
          .status-env { display: none; }
          .header-status { margin-left: auto; gap: 4px; }
          .app-header { gap: 10px; }
          /* Smaller bottom-nav labels so 3 tabs fit */
          .mobile-tab { font-size: 10px; padding: 8px 0; gap: 2px; }
        }
      `}</style>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────── */
function IconChat() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
function IconApproval() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}
function IconMonitoring() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}
function IconSignOut() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
function IconGear() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
