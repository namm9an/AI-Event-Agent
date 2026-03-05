interface StatusOverviewProps {
  events: number;
  speakers: number;
  reports: number;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="glass-card p-8 rounded-xl">
      <p className="font-display text-slate-400 text-xs font-bold tracking-widest mb-3">{label}</p>
      <p className="font-display text-4xl font-bold text-primary" style={{ textShadow: "0 0 15px rgba(26,213,255,0.4)" }}>{value}</p>
    </div>
  );
}

export default function StatusOverview({ events, speakers, reports }: StatusOverviewProps) {
  return (
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
      <StatCard label="EVENTS TRACKED" value={events} />
      <StatCard label="SPEAKERS INDEXED" value={speakers} />
      <StatCard label="DAILY REPORTS" value={reports} />
    </section>
  );
}
