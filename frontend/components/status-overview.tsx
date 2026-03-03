interface StatusOverviewProps {
  events: number;
  speakers: number;
  reports: number;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="frost rounded-2xl p-4">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-300/80">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

export default function StatusOverview({ events, speakers, reports }: StatusOverviewProps) {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      <StatCard label="Events" value={events} />
      <StatCard label="Speakers" value={speakers} />
      <StatCard label="Reports" value={reports} />
    </section>
  );
}
