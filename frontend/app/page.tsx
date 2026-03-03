import Link from "next/link";

import HomeRouter from "@/components/home-router";

export default function HomePage() {
  return (
    <main className="home-stage mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center px-4 py-10 sm:px-8 lg:px-10">
      <section className="hero-card relative w-full rounded-[2rem] p-6 sm:p-10 lg:p-14">
        <HomeRouter />

        <div className="mb-6 inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] chip">
          Scout Intelligence Stack
        </div>

        <h1 className="heading-display max-w-4xl text-3xl leading-[1.02] text-white sm:text-5xl">
          Move from random event hunting to a daily intelligence brief your team can use
        </h1>

        <p className="mt-6 max-w-3xl text-base leading-relaxed text-[color:var(--text-soft)] sm:text-xl">
          AI Event Agent tracks speakers, topic links, public profiles, and talk narratives across your configured sectors.
          Super admins can tune filters and schedules. Users get fresh daily reports and searchable history.
        </p>

        <div className="mt-9 flex flex-wrap gap-4">
          <Link
            href="/login"
            className="rounded-xl bg-[color:var(--accent)] px-6 py-3 text-base font-semibold text-slate-900 transition hover:translate-y-[-1px] hover:brightness-110"
          >
            Login to Scout
          </Link>
          <Link
            href="/dashboard"
            className="rounded-xl border border-white/35 px-6 py-3 text-base font-semibold text-white transition hover:bg-white/10"
          >
            Open Dashboard
          </Link>
        </div>

        <div className="mt-9 grid gap-3 sm:grid-cols-3">
          <article className="metric-card rounded-xl p-4">
            <p className="text-2xl font-bold heading-display">00:00 IST</p>
            <p className="mt-1 text-sm text-[color:var(--text-soft)]">Daily scrape window</p>
          </article>
          <article className="metric-card rounded-xl p-4">
            <p className="text-2xl font-bold heading-display">12:00 IST</p>
            <p className="mt-1 text-sm text-[color:var(--text-soft)]">PDF report generation</p>
          </article>
          <article className="metric-card rounded-xl p-4">
            <p className="text-2xl font-bold heading-display">Nemotron</p>
            <p className="mt-1 text-sm text-[color:var(--text-soft)]">Open-source extraction core</p>
          </article>
        </div>
      </section>
    </main>
  );
}
