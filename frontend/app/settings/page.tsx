"use client";

import { useEffect, useMemo, useState } from "react";

import AdminActionsPanel from "@/components/admin-actions-panel";
import AdminQueryManager from "@/components/admin-query-manager";
import AdminSchedulePanel from "@/components/admin-schedule-panel";
import ProtectedShell from "@/components/protected-shell";
import TopBar from "@/components/topbar";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Schedule, SearchQuery } from "@/lib/types";

export default function SettingsPage() {
  const token = useMemo(() => getToken() ?? "", []);
  const [queries, setQueries] = useState<SearchQuery[]>([]);
  const [schedule, setSchedule] = useState<Schedule>({
    timezone: "Asia/Kolkata",
    scrape_time: "00:00",
    report_time: "12:00"
  });

  async function refresh() {
    if (!token) return;
    const [queriesData, scheduleData] = await Promise.all([api.adminQueries(token), api.adminSchedule(token)]);
    setQueries(queriesData.queries);
    setSchedule(scheduleData);
  }

  useEffect(() => {
    refresh().catch(() => {
      setQueries([]);
    });
  }, [token]);

  return (
    <ProtectedShell requireRole="super_admin">
      <div className="bg-black min-h-screen text-slate-100">
        <TopBar />

        {/* Background Decoration */}
        <div className="fixed top-0 right-0 -z-10 w-[500px] h-[500px] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="fixed bottom-0 left-0 -z-10 w-[400px] h-[400px] bg-accent/5 blur-[100px] rounded-full pointer-events-none" />

        <main className="pt-32 pb-20 max-w-6xl mx-auto px-6">
          <header className="mb-12">
            <p className="font-display text-primary text-xs font-bold tracking-[0.3em] uppercase mb-2">Control Room</p>
            <h2 className="font-display text-5xl font-bold tracking-tighter uppercase text-slate-100">Super Admin Configuration</h2>
          </header>

          <div className="grid grid-cols-1 gap-8">
            <AdminActionsPanel token={token} />
            <AdminSchedulePanel token={token} schedule={schedule} onRefresh={refresh} />
            <AdminQueryManager token={token} queries={queries} onRefresh={refresh} />
          </div>
        </main>
      </div>
    </ProtectedShell>
  );
}
