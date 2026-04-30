"use client";

import { useRef, useState, useCallback } from "react";

interface Props {
  value:    number;
  onChange: (v: number) => void;
  height?:  number;
}

export default function SpeedBar({ value, onChange, height = 220 }: Props) {
  const [dragging, setDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);

  const thumbColor =
    value > 66 ? "#A74A43" :
    value > 33 ? "#C38D4F" : "#4A7060";

  const fillColor =
    value > 66 ? "#A74A43" :
    value > 33 ? "#C38D4F" : "#4A7060";

  const applyFromY = useCallback((clientY: number) => {
    const rect = trackRef.current?.getBoundingClientRect();
    if (!rect) return;
    const ratio = 1 - (clientY - rect.top) / rect.height;
    onChange(Math.round(Math.max(0, Math.min(100, ratio * 100))));
  }, [onChange]);

  const handleThumbMouseDown = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setDragging(true);
    const onMove = (ev: MouseEvent) => applyFromY(ev.clientY);
    const onUp   = () => {
      setDragging(false);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup",   onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup",   onUp);
  }, [applyFromY]);

  return (
    <div
      className="flex flex-col items-center"
      style={{ height, gap: "8px", flexShrink: 0 }}
    >
      <span
        style={{
          fontSize:      "9px",
          letterSpacing: "0.15em",
          fontFamily:    "StackSansNotch-Medium, sans-serif",
          color:         "#9A9080",
        }}
      >
        SPD
      </span>

      <div
        ref={trackRef}
        onClick={e => applyFromY(e.clientY)}
        style={{
          flex:            1,
          width:           "16px",
          borderRadius:    "9999px",
          backgroundColor: "#151210",
          border:          "1.5px solid #516067",
          position:        "relative",
          cursor:          "pointer",
        }}
      >
        {/* Fill */}
        <div
          style={{
            position:        "absolute",
            bottom:          0,
            left:            0,
            right:           0,
            height:          `${value}%`,
            borderRadius:    "9999px",
            backgroundColor: fillColor,
            opacity:         0.35,
            transition:      "background-color 0.4s",
          }}
        />

        {/* Thumb */}
        <div
          onMouseDown={handleThumbMouseDown}
          style={{
            position:        "absolute",
            left:            "50%",
            top:             `${(1 - value / 100) * 100}%`,
            transform:       "translate(-50%, -50%)",
            width:           dragging ? "22px" : "16px",
            height:          dragging ? "32px" : "24px",
            borderRadius:    "9999px",
            backgroundColor: thumbColor,
            border:          "1.5px solid #D8CFC0",
            transition:      "width 0.15s, height 0.15s, background-color 0.4s",
            cursor:          dragging ? "grabbing" : "grab",
            zIndex:          2,
          }}
        />
      </div>

      <span
        style={{
          fontSize:      "11px",
          letterSpacing: "0.05em",
          fontFamily:    "StackSansNotch-Bold, sans-serif",
          color:         thumbColor,
          transition:    "color 0.4s",
        }}
      >
        {value}
      </span>
    </div>
  );
}