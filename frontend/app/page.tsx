import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-8 px-6 py-20">
      <div className="frost w-full rounded-3xl p-10 text-center shadow-2xl shadow-cyan/10">
        <p className="mb-3 text-sm uppercase tracking-[0.22em] text-cyan">AI Event Agent</p>
        <h1 className="text-4xl font-semibold leading-tight sm:text-5xl">Scout-grade event intelligence for your team</h1>
        <p className="mx-auto mt-5 max-w-2xl text-base text-slate-200/80">
          Track speakers, topic links, and daily reports with Nemotron-powered enrichment.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <Link href="/login" className="rounded-xl bg-cyan px-5 py-3 font-semibold text-ink transition hover:scale-[1.02]">
            Go to Login
          </Link>
          <Link href="/dashboard" className="rounded-xl border border-slate-200/30 px-5 py-3 font-semibold transition hover:bg-white/10">
            Open Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
