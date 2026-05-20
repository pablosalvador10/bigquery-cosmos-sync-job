import type { ToolEvent } from "../types";

type Props = { event: ToolEvent | null };

export function ToolCard({ event }: Props) {
  if (!event) return null;

  return (
    <section className="tool-card">
      <h3>Tool Event</h3>
      <p><strong>Tool:</strong> {event.tool}</p>
      <p><strong>Status:</strong> {event.status}</p>
    </section>
  );
}
