"use client";

import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import type { Schedule } from "@/lib/types";

interface AdminSchedulePanelProps {
  token: string;
  schedule: Schedule;
  onRefresh: () => Promise<void>;
}

export default function AdminSchedulePanel({ token, schedule, onRefresh }: AdminSchedulePanelProps) {
  const [timezone, setTimezone] = useState(schedule.timezone);
  const [scrapeTime, setScrapeTime] = useState(schedule.scrape_time);
  const [reportTime, setReportTime] = useState(schedule.report_time);
  const [saving, setSaving] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    try {
      await api.updateAdminSchedule(token, {
        timezone,
        scrape_time: scrapeTime,
        report_time: reportTime
      });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel rounded-2xl p-4">
      <h2 className="panel-title">Scheduler</h2>
      <form className="mt-4 grid gap-3 md:grid-cols-3" onSubmit={onSubmit}>
        <label className="text-xs text-slate-300/90">
          Timezone
          <input
            className="input-shell mt-1 w-full rounded-lg px-3 py-2 text-sm"
            value={timezone}
            onChange={(e) => setTimezone(e.target.value)}
          />
        </label>
        <label className="text-xs text-slate-300/90">
          Scrape Time
          <input
            className="input-shell mt-1 w-full rounded-lg px-3 py-2 text-sm"
            type="time"
            value={scrapeTime}
            onChange={(e) => setScrapeTime(e.target.value)}
          />
        </label>
        <label className="text-xs text-slate-300/90">
          Report Time
          <input
            className="input-shell mt-1 w-full rounded-lg px-3 py-2 text-sm"
            type="time"
            value={reportTime}
            onChange={(e) => setReportTime(e.target.value)}
          />
        </label>
        <button className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold md:col-span-3" disabled={saving}>
          {saving ? "Saving..." : "Save schedule"}
        </button>
      </form>
    </section>
  );
}
