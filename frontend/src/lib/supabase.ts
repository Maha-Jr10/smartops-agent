import { createBrowserClient } from "@supabase/ssr";

export type UserRole = "commercial" | "delivery" | "admin";

export interface Profile {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
}

let _client: ReturnType<typeof createBrowserClient> | null = null;

export function getSupabase() {
  if (!_client) {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
    if (!url || !key) {
      // Will fail gracefully — AuthContext catches the error and treats user as unauthenticated
      throw new Error("NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set.");
    }
    _client = createBrowserClient(url, key);
  }
  return _client;
}
