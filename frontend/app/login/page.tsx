"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { setSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("user");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(username, password);
      setSession(data.access_token, data.role);
      router.push(data.role === "super_admin" ? "/settings" : "/dashboard");
    } catch (err) {
      setError("Login failed. Check username/password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-screen w-full max-w-6xl items-center gap-6 px-4 py-10 sm:px-8 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="panel rounded-3xl p-8 sm:p-10">
        <p className="panel-title">Agent Access</p>
        <h1 className="heading-display mt-3 text-4xl sm:text-5xl">Welcome to Scout Console</h1>
        <p className="mt-4 max-w-lg text-base text-[color:var(--text-soft)]">
          Monitor live event intelligence, inspect speakers, review daily PDF history, and tune scraping strategy from one command center.
        </p>
        <div className="mt-8 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setUsername("user")}
            className={`metric-card rounded-xl p-4 text-left transition ${
              username === "user" ? "border-cyan shadow-lg shadow-cyan/20" : ""
            }`}
          >
            <p className="panel-title">Mode</p>
            <p className="mt-2 text-lg font-semibold">Read-only User</p>
          </button>
          <button
            type="button"
            onClick={() => setUsername("super_admin")}
            className={`metric-card rounded-xl p-4 text-left transition ${
              username === "super_admin" ? "border-cyan shadow-lg shadow-cyan/20" : ""
            }`}
          >
            <p className="panel-title">Mode</p>
            <p className="mt-2 text-lg font-semibold">Super Admin</p>
          </button>
        </div>
      </section>

      <form onSubmit={onSubmit} className="panel w-full rounded-3xl p-8">
        <p className="panel-title">Authentication</p>
        <h2 className="heading-display mt-3 text-3xl">Sign in</h2>
        <p className="mt-2 text-sm text-slate-300/80">Use `user` or `super_admin` credentials.</p>

        <label className="mt-7 block text-sm text-slate-200">Username</label>
        <input
          className="input-shell mt-2 w-full rounded-xl px-4 py-3 outline-none focus:border-cyan"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="user"
          required
        />

        <label className="mt-5 block text-sm text-slate-200">Password</label>
        <input
          type="password"
          className="input-shell mt-2 w-full rounded-xl px-4 py-3 outline-none focus:border-cyan"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
        />

        {error ? <p className="mt-4 text-sm text-ember">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary mt-6 w-full rounded-xl px-4 py-3 font-semibold transition hover:brightness-110 disabled:opacity-70"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
