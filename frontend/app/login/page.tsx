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
    <main className="mx-auto flex min-h-screen w-full max-w-md items-center px-6 py-10">
      <form onSubmit={onSubmit} className="frost w-full rounded-3xl p-8 shadow-xl shadow-cyan/10">
        <p className="text-xs uppercase tracking-[0.2em] text-cyan">AI Event Agent</p>
        <h1 className="mt-3 text-3xl font-semibold">Sign in</h1>
        <p className="mt-2 text-sm text-slate-300/80">Use `user` or `super_admin` credentials.</p>

        <label className="mt-7 block text-sm text-slate-200">Username</label>
        <input
          className="mt-2 w-full rounded-xl border border-slate-300/25 bg-slate-950/50 px-4 py-3 outline-none focus:border-cyan"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="user"
          required
        />

        <label className="mt-5 block text-sm text-slate-200">Password</label>
        <input
          type="password"
          className="mt-2 w-full rounded-xl border border-slate-300/25 bg-slate-950/50 px-4 py-3 outline-none focus:border-cyan"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
        />

        {error ? <p className="mt-4 text-sm text-ember">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded-xl bg-cyan px-4 py-3 font-semibold text-ink transition hover:brightness-110 disabled:opacity-70"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}
