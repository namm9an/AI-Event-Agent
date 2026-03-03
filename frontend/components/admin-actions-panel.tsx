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
    <section className="panel rounded-2xl p-4">
      <h2 className="panel-title">Manual Actions</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <button
          type="button"
          className="btn-primary rounded-xl px-4 py-3 text-sm font-semibold"
          onClick={runScrape}
          disabled={running !== null}
        >
          {running === "scrape" ? "Running scrape..." : "Run Scrape Now"}
        </button>
        <button
          type="button"
          className="btn-danger rounded-xl px-4 py-3 text-sm font-semibold"
          onClick={runReport}
          disabled={running !== null}
        >
          {running === "report" ? "Generating report..." : "Generate Report Now"}
        </button>
      </div>
    </section>
  );
}
