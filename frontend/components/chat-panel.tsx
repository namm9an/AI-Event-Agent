"use client";

import { FormEvent, useState } from "react";

import { api } from "@/lib/api";

interface ChatPanelProps {
  token: string;
  activeReportId?: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPanel({ token, activeReportId }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const nextMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const response = await api.chat(token, {
        message: text,
        history: nextMessages,
        report_id: activeReportId
      });
      setMessages((prev) => [...prev, { role: "assistant", content: response.response }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Chat failed. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel rounded-2xl p-4">
      <h2 className="panel-title">Q/A Console</h2>
      <div className="mt-4 h-72 space-y-3 overflow-y-auto rounded-xl border border-white/10 bg-black/25 p-3">
        {messages.length === 0 ? (
          <p className="text-sm text-slate-300/80">Ask about events, speakers, topics, or selected report.</p>
        ) : (
          messages.map((msg, i) => (
            <div key={`${msg.role}-${i}`} className={msg.role === "user" ? "text-right" : "text-left"}>
              <span
                className={`inline-block max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  msg.role === "user" ? "bg-cyan text-slate-900" : "bg-white/10 text-slate-100"
                }`}
              >
                {msg.content}
              </span>
            </div>
          ))
        )}
      </div>
      <form className="mt-3 flex gap-2" onSubmit={onSubmit}>
        <input
          className="input-shell w-full rounded-xl px-3 py-2 text-sm outline-none focus:border-cyan"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask from selected report..."
        />
        <button className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold" disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </form>
    </section>
  );
}
