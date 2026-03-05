"use client";

import type { ReportItem } from "@/lib/types";

interface ReportsSidebarProps {
  reports: ReportItem[];
  activeReportId?: string;
  scrapeRunning?: boolean;
  reportRunning?: boolean;
  onSelect: (reportId: string) => void;
  onDownload: (reportId: string) => void;
  onDelete: (reportId: string) => void;
}

export default function ReportsSidebar({
  reports,
  activeReportId,
  scrapeRunning,
  reportRunning,
  onSelect,
  onDownload,
  onDelete,
}: ReportsSidebarProps) {
  function handleDelete(e: React.MouseEvent, reportId: string) {
    e.stopPropagation();
    if (!window.confirm("Delete this report? This cannot be undone.")) return;
    onDelete(reportId);
  }

  return (
    <aside className="glass-card rounded-xl flex flex-col h-fit">
      {/* Header */}
      <div className="p-6 border-b border-white/10 flex items-center justify-between gap-3">
        <h3 className="font-display text-sm font-bold tracking-widest text-slate-100">DAILY REPORTS</h3>
        {/* Scrape running indicator */}
        {(scrapeRunning || reportRunning) && (
          <div className="flex items-center gap-2 shrink-0">
            {/* Small spinning ring — 12px, no %, just a spinner */}
            <svg
              className="animate-spin text-primary"
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
              <path
                d="M11 6A5 5 0 0 0 6 1"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
            <span className="text-[10px] font-bold font-display uppercase tracking-widest text-primary">
              {scrapeRunning ? "Scraping…" : "Building…"}
            </span>
          </div>
        )}
      </div>

      {/* List */}
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
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold ${report.status === "ready"
                        ? "bg-accent/20 text-accent"
                        : "bg-white/10 text-slate-400"
                      }`}
                  >
                    {report.status?.toUpperCase() || "PENDING"}
                  </span>
                </div>
                <p
                  className={`text-sm font-medium mb-3 ${isActive ? "text-slate-100" : "text-slate-400"
                    }`}
                >
                  {report.file_name}
                </p>
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); onDownload(report.id); }}
                    className="text-xs font-bold text-primary flex items-center gap-1 hover:text-accent transition-colors"
                  >
                    ↓ DOWNLOAD
                  </button>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(e, report.id)}
                    className="text-xs font-bold text-[#ff7d93]/60 hover:text-[#ff7d93] transition-colors ml-auto"
                    title="Delete report"
                  >
                    ✕ DELETE
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
