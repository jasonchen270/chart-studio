import type { TraceEvent } from "@/hooks/useGenerateStream";

export function TraceLog({ events }: { events: TraceEvent[] }) {
  if (events.length === 0) return null;
  return (
    <ol className="trace">
      {events.map((evt, i) => (
        <li key={i} className={`trace-${evt.type}`}>
          {renderEvent(evt)}
        </li>
      ))}
    </ol>
  );
}

function renderEvent(evt: TraceEvent) {
  switch (evt.type) {
    case "thought":
      return <span className="thought">{evt.text}</span>;
    case "tool_call":
      return (
        <span>
          <strong>→ {evt.name}</strong>
          <code>{JSON.stringify(evt.input)}</code>
        </span>
      );
    case "tool_result":
      return (
        <span>
          <strong>← {evt.name}</strong>
          <code>{truncate(JSON.stringify(evt.result), 160)}</code>
        </span>
      );
    case "code":
      return <em>Code ready ({evt.code.split("\n").length} lines)</em>;
    case "done":
      return <em>Done ({evt.stop_reason})</em>;
  }
}

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n) + "...";
}
