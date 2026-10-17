/** Renders the three triage dimensions separately — never a single opaque score. */
export function PriorityBadge({
  urgency,
  evidence,
  location,
}: {
  urgency: number;
  evidence: number;
  location: number;
}) {
  const pct = (v: number) => `${Math.round(v * 100)}%`;
  const cell = "rounded px-2 py-1 text-xs font-medium";
  return (
    <div className="flex flex-wrap gap-2">
      <span className={`${cell} bg-rose-100 text-rose-800`} title="How soon a human should look">
        Urgency {pct(urgency)}
      </span>
      <span className={`${cell} bg-sky-100 text-sky-800`} title="Independent corroboration + extraction confidence">
        Evidence {pct(evidence)}
      </span>
      <span className={`${cell} bg-emerald-100 text-emerald-800`} title="How sure we are of the location">
        Location {pct(location)}
      </span>
    </div>
  );
}
