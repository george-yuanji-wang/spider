"use client";

import { useEffect, useRef } from "react";
import { useTel }          from "@/context/TelContext";
import { useCli }          from "@/context/CliContext";
import StatusIndicator     from "@/components/ui/StatusIndicator";
import CliOutput           from "@/components/ui/CliOutput";

const NODE_KEYS = ["camera", "motor", "tracker", "planner", "stream"] as const;
type NodeKey = typeof NODE_KEYS[number];

export default function TelemetryPanel() {
  const { tel }        = useTel();
  const { addMessage } = useCli();
  const prevTel        = useRef(tel);

  useEffect(() => {
    NODE_KEYS.forEach(node => {
      const key = `${node}_status` as `${NodeKey}_status`;
      if (prevTel.current[key] !== tel[key]) {
        addMessage(
          `${node.charAt(0).toUpperCase() + node.slice(1)} node: ${tel[key] ? "healthy" : "malfunctioning"}`
        );
      }
    });
    prevTel.current = tel;
  }, [tel.camera_status, tel.motor_status, tel.tracker_status, tel.planner_status, tel.stream_status]);

  const autoColor =
    tel.auto_state === "IDLE" || tel.auto_state === "DONE"
      ? "#516067"
      : "#C38D4F";

  const detectColor = tel.detect_mode === "ball" ? "#8AABB8" : "#A74A43";

  return (
    <div style={{
      display:       "flex",
      flexDirection: "column",
      height:        "100%",
      padding:       "8px 12px",
      boxSizing:     "border-box",
      gap:           "10px",
    }}>

      <span style={{
        fontFamily:    "StackSansNotch-SemiBold, sans-serif",
        fontSize:      "13px",
        letterSpacing: "0.12em",
        color:         "#D8CFC0",
        textTransform: "uppercase",
        flexShrink:    0,
      }}>
        Telemetry
      </span>

      <div style={{
        display:       "flex",
        flexDirection: "column",
        flex:          1,
        minHeight:     0,
        paddingLeft:   "8px",
        gap:           "10px",
      }}>

        {/* Node status indicators */}
        <div style={{
          display:             "grid",
          gridTemplateColumns: "1fr 1fr",
          gap:                 "6px 24px",
          flexShrink:          0,
        }}>
          <StatusIndicator label="Camera"  active={tel.camera_status}  fps={tel.camera_fps}  />
          <StatusIndicator label="Motor"   active={tel.motor_status}                         />
          <StatusIndicator label="Tracker" active={tel.tracker_status} fps={tel.tracker_fps} />
          <StatusIndicator label="Planner" active={tel.planner_status} fps={tel.planner_fps} />
          <StatusIndicator label="Stream"  active={tel.stream_status}                        />
        </div>

        {/* Auto state + detect mode */}
        <div style={{ display: "flex", flexDirection: "column", gap: "5px", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{
              fontFamily:    "StackSansNotch-Regular, sans-serif",
              fontSize:      "10px",
              letterSpacing: "0.1em",
              color:         "#9A9080",
              textTransform: "uppercase",
              width:         "52px",
              flexShrink:    0,
            }}>
              Auto
            </span>
            <span style={{
              fontFamily:    "StackSansNotch-Bold, sans-serif",
              fontSize:      "10px",
              letterSpacing: "0.08em",
              color:         autoColor,
              transition:    "color 0.3s",
            }}>
              {tel.auto_state}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{
              fontFamily:    "StackSansNotch-Regular, sans-serif",
              fontSize:      "10px",
              letterSpacing: "0.1em",
              color:         "#9A9080",
              textTransform: "uppercase",
              width:         "52px",
              flexShrink:    0,
            }}>
              Vision
            </span>
            <span style={{
              fontFamily:    "StackSansNotch-Bold, sans-serif",
              fontSize:      "10px",
              letterSpacing: "0.08em",
              color:         detectColor,
              transition:    "color 0.3s",
            }}>
              {tel.detect_mode}
            </span>
          </div>
        </div>

        {/* CLI */}
        <div style={{ flex: 1, minHeight: 0 }}>
          <CliOutput />
        </div>

      </div>
    </div>
  );
}