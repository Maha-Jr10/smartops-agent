"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchApprovals, decideApproval, type Approval } from "@/lib/api";

type Filter = "pending" | "all";

const STATUS_CONFIG = {
  pending:  { label: "En attente", bg: "#fef3c7", fg: "#b45309" },
  approved: { label: "Approuvé",   bg: "#d1fae5", fg: "#065f46" },
  rejected: { label: "Rejeté",     bg: "#fee2e2", fg: "#991b1b" },
};

export default function ApprovalsPanel() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [filter, setFilter]       = useState<Filter>("pending");
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchApprovals();
      setApprovals(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, [load]);

  const filtered = approvals.filter(a =>
    filter === "all" ? true : a.status === "pending"
  );
  const pendingCount = approvals.filter(a => a.status === "pending").length;

  return (
    <div className="ap-shell">

      {/* ── Header bar ──────────────────────────────────────── */}
      <div className="ap-bar">
        <div className="ap-bar-left">
          <h2 className="ap-title">File d'approbation</h2>
          {pendingCount > 0 && (
            <span className="ap-badge">{pendingCount}</span>
          )}
        </div>
        <div className="ap-bar-right">
          <div className="filter-tabs">
            <button
              className={`filter-tab ${filter === "pending" ? "filter-active" : ""}`}
              onClick={() => setFilter("pending")}
            >
              En attente
            </button>
            <button
              className={`filter-tab ${filter === "all" ? "filter-active" : ""}`}
              onClick={() => setFilter("all")}
            >
              Tout
            </button>
          </div>
          <button className="refresh-btn" onClick={load} title="Rafraîchir">
            <IconRefresh />
          </button>
        </div>
      </div>

      {/* ── Content ──────────────────────────────────────────── */}
      <div className="ap-content">
        {loading ? (
          <div className="ap-loading">
            <svg className="ap-spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
            <span>Chargement…</span>
          </div>
        ) : error ? (
          <div className="ap-error">
            <IconAlert />
            <p>{error}</p>
            <button className="retry-btn" onClick={load}>Réessayer</button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="ap-empty">
            <div className="ap-empty-icon">
              <IconInbox />
            </div>
            <p className="ap-empty-title">
              {filter === "pending" ? "Aucune demande en attente" : "Aucune demande"}
            </p>
            <p className="ap-empty-sub">
              Les actions à valider apparaîtront ici en temps réel.
            </p>
          </div>
        ) : (
          <div className="ap-list">
            {filtered.map(a => (
              <ApprovalCard key={a.request_id} approval={a} onDecision={load} />
            ))}
          </div>
        )}
      </div>

      <style>{`
        .ap-shell {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: var(--bg-page);
        }
        .ap-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 12px max(16px, env(safe-area-inset-left, 0px));
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
          flex-wrap: wrap;
        }
        .ap-bar-left { display: flex; align-items: center; gap: 8px; }
        .ap-bar-right { display: flex; align-items: center; gap: 8px; }
        .ap-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--fg-primary);
          margin: 0;
          font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .ap-badge {
          min-width: 20px;
          height: 20px;
          padding: 0 6px;
          border-radius: 10px;
          background: var(--danger);
          color: #fff;
          font-size: 11px;
          font-weight: 600;
          display: flex;
          align-items: center;
          justify-content: center;
          font-variant-numeric: tabular-nums;
        }
        .filter-tabs {
          display: flex;
          background: var(--bg-hover);
          border-radius: 8px;
          padding: 2px;
          gap: 2px;
        }
        .filter-tab {
          padding: 4px 12px;
          border-radius: 6px;
          border: none;
          background: none;
          font-size: 12px;
          font-weight: 500;
          color: var(--fg-secondary);
          cursor: pointer;
          transition: all 0.15s;
        }
        .filter-active {
          background: var(--bg-surface);
          color: var(--fg-primary);
          box-shadow: 0 1px 3px rgba(0,0,0,.08);
        }
        .refresh-btn {
          width: 30px;
          height: 30px;
          border-radius: 8px;
          border: 1px solid var(--border);
          background: var(--bg-surface);
          color: var(--fg-secondary);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: background 0.15s;
        }
        .refresh-btn:hover { background: var(--bg-hover); }

        .ap-content {
          flex: 1;
          overflow-y: auto;
          padding: 20px max(16px, env(safe-area-inset-left, 0px));
        }
        .ap-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-width: 760px;
          margin: 0 auto;
        }
        .ap-loading, .ap-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 48px 16px;
          color: var(--fg-muted);
          font-size: 13px;
          text-align: center;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .ap-spinner { animation: spin 0.7s linear infinite; }
        .retry-btn {
          margin-top: 4px;
          padding: 6px 16px;
          border-radius: 8px;
          border: 1px solid var(--border);
          background: var(--bg-surface);
          color: var(--fg-secondary);
          font-size: 12px;
          cursor: pointer;
        }
        .retry-btn:hover { background: var(--bg-hover); }

        .ap-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 10px;
          padding: 64px 16px;
          text-align: center;
        }
        .ap-empty-icon {
          width: 48px; height: 48px; border-radius: 12px;
          background: var(--bg-surface);
          border: 1px solid var(--border);
          display: flex; align-items: center; justify-content: center;
          color: var(--fg-muted);
          margin-bottom: 4px;
        }
        .ap-empty-title {
          font-size: 15px;
          font-weight: 600;
          color: var(--fg-primary);
          font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .ap-empty-sub {
          font-size: 13px;
          color: var(--fg-muted);
          max-width: 300px;
          line-height: 1.6;
        }
      `}</style>
    </div>
  );
}

/* ── Approval card ──────────────────────────────────────────── */
function ApprovalCard({ approval, onDecision }: { approval: Approval; onDecision: () => void }) {
  const [deciding, setDeciding]   = useState(false);
  const [comment, setComment]     = useState("");
  const [showReject, setShowReject] = useState(false);
  const [busy, setBusy]           = useState(false);

  const config = STATUS_CONFIG[approval.status as keyof typeof STATUS_CONFIG] ?? STATUS_CONFIG.pending;
  const isPending = approval.status === "pending";

  const createdAt = new Date(approval.created_at);
  const dateStr   = createdAt.toLocaleString("fr-FR", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  });

  async function decide(decision: "approved" | "rejected") {
    setBusy(true);
    try {
      await decideApproval(approval.request_id, decision, comment);
      onDecision();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
      setDeciding(false);
    }
  }

  return (
    <div className="card">
      {/* Card header */}
      <div className="card-header">
        <div className="card-header-left">
          <span className="card-action">{approval.action}</span>
          <span
            className="card-status"
            style={{ background: config.bg, color: config.fg }}
          >
            {config.label}
          </span>
        </div>
        <span className="card-time">{dateStr}</span>
      </div>

      {/* Details */}
      <div className="card-details">
        <DetailsView action={approval.action} details={approval.details} reason={approval.reason} />
      </div>

      {/* Footer */}
      <div className="card-footer">
        <div className="card-meta">
          <span className="meta-label">Demandé par</span>
          <span className="meta-val">{approval.requested_by}</span>
          <span className="meta-sep">·</span>
          <span className="meta-badge">{approval.role}</span>
          <span className="meta-sep">·</span>
          <span className="meta-id" title={approval.request_id ?? ""}>
            #{(approval.request_id ?? "").slice(0, 8)}
          </span>
        </div>

        {isPending && !deciding && (
          <div className="card-actions">
            <button
              className="action-btn action-reject"
              onClick={() => { setDeciding(true); setShowReject(true); }}
              disabled={busy}
            >
              <IconX />
              Rejeter
            </button>
            <button
              className="action-btn action-approve"
              onClick={() => decide("approved")}
              disabled={busy}
            >
              {busy ? <IconSpinnerSm /> : <IconCheck />}
              Approuver
            </button>
          </div>
        )}
      </div>

      {/* Reject comment */}
      {deciding && showReject && (
        <div className="reject-area">
          <textarea
            className="reject-input"
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Motif du rejet (optionnel)…"
            rows={2}
          />
          <div className="reject-actions">
            <button
              className="action-btn action-ghost"
              onClick={() => { setDeciding(false); setShowReject(false); setComment(""); }}
              disabled={busy}
            >
              Annuler
            </button>
            <button
              className="action-btn action-reject-confirm"
              onClick={() => decide("rejected")}
              disabled={busy}
            >
              {busy ? <IconSpinnerSm /> : <IconX />}
              Confirmer le rejet
            </button>
          </div>
        </div>
      )}

      <style>{`
        .card {
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0,0,0,.05);
          transition: box-shadow 0.15s;
        }
        .card:hover { box-shadow: 0 3px 8px rgba(0,0,0,.08); }

        .card-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border);
          gap: 8px;
          flex-wrap: wrap;
        }
        .card-header-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .card-action {
          font-size: 13px;
          font-weight: 600;
          color: var(--fg-primary);
          font-family: monospace;
        }
        .card-status {
          font-size: 11px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 20px;
          letter-spacing: 0.02em;
        }
        .card-time {
          font-size: 11px;
          color: var(--fg-muted);
          font-variant-numeric: tabular-nums;
          flex-shrink: 0;
        }

        .card-details {
          padding: 12px 16px;
          background: var(--bg-input);
          border-bottom: 1px solid var(--border);
          overflow-x: auto;
        }
        .details-pre {
          margin: 0;
          font-family: 'Menlo', 'Consolas', monospace;
          font-size: 12px;
          color: var(--fg-secondary);
          line-height: 1.6;
          white-space: pre;
          min-width: 0;
        }

        .card-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 10px 16px;
          gap: 12px;
          flex-wrap: wrap;
        }
        .card-meta {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
          min-width: 0;
        }
        .meta-label { font-size: 11px; color: var(--fg-muted); }
        .meta-val   { font-size: 12px; font-weight: 500; color: var(--fg-secondary); }
        .meta-sep   { color: var(--border); font-size: 12px; }
        .meta-badge {
          font-size: 11px;
          padding: 1px 7px;
          border-radius: 4px;
          background: var(--accent-subtle);
          color: var(--accent-text);
          font-weight: 500;
        }
        .meta-id { font-size: 11px; color: var(--fg-muted); font-family: monospace; }

        .card-actions { display: flex; gap: 8px; }
        .action-btn {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 6px 14px;
          border-radius: 8px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          border: 1px solid;
          transition: all 0.15s;
        }
        .action-btn:disabled { opacity: 0.5; cursor: default; }
        .action-approve {
          background: #d1fae5;
          border-color: #34d399;
          color: #065f46;
        }
        .action-approve:hover:not(:disabled) { background: #a7f3d0; }
        .action-reject {
          background: var(--bg-surface);
          border-color: var(--border);
          color: var(--fg-secondary);
        }
        .action-reject:hover:not(:disabled) { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }
        .action-reject-confirm {
          background: #fee2e2;
          border-color: #fca5a5;
          color: #991b1b;
        }
        .action-reject-confirm:hover:not(:disabled) { background: #fecaca; }
        .action-ghost {
          background: none;
          border-color: var(--border);
          color: var(--fg-secondary);
        }
        .action-ghost:hover:not(:disabled) { background: var(--bg-hover); }

        .reject-area {
          padding: 12px 16px;
          border-top: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          gap: 10px;
          background: #fef9f9;
        }
        @media (prefers-color-scheme: dark) {
          .reject-area { background: #1f1515; }
        }
        :root[data-theme="dark"] .reject-area { background: #1f1515; }
        .reject-input {
          width: 100%;
          padding: 8px 12px;
          border-radius: 8px;
          border: 1px solid var(--border);
          background: var(--bg-surface);
          color: var(--fg-primary);
          font-family: inherit;
          font-size: 13px;
          resize: vertical;
        }
        .reject-input:focus { outline: none; border-color: var(--border-focus); }
        .reject-actions { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }

        @keyframes spin { to { transform: rotate(360deg); } }
        .spin-sm { animation: spin 0.7s linear infinite; }
      `}</style>
    </div>
  );
}

/* ── Details renderer ──────────────────────────────────────── */
function DetailsView({
  action,
  details,
  reason,
}: {
  action: string;
  details: Record<string, unknown>;
  reason?: string;
}) {
  if (action === "send_email") {
    const { lead_id, subject, body } = details as {
      lead_id?: string;
      subject?: string;
      body?: string;
    };
    return (
      <div className="email-view">
        {reason && <p className="email-reason">{reason}</p>}
        <div className="email-fields">
          <div className="email-row">
            <span className="email-label">Destinataire</span>
            <span className="email-val">{lead_id ?? "—"}</span>
          </div>
          <div className="email-row">
            <span className="email-label">Objet</span>
            <span className="email-val">{subject ?? "—"}</span>
          </div>
        </div>
        <pre className="email-body">{body ?? ""}</pre>
        <style>{`
          .email-view { display: flex; flex-direction: column; gap: 8px; }
          .email-reason {
            margin: 0;
            font-size: 12px;
            color: var(--fg-muted);
            font-style: italic;
            padding-bottom: 4px;
            border-bottom: 1px solid var(--border);
          }
          .email-fields { display: flex; flex-direction: column; gap: 4px; }
          .email-row { display: flex; gap: 8px; align-items: baseline; }
          .email-label {
            font-size: 11px;
            font-weight: 600;
            color: var(--fg-muted);
            min-width: 80px;
            flex-shrink: 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
          }
          .email-val {
            font-size: 12px;
            color: var(--fg-secondary);
            font-family: 'Menlo', 'Consolas', monospace;
          }
          .email-body {
            margin: 4px 0 0;
            padding: 10px 12px;
            background: var(--bg-page);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: inherit;
            font-size: 12px;
            color: var(--fg-secondary);
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
          }
        `}</style>
      </div>
    );
  }
  return (
    <div>
      {reason && <p style={{ margin: "0 0 8px", fontSize: 12, color: "var(--fg-muted)", fontStyle: "italic" }}>{reason}</p>}
      <pre className="details-pre">{JSON.stringify(details, null, 2)}</pre>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────── */
function IconRefresh() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
    </svg>
  );
}
function IconCheck() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}
function IconX() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}
function IconAlert() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
    </svg>
  );
}
function IconInbox() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
      <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
    </svg>
  );
}
function IconSpinnerSm() {
  return (
    <svg className="spin-sm" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
  );
}
