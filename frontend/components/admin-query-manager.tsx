"use client";

import { FormEvent, useState } from "react";

import { api } from "@/lib/api";
import type { SearchQuery } from "@/lib/types";

interface AdminQueryManagerProps {
  token: string;
  queries: SearchQuery[];
  onRefresh: () => Promise<void>;
}

export default function AdminQueryManager({ token, queries, onRefresh }: AdminQueryManagerProps) {
  const [query, setQuery] = useState("");
  const [topic, setTopic] = useState("General");

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    await api.createAdminQuery(token, { query: query.trim(), topic: topic.trim() || "General", is_active: true, priority: 50 });
    setQuery("");
    setTopic("General");
    await onRefresh();
  }

  async function onToggle(item: SearchQuery) {
    await api.updateAdminQuery(token, item.id, { is_active: !item.is_active });
    await onRefresh();
  }

  async function onDelete(id: string) {
    await api.deleteAdminQuery(token, id);
    await onRefresh();
  }

  return (
    <section className="glass-card rounded-xl p-8">
      <div className="flex items-center gap-2 mb-6">
        <h3 className="text-xs font-bold tracking-[0.2em] uppercase text-slate-400">Query Controls</h3>
      </div>

      <form onSubmit={onCreate} className="flex flex-col md:flex-row gap-4 mb-10">
        <input
          className="scout-input flex-1 h-12 rounded-lg px-4"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. frontier model summit india 2026"
          required
        />
        <input
          className="scout-input w-full md:w-48 h-12 rounded-lg px-4"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic"
          required
        />
        <button
          type="submit"
          className="bg-primary text-black font-bold h-12 px-8 rounded-lg flex items-center justify-center gap-2 hover:brightness-110 font-display uppercase tracking-widest text-sm whitespace-nowrap"
        >
          ADD QUERY
        </button>
      </form>

      <div className="space-y-3">
        {queries.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-6">No queries yet. Add one above.</p>
        ) : (
          queries.map((item) => (
            <div
              key={item.id}
              className={`flex flex-wrap items-center justify-between p-4 border bg-white/[0.02] rounded-lg transition-all ${item.is_active
                  ? "border-white/5"
                  : "border-white/5 opacity-50"
                }`}
            >
              <div className="flex items-center gap-6 min-w-0">
                <p className="text-sm font-medium text-slate-100 truncate">{item.query}</p>
                <span className="px-3 py-1 bg-primary/10 text-primary text-[10px] font-bold rounded-full uppercase tracking-wider border border-primary/20 shrink-0">
                  {item.topic}
                </span>
              </div>
              <div className="flex gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => onToggle(item)}
                  className={`h-9 px-4 text-xs font-bold rounded transition-colors uppercase ${item.is_active
                      ? "text-slate-400 bg-white/5 hover:bg-white/10"
                      : "text-primary bg-primary/10 hover:bg-primary/20"
                    }`}
                >
                  {item.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(item.id)}
                  className="h-9 px-4 text-[#ff7d93] border border-[#ff7d93]/30 text-xs font-bold rounded hover:bg-[#ff7d93]/5 transition-colors uppercase"
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
