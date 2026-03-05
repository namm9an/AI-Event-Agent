"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ChatPanel from "@/components/chat-panel";
import EventsTable from "@/components/events-table";
import ProtectedShell from "@/components/protected-shell";
import ReportsSidebar from "@/components/reports-sidebar";
import StatusOverview from "@/components/status-overview";
import TopBar from "@/components/topbar";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Event, ReportItem } from "@/lib/types";

export default function DashboardPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [activeReportId, setActiveReportId] = useState<string | undefined>();
  const [scrapeRunning, setScrapeRunning] = useState(false);
  const [reportRunning, setReportRunning] = useState(false);

  const token = useMemo(() => getToken() ?? "", []);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [eventData, reportData] = await Promise.all([
        api.events(token),
        api.reports(token),
      ]);
      setEvents(eventData.events);
      setReports((prev) => {
        // Keep active selection if it still exists, else pick first
        const ids = new Set(reportData.reports.map((r) => r.id));
        setActiveReportId((prev) => (prev && ids.has(prev) ? prev : reportData.reports[0]?.id));
        return reportData.reports;
      });
    } catch {
      /* silent */
    }
  }, [token]);

  // Poll /api/status every 3 seconds to detect scrape/report in progress
  useEffect(() => {
    if (!token) return;

    async function pollStatus() {
      try {
        const s = await api.status(token);
        setScrapeRunning(s.crew_running);
        setReportRunning(s.report_running);

        // When a scrape just finished, refresh data
        if (!s.crew_running && !s.report_running) {
          await fetchData();
        }
      } catch {
        /* silent */
      }
    }

    pollStatus(); // call immediately on mount
    pollRef.current = setInterval(pollStatus, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [token, fetchData]);

  // Initial data load
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function viewReport(reportId: string) {
    api.viewReport(token, reportId).catch(() => {});
  }

  function downloadReport(reportId: string) {
    const report = reports.find((r) => r.id === reportId);
    api
      .downloadReport(token, reportId, report?.file_name ?? `report-${reportId}.pdf`)
      .catch(() => { });
  }

  async function deleteReport(reportId: string) {
    try {
      await api.deleteReport(token, reportId);
      // Remove from local state immediately
      setReports((prev) => {
        const next = prev.filter((r) => r.id !== reportId);
        setActiveReportId((active) => {
          if (active === reportId) return next[0]?.id;
          return active;
        });
        return next;
      });
    } catch {
      /* silent — could add toast here */
    }
  }

  return (
    <ProtectedShell>
      <div className="bg-black min-h-screen text-slate-100">
        <TopBar />

        {/* Background ambient glow */}
        <div className="fixed top-0 right-0 -z-10 w-[500px] h-[500px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="fixed bottom-0 left-0 -z-10 w-[400px] h-[400px] bg-accent/5 blur-[100px] rounded-full pointer-events-none" />

        <main className="pt-24 pb-12 px-8 max-w-[1600px] mx-auto">
          {/* Page Header */}
          <header className="mb-10">
            <p className="font-display text-primary text-xs font-bold tracking-[0.2em] mb-2">MISSION FEED</p>
            <h2 className="font-display text-5xl font-bold tracking-tight text-slate-100">
              DAILY EVENT INTELLIGENCE
            </h2>
          </header>

          {/* Stat cards */}
          <StatusOverview
            events={events.length}
            speakers={events.reduce((n, e) => n + (e.speakers?.length ?? 0), 0)}
            reports={reports.length}
          />

          {/* Main grid */}
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-8">
            <ReportsSidebar
              reports={reports}
              activeReportId={activeReportId}
              scrapeRunning={scrapeRunning}
              reportRunning={reportRunning}
              onSelect={setActiveReportId}
              onView={viewReport}
              onDownload={downloadReport}
              onDelete={deleteReport}
            />
            <div className="flex flex-col gap-8">
              <EventsTable events={events} />
              <ChatPanel token={token} activeReportId={activeReportId} />
            </div>
          </div>
        </main>
      </div>
    </ProtectedShell>
  );
}
