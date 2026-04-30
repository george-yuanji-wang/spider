"use client";

import { DriveMode } from "@/lib/ctrl";

interface Props {
  mode:     DriveMode;
  onChange: (m: DriveMode) => void;
}

export default function ModeLever({ mode, onChange }: Props) {
  const isAuto = mode === "auto";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>

      <span style={{
        fontFamily:    "StackSansNotch-Regular, sans-serif",
        fontSize:      "9px",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color:         !isAuto ? "#8AABB8" : "#2A2420",
        transition:    "color 0.3s",
      }}>
        Manual
      </span>

      <div
        onClick={() => onChange(isAuto ? "manual" : "auto")}
        style={{
          width:           "36px",
          height:          "58px",
          borderRadius:    "18px",
          backgroundColor: isAuto ? "#1C1710" : "#101418",
          border:          `1.5px solid ${isAuto ? "#C38D4F" : "#516067"}`,
          position:        "relative",
          cursor:          "pointer",
          transition:      "background-color 0.3s, border-color 0.3s",
          flexShrink:      0,
        }}
      >
        <div style={{
          position:        "absolute",
          left:            "50%",
          top:             "50%",
          transform:       "translate(-50%, -50%)",
          width:           "10px",
          height:          "1px",
          backgroundColor: "#2A2420",
        }} />

        <div style={{
          position:        "absolute",
          left:            "50%",
          top:             isAuto ? "calc(100% - 10px)" : "10px",
          transform:       "translate(-50%, -50%)",
          width:           "28px",
          height:          "20px",
          borderRadius:    "10px",
          backgroundColor: isAuto ? "#C38D4F" : "#516067",
          border:          `1px solid ${isAuto ? "#E0B07A" : "#7A8FA0"}`,
          transition:      "top 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.3s, border-color 0.3s",
          display:         "flex",
          alignItems:      "center",
          justifyContent:  "center",
          flexDirection:   "column",
          gap:             "3px",
        }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{ width: "14px", height: "1px", borderRadius: "1px", backgroundColor: "#1E1B17", opacity: 0.5 }} />
          ))}
        </div>
      </div>

      <span style={{
        fontFamily:    "StackSansNotch-Regular, sans-serif",
        fontSize:      "9px",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color:         isAuto ? "#C38D4F" : "#2A2420",
        transition:    "color 0.3s",
      }}>
        Auto
      </span>

    </div>
  );
}