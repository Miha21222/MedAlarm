import { Mic, Square } from "lucide-react";

export function MicButton({
  supported,
  recording,
  onClick,
  label,
}: {
  supported: boolean;
  recording: boolean;
  onClick: () => void;
  label: string;
}) {
  if (!supported) return null;
  return (
    <button type="button" className={`mic-btn${recording ? " recording" : ""}`} onClick={onClick} aria-label={label}>
      {recording ? <Square size={16} /> : <Mic size={16} />}
    </button>
  );
}
