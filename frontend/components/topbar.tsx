"use client";

import Link from "next/link";

import { clearSession, getRole } from "@/lib/session";

export default function TopBar() {
  const role = getRole();

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-black/90 backdrop-blur-md border-b border-white/10 z-50 px-8 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <span className="text-black font-display font-bold text-xl">S</span>
        </div>
        <h1 className="font-display font-bold text-xl tracking-wider text-slate-100">SCOUT</h1>
      </div>
      <div className="flex items-center gap-10">
        <div className="flex items-center gap-8">
          <Link
            href="/dashboard"
            className="font-display text-sm font-bold tracking-widest text-primary"
          >
            DASHBOARD
          </Link>
          {role === "super_admin" && (
            <Link
              href="/settings"
              className="font-display text-sm font-bold tracking-widest text-slate-400 hover:text-slate-100 transition-colors"
            >
              SETTINGS
            </Link>
          )}
        </div>
        <button
          type="button"
          onClick={() => { clearSession(); window.location.href = "/login"; }}
          className="font-display text-sm font-bold tracking-widest px-6 py-2 border border-[#ff7d93]/40 text-[#ff7d93] rounded-lg hover:bg-[#ff7d93]/10 transition-all"
        >
          LOGOUT
        </button>
      </div>
    </header>
  );
}
