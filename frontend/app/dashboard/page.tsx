"use client";

import { useEffect, useMemo, useState } from "react";

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

  const token = useMemo(() => getToken() ?? "", []);

  useEffect(() => {
    if (!token) return;

    Promise.all([api.events(token), api.reports(token)])
      .then(([eventData, reportData]) => {
        setEvents(eventData.events);
        setReports(reportData.reports);
        setActiveReportId(reportData.reports[0]?.id);
      })
      .catch(() => {
        setEvents([]);
        setReports([]);
      });
  }, [token]);

  function downloadReport(reportId: string) {
    const report = reports.find((r) => r.id === reportId);
    api.downloadReport(token, reportId, report?.file_name ?? `report-${reportId}.pdf`).catch(() => { });
  }

  return (
    <ProtectedShell>
      <div className="bg-black min-h-screen text-slate-100">
        <TopBar />

        {/* Background Decoration */}
        <div className="fixed top-0 right-0 -z-10 w-[500px] h-[500px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="fixed bottom-0 left-0 -z-10 w-[400px] h-[400px] bg-accent/5 blur-[100px] rounded-full pointer-events-none" />

        <main className="pt-24 pb-12 px-8 max-w-[1600px] mx-auto">
          {/* Page Header */}
          <header className="mb-10">
            <p className="font-display text-primary text-xs font-bold tracking-[0.2em] mb-2">MISSION FEED</p>
            <h2 className="font-display text-5xl font-bold tracking-tight text-slate-100">DAILY EVENT INTELLIGENCE</h2>
          </header>

          {/* Status Overview */}
          <StatusOverview
            events={events.length}
            speakers={events.reduce((n, e) => n + (e.speakers?.length ?? 0), 0)}
            reports={reports.length}
          />

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-8">
            <ReportsSidebar
              reports={reports}
              activeReportId={activeReportId}
              onSelect={setActiveReportId}
              onDownload={downloadReport}
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
