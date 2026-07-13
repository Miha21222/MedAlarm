import type { ReactNode } from "react";
import emblemIcon from "../img/big_logo.png";

// MedAlarm's breathing brand-orbit logo treatment is kept as-is here (it reads
// better than PocketMind's plain spinner) — this is a file move, not a
// restyle. Also doubles as the retry-on-error screen via `children`.
export function LoadingState({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <main className="brand-state">
      <div className="brand-orbit">
        <img src={emblemIcon} alt="MedAlarm" />
      </div>
      <p>{label}</p>
      {children}
    </main>
  );
}
