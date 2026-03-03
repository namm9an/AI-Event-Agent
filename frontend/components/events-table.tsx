import type { Event } from "@/lib/types";

interface EventsTableProps {
  events: Event[];
}

export default function EventsTable({ events }: EventsTableProps) {
  return (
    <section className="panel rounded-2xl p-4">
      <h2 className="panel-title">Events</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="table-shell min-w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Date</th>
              <th className="px-3 py-2">City</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Speakers</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td className="px-3 py-3">
                  <p className="font-medium">{event.name}</p>
                  <a className="text-xs text-cyan hover:underline" href={event.url} target="_blank" rel="noreferrer">
                    source link
                  </a>
                </td>
                <td className="px-3 py-3">{event.date_text || "-"}</td>
                <td className="px-3 py-3">{event.city || "-"}</td>
                <td className="px-3 py-3">{event.status || "Unknown"}</td>
                <td className="px-3 py-3">{event.speakers?.length ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
