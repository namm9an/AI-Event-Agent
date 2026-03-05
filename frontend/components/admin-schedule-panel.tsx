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
      await api.updateAdminSchedule(token, { timezone, scrape_time: scrapeTime, report_time: reportTime });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="glass-card rounded-xl p-8">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">Scheduler</h3>
      </div>
      <form onSubmit={onSubmit}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Timezone</label>
            <input
              className="scout-input h-12 rounded-lg px-4"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Scrape Time</label>
            <input
              className="scout-input h-12 rounded-lg px-4"
              type="time"
              value={scrapeTime}
              onChange={(e) => setScrapeTime(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Report Time</label>
            <input
              className="scout-input h-12 rounded-lg px-4"
              type="time"
              value={reportTime}
              onChange={(e) => setReportTime(e.target.value)}
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={saving}
          className="w-full h-14 bg-primary text-black font-bold rounded-lg hover:brightness-110 transition-all uppercase tracking-widest text-sm font-display disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Schedule"}
        </button>
      </form>
    </section>
  );
}
