const BASE = "/api";

export type Role = "commercial" | "delivery" | "admin";

async function authHeaders(): Promise<HeadersInit> {
  try {
    const { getSupabase } = await import("@/lib/supabase");
    const { data } = await getSupabase().auth.getSession();
    const token = data.session?.access_token;
    if (token) return { "Content-Type": "application/json", Authorization: `Bearer ${token}` };
  } catch { /* local dev without Supabase */ }
  return { "Content-Type": "application/json" };
}

export interface ChatMessage {
  id: string;
  role: "user" | "agent" | "error";
  text: string;
  traceId?: string;
  timestamp: Date;
}

export interface Approval {
  request_id: string;
  action: string;
  details: Record<string, unknown>;
  reason?: string;
  requested_by: string;
  role: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  comment?: string;
}

export interface HealthStatus {
  status: string;
  version: string;
  env: string;
}

export async function sendChat(
  message: string,
  sessionId?: string,
): Promise<{ answer: string; trace_id: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId ?? "" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erreur inconnue");
  }
  return res.json();
}

export async function fetchApprovals(): Promise<Approval[]> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/approvals`, { headers });
  if (!res.ok) throw new Error("Impossible de charger les approbations");
  return res.json();
}

export async function decideApproval(
  requestId: string,
  decision: "approved" | "rejected",
  comment = ""
): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/approvals/${requestId}`, {
    method: "POST",
    headers,
    body: JSON.stringify({ decision, comment }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erreur lors de la décision");
  }
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("API indisponible");
  return res.json();
}

export interface GroqKeyStatus {
  has_key: string;
  masked: string;
  source: string;
}

export async function fetchGroqKeyStatus(): Promise<GroqKeyStatus> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/groq-key`, { headers });
  if (!res.ok) throw new Error("Impossible de charger le statut de la clé");
  return res.json();
}

export async function updateGroqKey(apiKey: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/groq-key`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Erreur lors de la mise à jour");
  }
}

export interface OpenRouterKeyStatus {
  has_key: string;
  masked: string;
}

export async function fetchOpenRouterKeyStatus(): Promise<OpenRouterKeyStatus> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/openrouter-key`, { headers });
  if (!res.ok) throw new Error("Impossible de charger le statut de la clé OpenRouter");
  return res.json();
}

export async function updateOpenRouterKey(apiKey: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/openrouter-key`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ api_key: apiKey }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Erreur lors de la mise à jour");
  }
}

export interface ModelStatus {
  current: string;
  models: { id: string; label: string }[];
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/model`, { headers });
  if (!res.ok) throw new Error("Impossible de charger le modèle actif");
  return res.json();
}

export async function updateModel(modelId: string): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/settings/model`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ model_id: modelId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Erreur lors de la mise à jour");
  }
}

export interface MonitoringStatus {
  status: "ok" | "drift_detected" | "insufficient_data" | "never_run";
  last_run?: string;
  message?: string;
  drifted_columns?: string[];
}

export async function fetchMonitoringStatus(): Promise<MonitoringStatus> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/monitoring/status`, { headers });
  if (!res.ok) throw new Error("Impossible de charger le statut monitoring");
  return res.json();
}

export async function seedDemoData(): Promise<{ seeded_traces: number; report: string }> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/admin/seed-data`, { method: "POST", headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Erreur lors de l'injection");
  }
  return res.json();
}

export async function deleteSeedData(): Promise<void> {
  const headers = await authHeaders();
  const res = await fetch(`${BASE}/admin/seed-data`, { method: "DELETE", headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail ?? "Erreur lors de la suppression");
  }
}

export async function fetchDriftReport(): Promise<string | null> {
  try {
    const { getSupabase } = await import("@/lib/supabase");
    const { data } = await getSupabase().auth.getSession();
    const token = data.session?.access_token;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${BASE}/report/drift`, { headers });
    if (!res.ok) return null;
    return res.text();
  } catch {
    return null;
  }
}
