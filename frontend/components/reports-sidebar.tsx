"use client";

import type { ReportItem } from "@/lib/types";

interface ReportsSidebarProps {
  reports: ReportItem[];
  activeReportId?: string;
  onSelect: (reportId: string) => void;
  onDownload: (reportId: string) => void;
}

export default function ReportsSidebar({ reports, activeReportId, onSelect, onDownload }: ReportsSidebarProps) {
  return (
    <aside className="frost rounded-2xl p-4">
      <h2 className="section-title text-sm uppercase tracking-[0.2em] text-cyan">Daily Reports</h2>
      <div className="mt-4 max-h-[420px] space-y-2 overflow-y-auto pr-1">
        {reports.length === 0 ? (
          <p className="text-sm text-slate-300/80">No reports yet.</p>
        ) : (
          reports.map((report) => (
            <div
              key={report.id}
              className={`rounded-xl border p-3 ${
                activeReportId === report.id ? "border-cyan bg-cyan/10" : "border-white/15 bg-white/5"
              }`}
            >
              <button type="button" className="w-full text-left" onClick={() => onSelect(report.id)}>
                <p className="font-medium">{report.report_date}</p>
                <p className="text-xs text-slate-300/80">{report.file_name}</p>
              </button>
              <div className="mt-2 flex justify-between text-xs text-slate-300/80">
                <span>{report.status}</span>
                <button type="button" className="text-cyan hover:underline" onClick={() => onDownload(report.id)}>
                  Download
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
