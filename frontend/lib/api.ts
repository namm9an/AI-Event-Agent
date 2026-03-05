import type {
  Event,
  LoginResponse,
  MeResponse,
  ReportItem,
  Schedule,
  SearchQuery,
  Speaker
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010";

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers ?? {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store"
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Request failed: ${res.status}`);
  }

  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<LoginResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    }),

  me: (token: string) => request<MeResponse>("/api/auth/me", {}, token),

  status: (token: string) =>
    request<{ crew_running: boolean; report_running: boolean; totals: Record<string, number> }>("/api/status", {}, token),

  events: (token: string) => request<{ events: Event[]; total: number }>("/api/events", {}, token),

  speakers: (token: string) =>
    request<{ speakers: Speaker[]; total: number }>("/api/speakers", {}, token),

  reports: (token: string) => request<{ reports: ReportItem[] }>("/api/reports", {}, token),

  downloadReport: async (token: string, reportId: string, fileName: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(body || `Download failed: ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = fileName || `report-${reportId}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  },

  viewReport: async (token: string, reportId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/reports/${reportId}/download`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store"
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(body || `View failed: ${res.status}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  },

  deleteReport: (token: string, reportId: string) =>
    request<{ deleted: boolean; id: string }>(
      `/api/reports/${reportId}`,
      { method: "DELETE" },
      token
    ),

  chat: (token: string, payload: { message: string; history: Array<{ role: string; content: string }>; report_id?: string }) =>
    request<{ response: string }>(
      "/api/chat",
      {
        method: "POST",
        body: JSON.stringify(payload)
      },
      token
    ),

  adminQueries: (token: string) => request<{ queries: SearchQuery[] }>("/api/admin/queries", {}, token),

  createAdminQuery: (
    token: string,
    payload: { query: string; topic: string; is_active: boolean; priority: number }
  ) =>
    request<SearchQuery>(
      "/api/admin/queries",
      {
        method: "POST",
        body: JSON.stringify(payload)
      },
      token
    ),

  updateAdminQuery: (token: string, queryId: string, payload: Partial<SearchQuery>) =>
    request<SearchQuery>(
      `/api/admin/queries/${queryId}`,
      {
        method: "PUT",
        body: JSON.stringify(payload)
      },
      token
    ),

  deleteAdminQuery: (token: string, queryId: string) =>
    request<{ deleted: boolean }>(
      `/api/admin/queries/${queryId}`,
      {
        method: "DELETE"
      },
      token
    ),

  adminSchedule: (token: string) => request<Schedule>("/api/admin/schedule", {}, token),

  updateAdminSchedule: (token: string, payload: Schedule) =>
    request<Schedule>(
      "/api/admin/schedule",
      {
        method: "PUT",
        body: JSON.stringify(payload)
      },
      token
    ),

  enrichLinkedin: (token: string) =>
    request<{ enriched: number; total_checked: number }>("/api/admin/enrich-linkedin", { method: "POST" }, token),

  runNow: (token: string) => request<{ started: boolean }>("/api/admin/run-now", { method: "POST" }, token),

  generateReportNow: (token: string) =>
    request<{ started: boolean }>("/api/admin/reports/generate-now", { method: "POST" }, token)
};
