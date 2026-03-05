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
    api.downloadReport(token, reportId, report?.file_name ?? `report-${reportId}.pdf`).catch(() => {});
  }

  return (
    <ProtectedShell>
      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <TopBar />
        <section className="mb-4">
          <p className="panel-title">Mission Feed</p>
          <h2 className="heading-display mt-1 text-3xl">Daily Event Intelligence</h2>
        </section>

        <StatusOverview events={events.length} speakers={events.reduce((n, e) => n + (e.speakers?.length ?? 0), 0)} reports={reports.length} />

        <div className="mt-6 grid gap-5 lg:grid-cols-[280px_1fr]">
          <ReportsSidebar
            reports={reports}
            activeReportId={activeReportId}
            onSelect={setActiveReportId}
            onDownload={downloadReport}
          />

          <div className="space-y-5">
            <EventsTable events={events} />
            <ChatPanel token={token} activeReportId={activeReportId} />
          </div>
        </div>
      </main>
    </ProtectedShell>
  );
}
