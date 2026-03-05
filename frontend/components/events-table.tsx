"use client";

import { useState } from "react";

import type { Event } from "@/lib/types";

interface EventsTableProps {
  events: Event[];
}

export default function EventsTable({ events }: EventsTableProps) {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  function toggleSpeakers(eventId: string) {
    setExpandedEventId((prev) => (prev === eventId ? null : eventId));
  }
  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div className="p-6 border-b border-white/10 flex justify-between items-center">
        <h3 className="font-display text-sm font-bold tracking-widest text-slate-100 uppercase">
          Live &amp; Upcoming Events
        </h3>
      </div>
      {events.length === 0 ? (
        <p className="text-sm text-slate-500 py-12 text-center">
          No events scraped yet. Run a scrape to populate this table.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="px-6 py-4 font-display text-xs font-bold text-slate-400 tracking-widest uppercase">Event</th>
                <th className="px-6 py-4 font-display text-xs font-bold text-slate-400 tracking-widest uppercase">Date</th>
                <th className="px-6 py-4 font-display text-xs font-bold text-slate-400 tracking-widest uppercase">City</th>
                <th className="px-6 py-4 font-display text-xs font-bold text-slate-400 tracking-widest uppercase text-center">Status</th>
                <th className="px-6 py-4 font-display text-xs font-bold text-slate-400 tracking-widest uppercase text-right">Speakers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {events.map((event) => (
                <>
                  <tr key={event.id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-5">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-slate-100">{event.name}</span>
                        <a
                          className="text-[10px] font-bold text-primary hover:underline mt-1"
                          href={event.url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          SOURCE ↗
                        </a>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-sm text-slate-400">{event.date_text || "—"}</td>
                    <td className="px-6 py-5 text-sm text-slate-400">{event.city || "—"}</td>
                    <td className="px-6 py-5 text-center">
                      <StatusBadge status={event.status} />
                    </td>
                    <td className="px-6 py-5 text-right">
                      <button
                        type="button"
                        onClick={() => toggleSpeakers(event.id)}
                        className="text-sm font-display font-bold text-primary hover:text-accent transition-colors"
                      >
                        {event.speakers?.length ?? 0}{" "}
                        {expandedEventId === event.id ? "▲" : "▼"}
                      </button>
                    </td>
                  </tr>
                  {expandedEventId === event.id && event.speakers && event.speakers.length > 0 && (
                    <tr key={`${event.id}-speakers`}>
                      <td colSpan={5} className="px-6 pb-5 pt-0">
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-3 border-t border-white/10">
                          {event.speakers.map((speaker) => (
                            <div key={speaker.id} className="bg-white/[0.03] border border-white/10 rounded-lg p-3">
                              <p className="text-sm font-semibold text-slate-100">{speaker.name}</p>
                              {speaker.designation && (
                                <p className="text-xs text-slate-400 mt-0.5">{speaker.designation}</p>
                              )}
                              {speaker.company && (
                                <p className="text-xs text-slate-500">{speaker.company}</p>
                              )}
                              {speaker.talk_title && (
                                <p className="text-xs text-primary/80 mt-1 italic">{speaker.talk_title}</p>
                              )}
                              <div className="flex gap-3 mt-2">
                                {speaker.linkedin_url && (
                                  <a
                                    href={speaker.linkedin_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[10px] font-bold text-primary hover:text-accent transition-colors"
                                  >
                                    LINKEDIN ↗
                                  </a>
                                )}
                                {speaker.wikipedia_url && (
                                  <a
                                    href={speaker.wikipedia_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="text-[10px] font-bold text-slate-400 hover:text-slate-200 transition-colors"
                                  >
                                    WIKIPEDIA ↗
                                  </a>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = (status || "unknown").toLowerCase();
  let classes = "inline-block px-3 py-1 text-[10px] font-bold rounded-full border ";
  if (s === "upcoming") {
    classes += "bg-accent/20 text-accent border-accent/30";
  } else if (s === "live" || s === "ongoing") {
    classes += "bg-primary/20 text-primary border-primary/30";
  } else {
    classes += "bg-white/5 text-slate-400 border-white/10";
  }
  return <span className={classes}>{status?.toUpperCase() || "UNKNOWN"}</span>;
}
