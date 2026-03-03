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
      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        <TopBar />
        <div className="space-y-5">
          <section>
            <p className="panel-title">Control Room</p>
            <h2 className="heading-display mt-1 text-3xl">Super Admin Configuration</h2>
          </section>
          <AdminActionsPanel token={token} />
          <AdminSchedulePanel token={token} schedule={schedule} onRefresh={refresh} />
          <AdminQueryManager token={token} queries={queries} onRefresh={refresh} />
        </div>
      </main>
    </ProtectedShell>
  );
}
