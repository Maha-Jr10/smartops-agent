import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { AuthGuard } from "@/components/AuthGuard";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "SmartOps Agent",
  description: "Assistant interne Smartara — recherche CRM, factures, commissions",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" style={{ height: "100%" }}>
      <body style={{ height: "100%" }}>
        <AuthProvider>
          <AuthGuard>{children}</AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
