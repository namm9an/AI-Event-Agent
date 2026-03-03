"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { clearSession, getRole, getToken } from "@/lib/session";
import type { Role } from "@/lib/types";

interface ProtectedShellProps {
  children: React.ReactNode;
  requireRole?: Role;
}

export default function ProtectedShell({ children, requireRole }: ProtectedShellProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getToken();
    const role = getRole();

    if (!token || !role) {
      router.replace("/login");
      return;
    }

    if (requireRole && role !== requireRole) {
      router.replace("/dashboard");
      return;
    }

    api.me(token)
      .then(() => setReady(true))
      .catch(() => {
        clearSession();
        router.replace("/login");
      });
  }, [requireRole, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="frost rounded-2xl px-8 py-6 text-sm text-slate-200/80">Validating session...</div>
      </div>
    );
  }

  return <>{children}</>;
}
