import type { ReactNode } from "react";

export function SectionHeader({ icon, title, count }: { icon: ReactNode; title: string; count: number }) {
  return (
    <div className="section-heading">
      <span>{icon}</span>
      <h2>{title}</h2>
      <strong>{count}</strong>
    </div>
  );
}
