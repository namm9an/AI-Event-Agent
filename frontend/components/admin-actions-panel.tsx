"use client";

import { useState } from "react";

import { api } from "@/lib/api";

interface AdminActionsPanelProps {
  token: string;
}

export default function AdminActionsPanel({ token }: AdminActionsPanelProps) {
  const [running, setRunning] = useState<"scrape" | "report" | null>(null);

  async function runScrape() {
    setRunning("scrape");
    try {
      await api.runNow(token);
    } finally {
      setRunning(null);
    }
  }

  async function runReport() {
    setRunning("report");
    try {
      await api.generateReportNow(token);
    } finally {
      setRunning(null);
    }
  }

  return (
    <section className="glass-card rounded-xl p-8">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">Manual Actions</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          type="button"
          onClick={runScrape}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 bg-primary text-black font-bold rounded-lg hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "scrape" ? "Running Scrape..." : "Run Scrape Now"}
        </button>
        <button
          type="button"
          onClick={runReport}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 border border-[#ff7d93]/40 text-[#ff7d93] font-bold rounded-lg hover:bg-[#ff7d93]/5 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "report" ? "Generating Report..." : "Generate Report Now"}
        </button>
      </div>
    </section>
  );
}
