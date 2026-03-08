"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

interface AdminActionsPanelProps {
  token: string;
}

export default function AdminActionsPanel({ token }: AdminActionsPanelProps) {
  const [running, setRunning] = useState<"scrape" | "report" | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!token) return;

    async function pollStatus() {
      try {
        const s = await api.status(token);
        if (s.crew_running) {
          setRunning("scrape");
        } else if (s.report_running) {
          setRunning("report");
        } else {
          setRunning(null);
        }
      } catch {
        // silent
      }
    }

    pollStatus();
    pollRef.current = setInterval(pollStatus, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [token]);

  async function runScrape() {
    setRunning("scrape");
    try {
      await api.runNow(token);
    } catch {
      setRunning(null);
    }
  }

  async function runReport() {
    setRunning("report");
    try {
      await api.generateReportNow(token);
      router.push("/dashboard");
    } catch {
      setRunning(null);
    }
  }

  async function clearAllEvents() {
    if (!confirm("This will permanently delete ALL events and speakers from the database. Are you sure?")) return;
    setRunning("scrape");
    try {
      const result = await api.clearAllEvents(token);
      alert(`Cleared ${result.deleted_events} events and ${result.deleted_speakers} speakers.`);
      router.refresh();
    } catch {
      alert("Failed to clear events. Check your connection.");
    } finally {
      setRunning(null);
    }
  }

  async function enrichLinkedin() {
    setRunning("scrape");
    try {
      const result = await api.enrichLinkedin(token);
      alert(`LinkedIn enrichment complete: ${result.enriched} of ${result.total_checked} speakers enriched.`);
    } catch {
      // silent
    } finally {
      setRunning(null);
    }
  }

  // Small spinner SVG
  const spinner = (
    <svg className="animate-spin" width="16" height="16" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
      <path d="M11 6A5 5 0 0 0 6 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );

  return (
    <section className="glass-card rounded-xl p-8">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">Manual Actions</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <button
          type="button"
          onClick={runScrape}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 bg-primary text-black font-bold rounded-lg hover:brightness-110 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "scrape" ? <>{spinner} SCRAPING IN PROGRESS...</> : "Run Scrape Now"}
        </button>
        <button
          type="button"
          onClick={runReport}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 border border-[#ff7d93]/40 text-[#ff7d93] font-bold rounded-lg hover:bg-[#ff7d93]/5 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "report" ? <>{spinner} BUILDING REPORT...</> : "Generate Report Now"}
        </button>
        <button
          type="button"
          onClick={enrichLinkedin}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 border border-accent/40 text-accent font-bold rounded-lg hover:bg-accent/5 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "scrape" ? <>{spinner} ENRICHING...</> : "Enrich LinkedIn URLs"}
        </button>
        <button
          type="button"
          onClick={clearAllEvents}
          disabled={running !== null}
          className="flex items-center justify-center gap-3 h-16 border border-red-500/40 text-red-400 font-bold rounded-lg hover:bg-red-500/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-display uppercase tracking-widest text-sm"
        >
          {running === "scrape" ? <>{spinner} CLEARING...</> : "Clear All Events"}
        </button>
      </div>
    </section>
  );
}
