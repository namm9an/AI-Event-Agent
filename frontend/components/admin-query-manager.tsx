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
    await api.createAdminQuery(token, {
      query: query.trim(),
      topic: topic.trim() || "General",
      is_active: true,
      priority: 50
    });
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
    <section className="frost rounded-2xl p-4">
      <h2 className="section-title text-sm uppercase tracking-[0.2em] text-cyan">Query Controls</h2>

      <form className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_140px]" onSubmit={onCreate}>
        <input
          className="rounded-xl border border-white/20 bg-black/25 px-3 py-2 text-sm outline-none focus:border-cyan"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="frontier model summit india 2026"
          required
        />
        <input
          className="rounded-xl border border-white/20 bg-black/25 px-3 py-2 text-sm outline-none focus:border-cyan"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Topic"
          required
        />
        <button className="rounded-xl bg-cyan px-4 py-2 text-sm font-semibold text-ink">Add query</button>
      </form>

      <div className="mt-4 space-y-2">
        {queries.map((item) => (
          <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-white/15 px-3 py-2">
            <div>
              <p className="text-sm font-medium">{item.query}</p>
              <p className="text-xs text-slate-300/80">{item.topic}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className="rounded-lg border border-white/20 px-3 py-1 text-xs"
                onClick={() => onToggle(item)}
              >
                {item.is_active ? "Disable" : "Enable"}
              </button>
              <button
                type="button"
                className="rounded-lg border border-ember/70 px-3 py-1 text-xs text-ember"
                onClick={() => onDelete(item.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
