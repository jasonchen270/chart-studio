import { useCallback, useEffect, useRef, useState } from "react";

type Props = {
  left: React.ReactNode;
  right: React.ReactNode;
  initialLeftPct?: number;
};

export function SplitPane({ left, right, initialLeftPct = 50 }: Props) {
  const [leftPct, setLeftPct] = useState(initialLeftPct);
  const dragging = useRef(false);
  const wrap = useRef<HTMLDivElement>(null);

  const onDown = useCallback(() => {
    dragging.current = true;
    document.body.style.cursor = "col-resize";
  }, []);

  useEffect(() => {
    function move(e: MouseEvent) {
      if (!dragging.current || !wrap.current) return;
      const rect = wrap.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      // Clamp so neither pane can collapse out of reach.
      setLeftPct(Math.min(80, Math.max(20, pct)));
    }
    function up() {
      dragging.current = false;
      document.body.style.cursor = "";
    }
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
    return () => {
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
  }, []);

  return (
    <div ref={wrap} className="split">
      <div style={{ width: `${leftPct}%` }} className="split-pane">{left}</div>
      <div className="split-gutter" onMouseDown={onDown} />
      <div style={{ width: `${100 - leftPct}%` }} className="split-pane">{right}</div>
    </div>
  );
}
