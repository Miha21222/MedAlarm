import type { ReactNode } from "react";

export function SectionHeader({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <div className="section-heading">
      <span>{icon}</span>
      <h2>{title}</h2>
    </div>
  );
}
