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

      {/* Body placeholder */}
      <main className="relative flex-1 flex flex-col pt-20" />
    </div>
  );
}
