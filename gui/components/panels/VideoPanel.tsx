"use client";

import { useRef, useEffect, useState } from "react";
import { useTel }   from "@/context/TelContext";
import Toggle       from "@/components/ui/Toggle";

export default function VideoPanel() {
  const { tel } = useTel();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [displayOn,     setDisplayOn]     = useState(false);
  const [ballOverlayOn, setBallOverlayOn] = useState(false);
  const [pathOverlayOn, setPathOverlayOn] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, 640, 480);

    if (ballOverlayOn && tel.ball) {
      const { cx, cy, x, y, w, h } = tel.ball;

      if (cx !== null && cy !== null) {
        ctx.strokeStyle = "white";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(cx - 12, cy);
        ctx.lineTo(cx + 12, cy);
        ctx.moveTo(cx, cy - 12);
        ctx.lineTo(cx, cy + 12);
        ctx.stroke();
      }

      if (x !== null && y !== null && w !== null && h !== null) {
        ctx.strokeStyle = "white";
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);
      }
    }

    if (pathOverlayOn && tel.path.length > 0) {
      ctx.strokeStyle = "#CC3333";
      ctx.lineWidth = 2;
      ctx.beginPath();
      let started = false;
      for (const point of tel.path) {
        if (point.x === null || point.y === null) {
          started = false;
          continue;
        }
        if (!started) {
          ctx.moveTo(point.x, point.y);
          started = true;
        } else {
          ctx.lineTo(point.x, point.y);
        }
      }
      ctx.stroke();
    }
  }, [ballOverlayOn, pathOverlayOn, tel.ball, tel.path]);

  return (
    <div className="flex flex-col items-center gap-3">

      {/* Top bar: title left, toggles right */}
      <div className="flex items-center justify-between" style={{ width: 640 }}>
        <span
          className="font-stack-semibold text-text-primary tracking-widest uppercase"
          style={{ fontSize: "13px" }}
        >
          Video Feed
        </span>
        <div className="flex items-center gap-5">
          <Toggle label="Display"      enabled={displayOn}     onToggle={() => setDisplayOn(v => !v)}     />
          <Toggle label="Ball Overlay" enabled={ballOverlayOn} onToggle={() => setBallOverlayOn(v => !v)} />
          <Toggle label="Path Overlay" enabled={pathOverlayOn} onToggle={() => setPathOverlayOn(v => !v)} />
        </div>
      </div>

      {/* Video area */}
      <div className="relative flex-shrink-0" style={{ width: 640, height: 480 }}>

        {displayOn ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src="/api/stream"
            alt="live feed"
            style={{
              position:  "absolute",
              inset:     0,
              width:     "100%",
              height:    "100%",
              objectFit: "cover",
            }}
          />
        ) : (
          <div
            className="absolute inset-0 flex items-center justify-center"
            style={{ backgroundColor: "#0E0C0A" }}
          >
            <span className="font-stack-light text-text-secondary text-sm tracking-widest">
              NOT AVAILABLE
            </span>
          </div>
        )}

        {/* Overlay canvas always on top */}
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className="absolute inset-0 pointer-events-none"
        />

      </div>
    </div>
  );
}