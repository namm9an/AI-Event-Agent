"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearSession, getRole } from "@/lib/session";

export default function TopBar() {
  const router = useRouter();
  const role = getRole();

  return (
    <header className="frost mb-6 rounded-2xl px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-cyan">Scout Console</p>
          <h1 className="text-xl font-semibold">AI Event Agent</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Link className="rounded-lg border border-white/20 px-3 py-2 hover:bg-white/10" href="/dashboard">
            Dashboard
          </Link>
          {role === "super_admin" ? (
            <Link className="rounded-lg border border-white/20 px-3 py-2 hover:bg-white/10" href="/settings">
              Settings
            </Link>
          ) : null}
          <button
            type="button"
            className="rounded-lg bg-ember px-3 py-2 font-semibold text-ink"
            onClick={() => {
              clearSession();
              router.push("/login");
            }}
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
