import type { ReactNode } from "react";

// MedAlarm's breathing brand-orbit logo treatment is kept as-is here (it reads
// better than PocketMind's plain spinner) — this is a file move, not a
// restyle. Also doubles as the retry-on-error screen via `children`.
export function LoadingState({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <main className="brand-state">
      <div className="brand-orbit">
        <img src={`${import.meta.env.BASE_URL}logo.png`} alt="MedAlarm" />
      </div>
      <p>{label}</p>
      {children}
    </main>
  );
}
