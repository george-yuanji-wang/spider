"use client";

import { useRef, useState, useCallback } from "react";

interface Props {
  size?:     number;
  onChange?: (x: number, y: number) => void;
}

export default function AnalogStick({ size = 210, onChange }: Props) {
  const [pos,      setPos]      = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const radius    = size / 2;
  const thumbR    = size * 0.11;
  const maxTravel = radius - thumbR - 6;

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setDragging(true);

    const onMove = (ev: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const cx = rect.left + rect.width  / 2;
      const cy = rect.top  + rect.height / 2;
      let dx = ev.clientX - cx;
      let dy = ev.clientY - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > maxTravel) {
        dx = (dx / dist) * maxTravel;
        dy = (dy / dist) * maxTravel;
      }
      setPos({ x: dx, y: dy });
      onChange?.(dx / maxTravel, dy / maxTravel);
    };

    const onUp = () => {
      setDragging(false);
      setPos({ x: 0, y: 0 });
      onChange?.(0, 0);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup",   onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup",   onUp);
  }, [maxTravel, onChange]);

  const radialLines = Array.from({ length: 8 }, (_, i) => {
    const angle  = (i * Math.PI) / 4;
    const innerR = radius * 0.12;
    const outerR = radius * 0.88;
    return {
      x1: radius + Math.cos(angle) * innerR,
      y1: radius + Math.sin(angle) * innerR,
      x2: radius + Math.cos(angle) * outerR,
      y2: radius + Math.sin(angle) * outerR,
    };
  });

  const thumbX = radius + pos.x;
  const thumbY = radius + pos.y;

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      style={{
        width:           size,
        height:          size,
        borderRadius:    "50%",
        backgroundColor: "#151210",
        border:          `1.5px solid ${dragging ? "#5C7A8A" : "#516067"}`,
        position:        "relative",
        cursor:          dragging ? "grabbing" : "crosshair",
        overflow:        "hidden",
        transition:      "border-color 0.15s",
        userSelect:      "none",
        flexShrink:      0,
      }}
    >
      <svg
        width={size}
        height={size}
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        {/* Concentric rings */}
        {[0.33, 0.6, 0.85].map(r => (
          <circle
            key={r}
            cx={radius} cy={radius}
            r={radius * r}
            fill="none"
            stroke="#8AABB8"
            strokeWidth="0.5"
            opacity={r === 0.33 ? "0.4" : r === 0.6 ? "0.28" : "0.18"}
          />
        ))}

        {/* Radial lines */}
        {radialLines.map((l, i) => (
          <line
            key={i}
            x1={l.x1} y1={l.y1}
            x2={l.x2} y2={l.y2}
            stroke="#8AABB8"
            strokeWidth="0.5"
            opacity="0.28"
          />
        ))}

        {/* Cardinal ticks */}
        {[0, Math.PI / 2, Math.PI, (3 * Math.PI) / 2].map((angle, i) => (
          <circle
            key={i}
            cx={radius + Math.cos(angle) * (radius * 0.78)}
            cy={radius + Math.sin(angle) * (radius * 0.78)}
            r="2"
            fill="#8AABB8"
            opacity="0.5"
          />
        ))}

        {/* Travel line */}
        {dragging && (
          <line
            x1={radius} y1={radius}
            x2={thumbX} y2={thumbY}
            stroke="#8AABB8"
            strokeWidth="1"
            opacity="0.5"
          />
        )}

        {/* Thumb */}
        <circle
          cx={thumbX} cy={thumbY}
          r={thumbR}
          fill={dragging ? "#1A2530" : "#2A2420"}
          stroke={dragging ? "#8AABB8" : "#516067"}
          strokeWidth="1.5"
          style={{
            transition: dragging
              ? "none"
              : "cx 0.25s cubic-bezier(0.34,1.56,0.64,1), cy 0.25s cubic-bezier(0.34,1.56,0.64,1)",
          }}
        />

        {/* Center dot */}
        <circle
          cx={radius} cy={radius}
          r="2.5"
          fill="#8AABB8"
          opacity="0.45"
        />
      </svg>
    </div>
  );
}