"use client";

import { useState, useRef, useEffect, type FormEvent, type KeyboardEvent } from "react";
import { sendChat, type ChatMessage } from "@/lib/api";

const SUGGESTIONS = [
  "Bonjour, que peux-tu faire pour moi ?",
  "Liste les clients actifs",
  "Quels projets sont actuellement en cours ?",
  "Montre-moi les leads en attente de contact",
];

let idCounter = 0;
function genId() { return `msg-${++idCounter}`; }

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  async function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: ChatMessage = {
      id: genId(), role: "user", text: trimmed, timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { answer, trace_id } = await sendChat(trimmed);
      setMessages(prev => [...prev, {
        id: genId(), role: "agent", text: answer, traceId: trace_id, timestamp: new Date(),
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        id: genId(), role: "error",
        text: err instanceof Error ? err.message : "Erreur inattendue",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit(input);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  }

  function handleSuggestion(s: string) {
    setInput(s);
    inputRef.current?.focus();
  }

  return (
    <div className="chat-shell">

      {/* ── Toolbar ──────────────────────────────────────────── */}
      {messages.length > 0 && (
        <div className="chat-toolbar">
          <button
            className="clear-btn"
            onClick={() => setMessages([])}
            title="Effacer la conversation"
          >
            <IconTrash />
            <span className="clear-label">Effacer</span>
          </button>
        </div>
      )}

      {/* ── Message list ─────────────────────────────────────── */}
      <div className="messages-area" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-logo">SO</div>
            <p className="empty-title">Comment puis-je vous aider ?</p>
            <p className="empty-sub">Recherchez un client, vérifiez une facture ou calculez une commission.</p>
            <div className="suggestions">
              {SUGGESTIONS.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => handleSuggestion(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {loading && <TypingIndicator />}
          </div>
        )}
      </div>

      {/* ── Input ────────────────────────────────────────────── */}
      <form className="input-area" onSubmit={handleSubmit}>
        <div className="input-wrap">
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Écrivez votre message… (Entrée pour envoyer)"
            rows={1}
            disabled={loading}
            maxLength={1000}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!input.trim() || loading}
            title="Envoyer (Entrée)"
          >
            {loading ? <IconSpinner /> : <IconSend />}
          </button>
        </div>
        <p className="input-hint">Shift+Entrée pour un saut de ligne</p>
      </form>

      <style>{`
        /* ── Shell ─────────────────────────────────────── */
        .chat-shell {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: var(--bg-page);
        }

        /* ── Toolbar ────────────────────────────────────── */
        .chat-toolbar {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          padding: 6px max(16px, env(safe-area-inset-left, 0px));
          background: var(--bg-surface);
          border-bottom: 1px solid var(--border);
          flex-shrink: 0;
        }

        .clear-btn {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 5px 10px;
          border-radius: 8px;
          border: 1px solid transparent;
          background: none;
          color: var(--fg-muted);
          font-size: 12px;
          cursor: pointer;
          transition: background 0.15s, color 0.15s;
          flex-shrink: 0;
        }
        .clear-btn:hover { background: var(--bg-hover); color: var(--fg-primary); }
        .clear-label { display: none; }
        @media (min-width: 480px) { .clear-label { display: inline; } }

        /* ── Messages area ──────────────────────────────── */
        .messages-area {
          flex: 1;
          overflow-y: auto;
          overflow-x: hidden;
          padding: 24px max(16px, env(safe-area-inset-left, 0px));
          scroll-behavior: smooth;
        }

        /* ── Empty state ─────────────────────────────────── */
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 48px 16px;
          gap: 12px;
          height: 100%;
          min-height: 300px;
        }
        .empty-logo {
          width: 52px;
          height: 52px;
          border-radius: 14px;
          background: var(--accent);
          color: #fff;
          font-size: 15px;
          font-weight: 700;
          letter-spacing: 0.04em;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 4px;
        }
        .empty-title {
          font-size: 18px;
          font-weight: 600;
          color: var(--fg-primary);
          font-family: 'Plus Jakarta Sans', sans-serif;
        }
        .empty-sub {
          font-size: 13px;
          color: var(--fg-muted);
          max-width: 320px;
          line-height: 1.6;
        }
        .suggestions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: center;
          margin-top: 8px;
        }
        .suggestion-chip {
          padding: 7px 14px;
          border-radius: 20px;
          border: 1px solid var(--border);
          background: var(--bg-surface);
          font-size: 12px;
          color: var(--fg-secondary);
          cursor: pointer;
          transition: all 0.15s;
          text-align: left;
        }
        .suggestion-chip:hover {
          border-color: var(--accent);
          color: var(--accent);
          background: var(--accent-subtle);
        }

        /* ── Messages list ──────────────────────────────── */
        .messages-list {
          display: flex;
          flex-direction: column;
          gap: 16px;
          max-width: 760px;
          margin: 0 auto;
          width: 100%;
        }

        /* ── Input area ──────────────────────────────────── */
        .input-area {
          padding: 12px max(16px, env(safe-area-inset-left, 0px));
          background: var(--bg-surface);
          border-top: 1px solid var(--border);
          flex-shrink: 0;
        }
        .input-wrap {
          display: flex;
          align-items: flex-end;
          gap: 8px;
          max-width: 760px;
          margin: 0 auto;
        }
        .chat-input {
          flex: 1;
          min-width: 0;
          padding: 10px 14px;
          border-radius: 12px;
          border: 1px solid var(--border);
          background: var(--bg-input);
          color: var(--fg-primary);
          font-family: inherit;
          font-size: 14px;
          line-height: 1.5;
          resize: none;
          min-height: 44px;
          max-height: 140px;
          overflow-y: auto;
          transition: border-color 0.15s;
          field-sizing: content;
        }
        .chat-input:focus { outline: none; border-color: var(--border-focus); }
        .chat-input:disabled { opacity: 0.6; }
        .chat-input::placeholder { color: var(--fg-muted); }
        .send-btn {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          border: none;
          background: var(--accent);
          color: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          flex-shrink: 0;
          transition: background 0.15s, opacity 0.15s;
        }
        .send-btn:hover:not(:disabled) { background: var(--accent-hover); }
        .send-btn:disabled { opacity: 0.4; cursor: default; }
        .input-hint {
          font-size: 11px;
          color: var(--fg-muted);
          text-align: right;
          margin-top: 4px;
          max-width: 760px;
          margin-inline: auto;
        }

        /* ── Typing indicator ────────────────────────────── */
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40%            { transform: translateY(-5px); }
        }
        .typing-dot {
          width: 5px; height: 5px; border-radius: 50%;
          background: var(--fg-muted);
          animation: bounce 1.2s ease-in-out infinite;
        }
        .typing-dot:nth-child(2) { animation-delay: 0.15s; }
        .typing-dot:nth-child(3) { animation-delay: 0.30s; }

        /* ── Spinner ─────────────────────────────────────── */
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner { animation: spin 0.7s linear infinite; }

        /* ── Bubble rows ─────────────────────────────────── */
        .bubble-row { display: flex; align-items: flex-end; gap: 8px; }
        .bubble-row-user { flex-direction: row-reverse; }
        .bubble-col { display: flex; flex-direction: column; gap: 3px; max-width: 80%; min-width: 0; }
        .bubble-col-user { align-items: flex-end; }
        .agent-avatar {
          width: 28px; height: 28px; border-radius: 8px;
          background: var(--accent); color: #fff;
          font-size: 10px; font-weight: 700; letter-spacing: .04em;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
        }
        .bubble { padding: 10px 14px; border-radius: 16px; word-break: break-word; }
        .bubble-user {
          background: var(--bubble-user-bg); color: var(--bubble-user-fg);
          border-radius: 16px 16px 4px 16px;
        }
        .bubble-agent {
          background: var(--bubble-agent-bg); color: var(--bubble-agent-fg);
          border: 1px solid var(--border);
          border-radius: 16px 16px 16px 4px;
          box-shadow: 0 1px 3px rgba(0,0,0,.06);
        }
        .bubble-error {
          background: var(--bubble-error-bg); color: var(--bubble-error-fg);
          border: 1px solid currentColor; opacity: .9;
          border-radius: 16px 16px 16px 4px;
        }
        .bubble-text { font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
        .bubble-meta { display: flex; align-items: center; gap: 8px; padding: 0 4px; }
        .bubble-meta-right { flex-direction: row-reverse; }
        .bubble-time { font-size: 11px; color: var(--fg-muted); font-variant-numeric: tabular-nums; }
        .bubble-trace { font-size: 10px; color: var(--fg-muted); font-family: monospace; opacity: .7; }
      `}</style>
    </div>
  );
}

/* ── Message bubble ─────────────────────────────────────────── */
function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser  = msg.role === "user";
  const isError = msg.role === "error";
  const time    = msg.timestamp.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className={`bubble-row ${isUser ? "bubble-row-user" : "bubble-row-agent"}`}>
      {!isUser && (
        <div className="agent-avatar">SO</div>
      )}
      <div className={`bubble-col ${isUser ? "bubble-col-user" : ""}`}>
        <div className={`bubble ${isUser ? "bubble-user" : isError ? "bubble-error" : "bubble-agent"}`}>
          <p className="bubble-text">{msg.text}</p>
        </div>
        <div className={`bubble-meta ${isUser ? "bubble-meta-right" : ""}`}>
          <span className="bubble-time">{time}</span>
          {msg.traceId && (
            <span className="bubble-trace" title={msg.traceId}>
              trace #{msg.traceId.slice(0, 8)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="bubble-row bubble-row-agent">
      <div className="agent-avatar">SO</div>
      <div
        style={{
          display: "flex", alignItems: "center", gap: 4,
          padding: "10px 14px",
          background: "var(--bubble-agent-bg)",
          border: "1px solid var(--border)",
          borderRadius: "16px 16px 16px 4px",
          boxShadow: "0 1px 3px rgba(0,0,0,.06)",
        }}
      >
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  );
}

/* ── Icons ──────────────────────────────────────────────────── */
function IconSend() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
    </svg>
  );
}
function IconSpinner() {
  return (
    <svg className="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
    </svg>
  );
}
function IconTrash() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/>
    </svg>
  );
}
