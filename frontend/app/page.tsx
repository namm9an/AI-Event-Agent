import Link from "next/link";
import HomeRouter from "@/components/home-router";

export default function HomePage() {
  return (
    <div className="scout-black relative overflow-x-hidden min-h-screen flex flex-col">
      <HomeRouter />

      {/* Navigation */}
      <header className="fixed top-0 w-full z-50 border-b border-white/10 bg-black/80 backdrop-blur-md">
        <nav className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <span className="text-black font-display font-bold text-xs">S</span>
            </div>
            <span className="font-display font-bold text-xl tracking-widest uppercase text-white">Scout</span>
          </div>

          <div className="hidden md:flex items-center gap-10">
            <Link href="/" className="text-xs font-medium hover:text-primary transition-colors uppercase tracking-widest text-white/60">Home</Link>
            <Link href="/dashboard" className="text-xs font-medium hover:text-primary transition-colors uppercase tracking-widest text-white/60">Dashboard</Link>
            <Link href="/dashboard" className="text-xs font-medium hover:text-primary transition-colors uppercase tracking-widest text-white/60">Reports</Link>
          </div>

          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-5 py-2.5 border border-primary text-primary rounded-full text-xs font-display font-bold uppercase tracking-widest hover:bg-primary hover:text-black transition-all"
          >
            Open Dashboard ↗
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <main className="relative flex-1 flex flex-col pt-20">
        {/* Halftone blob */}
        <div className="absolute top-1/4 -right-20 w-[600px] h-[600px] halftone-blob pointer-events-none" />
        <div className="absolute top-0 right-0 w-1/2 h-full dots-pattern opacity-25 pointer-events-none" />

        <section className="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-12 w-full flex flex-col justify-center min-h-[85vh]">
          <div className="w-full lg:w-[80%]">
            <h1 className="font-display text-5xl md:text-7xl lg:text-[6rem] font-bold leading-[1.05] tracking-tighter uppercase mb-12 text-white">
              Discover Events.<br />
              <span className="text-primary">/</span> Find Speakers.<br />
              <span className="text-accent">/</span> Stay Ahead.
            </h1>
          </div>

          <div className="max-w-xl">
            <p className="text-lg text-white/50 font-light leading-relaxed mb-10">
              Nemotron-powered intelligence for India&apos;s AI/ML ecosystem.<br />
              Daily reports, speaker profiles, and event tracking —{" "}
              <span className="text-white font-medium">automated.</span>
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/login"
                className="px-8 py-4 bg-primary text-black font-display font-bold text-sm uppercase tracking-[0.2em] rounded-lg hover:bg-accent transition-colors"
              >
                Login to Scout ↗
              </Link>
              <Link
                href="/dashboard"
                className="px-8 py-4 border border-white/20 text-white font-display font-bold text-sm uppercase tracking-[0.2em] rounded-lg hover:bg-white/10 transition-colors"
              >
                View Reports
              </Link>
            </div>
          </div>
        </section>

        {/* Stats bar */}
        <section className="relative z-10 border-y border-white/10 bg-black/50 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-6 py-10">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {[
                { value: "200+", label: "Events Tracked" },
                { value: "500+", label: "Speakers Indexed" },
                { value: "Daily", label: "PDF Reports" },
                { value: "India", label: "Focused Engine" },
              ].map((stat) => (
                <div key={stat.label} className="flex flex-col md:flex-row md:items-center gap-3">
                  <span className="text-2xl font-display font-bold text-primary">{stat.value}</span>
                  <span className="text-xs uppercase tracking-[0.2em] text-white/40">{stat.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
