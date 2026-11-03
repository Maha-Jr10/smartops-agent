"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

type Mode = "signin" | "signup";

export default function LoginPage() {
  const { signIn, signUp, loading } = useAuth();
  const router = useRouter();

  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setBusy(true);
    try {
      if (mode === "signin") {
        const err = await signIn(email, password);
        if (err) { setError(err); return; }
        router.push("/");
      } else {
        const err = await signUp(email, password, displayName);
        if (err) { setError(err); return; }
        setInfo("Compte créé. Vérifiez votre email pour confirmer, puis connectez-vous.");
        setMode("signin");
      }
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="login-brand">
          <span className="brand-logo">SO</span>
          <p className="brand-name">SmartOps</p>
          <p className="brand-sub">Assistant Smartara</p>
        </div>

        <div className="login-tabs">
          <button
            className={`login-tab ${mode === "signin" ? "login-tab-active" : ""}`}
            onClick={() => { setMode("signin"); setError(null); setInfo(null); }}
          >
            Connexion
          </button>
          <button
            className={`login-tab ${mode === "signup" ? "login-tab-active" : ""}`}
            onClick={() => { setMode("signup"); setError(null); setInfo(null); }}
          >
            Créer un compte
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          {mode === "signup" && (
            <div className="field">
              <label className="field-label">Nom complet</label>
              <input
                className="field-input"
                type="text"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="Jean Dupont"
                required
                autoComplete="name"
              />
            </div>
          )}
          <div className="field">
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="vous@smartara.example"
              required
              autoComplete="email"
            />
          </div>
          <div className="field">
            <label className="field-label">Mot de passe</label>
            <input
              className="field-input"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={mode === "signup" ? "8 caractères minimum" : ""}
              required
              minLength={mode === "signup" ? 8 : undefined}
              autoComplete={mode === "signin" ? "current-password" : "new-password"}
            />
          </div>

          {error && <p className="login-error">{error}</p>}
          {info  && <p className="login-info">{info}</p>}

          <button className="login-submit" type="submit" disabled={busy}>
            {busy ? "…" : mode === "signin" ? "Se connecter" : "Créer le compte"}
          </button>
        </form>

        <p className="login-note">
          Accès réservé aux membres de l&apos;équipe Smartara.
        </p>
      </div>

      <style>{`
        .login-shell {
          min-height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 24px 16px;
          background: var(--bg-page);
        }
        .login-card {
          width: 100%;
          max-width: 380px;
          background: var(--bg-surface);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 32px 28px;
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .login-brand {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }
        .brand-logo {
          width: 48px; height: 48px;
          border-radius: 14px;
          background: var(--accent);
          color: #fff;
          font-size: 14px; font-weight: 700; letter-spacing: .04em;
          display: flex; align-items: center; justify-content: center;
        }
        .brand-name {
          font-size: 18px; font-weight: 700;
          color: var(--fg-primary);
          font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .brand-sub { font-size: 12px; color: var(--fg-muted); }

        .login-tabs {
          display: flex;
          border-bottom: 1px solid var(--border);
          gap: 0;
        }
        .login-tab {
          flex: 1;
          padding: 8px 0;
          font-size: 13px; font-weight: 500;
          color: var(--fg-muted);
          background: none; border: none; cursor: pointer;
          border-bottom: 2px solid transparent;
          margin-bottom: -1px;
          transition: color .15s, border-color .15s;
        }
        .login-tab:hover { color: var(--fg-primary); }
        .login-tab-active { color: var(--accent); border-bottom-color: var(--accent); }

        .login-form {
          display: flex; flex-direction: column; gap: 14px;
        }
        .field { display: flex; flex-direction: column; gap: 5px; }
        .field-label { font-size: 12px; font-weight: 500; color: var(--fg-secondary); }
        .field-input {
          padding: 9px 12px;
          border-radius: 9px;
          border: 1px solid var(--border);
          background: var(--bg-input);
          color: var(--fg-primary);
          font-size: 14px;
          transition: border-color .15s;
        }
        .field-input:focus { outline: none; border-color: var(--border-focus); }

        .login-error {
          font-size: 13px; color: var(--danger);
          background: color-mix(in srgb, var(--danger) 10%, transparent);
          border: 1px solid color-mix(in srgb, var(--danger) 25%, transparent);
          border-radius: 8px; padding: 8px 12px;
        }
        .login-info {
          font-size: 13px; color: var(--success);
          background: color-mix(in srgb, var(--success) 10%, transparent);
          border: 1px solid color-mix(in srgb, var(--success) 25%, transparent);
          border-radius: 8px; padding: 8px 12px;
        }
        .login-submit {
          padding: 10px;
          border-radius: 10px;
          border: none;
          background: var(--accent);
          color: #fff;
          font-size: 14px; font-weight: 600;
          cursor: pointer;
          transition: background .15s, opacity .15s;
        }
        .login-submit:hover:not(:disabled) { background: var(--accent-hover); }
        .login-submit:disabled { opacity: .5; cursor: default; }

        .login-note {
          font-size: 11px; color: var(--fg-muted);
          text-align: center;
        }
      `}</style>
    </div>
  );
}
