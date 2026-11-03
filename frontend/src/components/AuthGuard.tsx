"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export function AuthGuard({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const supabaseConfigured = !!process.env.NEXT_PUBLIC_SUPABASE_URL;

  useEffect(() => {
    if (loading) return;
    if (!supabaseConfigured) return; // local dev — no auth required
    if (!session && pathname !== "/login") {
      router.replace("/login");
    } else if (session && pathname === "/login") {
      router.replace("/");
    }
  }, [session, loading, pathname, router, supabaseConfigured]);

  if (loading) {
    return (
      <div style={{
        height: "100%", display: "flex",
        alignItems: "center", justifyContent: "center",
        background: "var(--bg-page)",
      }}>
        <div style={{ fontSize: 13, color: "var(--fg-muted)" }}>Chargement…</div>
      </div>
    );
  }

  return <>{children}</>;
}
