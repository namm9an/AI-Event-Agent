"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { setSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("user");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(username.trim(), password);
      setSession(data.access_token, data.role);
      router.push(data.role === "super_admin" ? "/settings" : "/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed.";
      if (message.includes("Failed to fetch")) {
        setError("Login failed: API not reachable. Check NEXT_PUBLIC_API_URL and backend server.");
      } else {
        setError("Login failed. Check username/password.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="scout-black relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Corner teal glow */}
      <div className="corner-glow" />
      {/* Dots overlay */}
      <div className="dots-overlay-login" />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[420px] mx-4">
        <div className="glass-card rounded-2xl px-10 py-12">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <span className="font-display font-bold text-sm text-black tracking-wider">S</span>
            </div>
            <div className="mt-2.5 flex items-center gap-1.5">
              <span className="font-display text-[13px] font-semibold text-white/90 tracking-[0.12em] uppercase">
                AI Event Scout
              </span>
            </div>
          </div>

          {/* Headline */}
          <h1 className="font-display text-[28px] font-bold text-white text-center mb-2">
            Sign in
          </h1>
          <p className="text-[13px] text-white/45 text-center leading-relaxed mb-8">
            Use your team credentials to access the dashboard
          </p>

          {/* Form */}
          <form onSubmit={onSubmit} className="flex flex-col gap-3.5">
            <div>
              <label className="block text-[11px] text-white/45 uppercase tracking-[0.1em] mb-1.5">
                Username
              </label>
              <input
                className="scout-input"
                type="text"
                placeholder="Enter your username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="block text-[11px] text-white/45 uppercase tracking-[0.1em] mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  className="scout-input pr-16"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] text-white/40 hover:text-white/70 transition-colors uppercase tracking-wider"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-[13px] text-ember mt-1">{error}</p>
            )}

            <div className="mt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-black border-none rounded-lg py-3.5 px-6 font-display font-bold text-[14px] uppercase tracking-[0.12em] cursor-pointer transition-all hover:bg-accent hover:-translate-y-px active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </div>
          </form>

          {/* Role pills — added in next commit */}
        </div>
      </div>
    </div>
  );
}
