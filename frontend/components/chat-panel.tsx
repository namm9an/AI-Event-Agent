"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

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
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
        report_id: activeReportId,
      });
      setMessages((prev) => [...prev, { role: "assistant", content: response.response }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Chat failed. Try again." }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="glass-card rounded-xl flex flex-col h-[400px]">
      <div className="p-6 border-b border-white/10 flex items-center gap-2">
        <h3 className="font-display text-sm font-bold tracking-widest text-slate-100 uppercase">
          Intelligence Q&amp;A
        </h3>
      </div>
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-4 bg-black/30">
        {messages.length === 0 ? (
          <div className="flex flex-col gap-1 max-w-[80%]">
            <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-tl-none">
              <p className="text-sm text-slate-300">
                Ready to analyze event intelligence. Ask about events, speakers, topics, or the selected report.
              </p>
            </div>
            <span className="text-[9px] font-bold text-slate-500 ml-1 uppercase">AI Scout Assistant</span>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={`${msg.role}-${i}`}
              className={`flex flex-col gap-1 max-w-[80%] ${msg.role === "user" ? "self-end" : ""}`}
            >
              <div
                className={`p-4 rounded-2xl ${msg.role === "user"
                    ? "bg-primary rounded-tr-none"
                    : "bg-white/5 border border-white/10 rounded-tl-none"
                  }`}
              >
                {msg.role === "user" ? (
                  <p className="text-sm font-medium text-black">{msg.content}</p>
                ) : (
                  <div className="text-sm text-slate-300 space-y-1">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <span className="block">{children}</span>,
                        strong: ({ children }) => <strong className="font-bold text-slate-100">{children}</strong>,
                        ul: ({ children }) => <ul className="list-disc list-inside mt-1 space-y-1">{children}</ul>,
                        li: ({ children }) => <li>{children}</li>,
                        a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">{children}</a>,
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
              <span
                className={`text-[9px] font-bold text-slate-500 uppercase ${msg.role === "user" ? "mr-1 text-right" : "ml-1"
                  }`}
              >
                {msg.role === "user" ? "YOU" : "AI Scout Assistant"}
              </span>
            </div>
          ))
        )}
        {loading && (
          <div className="flex flex-col gap-1 max-w-[80%]">
            <div className="bg-white/5 border border-white/10 p-4 rounded-2xl rounded-tl-none">
              <p className="text-sm text-slate-400">Analyzing...</p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="p-4 border-t border-white/10 flex gap-3" onSubmit={onSubmit}>
        <input
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary/50 text-slate-100 placeholder:text-slate-600"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask intelligence query..."
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-primary text-black font-display font-bold text-xs tracking-widest px-6 py-2 rounded-lg hover:brightness-110 transition-all disabled:opacity-50"
        >
          SEND
        </button>
      </form>
    </div>
  );
}
