"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { clearSession, getRole } from "@/lib/session";

export default function TopBar() {
  const router = useRouter();
  const role = getRole();

  return (
    <header className="panel mb-6 rounded-2xl px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="panel-title">Scout Console</p>
          <h1 className="heading-display text-2xl">AI Event Agent</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <Link className="btn-secondary rounded-lg px-3 py-2 transition hover:bg-white/12" href="/dashboard">
            Dashboard
          </Link>
          {role === "super_admin" ? (
            <Link className="btn-secondary rounded-lg px-3 py-2 transition hover:bg-white/12" href="/settings">
              Settings
            </Link>
          ) : null}
          <button
            type="button"
            className="btn-danger rounded-lg px-3 py-2 font-semibold"
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
