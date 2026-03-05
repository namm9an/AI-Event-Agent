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
    <aside className="glass-card rounded-xl flex flex-col h-fit">
      <div className="p-6 border-b border-white/10">
        <h3 className="font-display text-sm font-bold tracking-widest text-slate-100">DAILY REPORTS</h3>
      </div>
      <div className="p-2 flex flex-col gap-2 max-h-[600px] overflow-y-auto">
        {reports.length === 0 ? (
          <p className="text-sm text-slate-500 py-8 text-center">No reports yet.</p>
        ) : (
          reports.map((report) => {
            const isActive = activeReportId === report.id;
            return (
              <div
                key={report.id}
                className={`p-4 rounded-lg cursor-pointer transition-all ${isActive
                    ? "bg-primary/5 border border-primary shadow-[0_0_15px_rgba(26,213,255,0.1)]"
                    : "hover:bg-white/5 border border-transparent"
                  }`}
                onClick={() => onSelect(report.id)}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] font-bold text-slate-500">{report.report_date}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${report.status === "ready"
                      ? "bg-accent/20 text-accent"
                      : "bg-white/10 text-slate-400"
                    }`}>
                    {report.status?.toUpperCase() || "PENDING"}
                  </span>
                </div>
                <p className={`text-sm font-medium mb-3 ${isActive ? "text-slate-100" : "text-slate-400"}`}>
                  {report.file_name}
                </p>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); onDownload(report.id); }}
                  className="text-xs font-bold text-primary flex items-center gap-1 hover:text-accent transition-colors"
                >
                  ↓ DOWNLOAD
                </button>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
