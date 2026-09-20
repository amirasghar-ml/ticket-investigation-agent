import type { AgentEvent } from "../types";

export function Timeline({ events }: { events: AgentEvent[] }) {
  if (events.length === 0) {
    return null;
  }
  return (
    <div className="timeline">
      {events.map((event, index) => (
        <div className="event" key={`${event.type}-${index}`}>
          <strong>{event.title}</strong>
          <span>{event.stage}</span>
        </div>
      ))}
    </div>
  );
}
