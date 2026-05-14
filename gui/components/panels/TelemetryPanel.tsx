"use client";

import { useEffect, useRef } from "react";
import { useTel }      from "@/context/TelContext";
import { useCli }      from "@/context/CliContext";
import { useCtrl }     from "@/context/CtrlContext";
import StatusIndicator from "@/components/ui/StatusIndicator";
import CliOutput       from "@/components/ui/CliOutput";

const NODE_KEYS = ["camera", "motor", "tracker", "planner", "stream"] as const;
type NodeKey = typeof NODE_KEYS[number];

const AUTO_STATES = [
  "SEARCH_BALL", "APPROACH_BALL", "CAPTURE",
  "SEARCH_MAT",  "APPROACH_MAT",  "DEPOSIT",
] as const;

const STATE_COLORS: Record<string, string> = {
  IDLE:          "#516067",
  SEARCH_BALL:   "#8AABB8",
  APPROACH_BALL: "#8AABB8",
  CAPTURE:       "#C38D4F",
  SEARCH_MAT:    "#A74A43",
  APPROACH_MAT:  "#A74A43",
  DEPOSIT:       "#A74A43",
  DONE:          "#4A7060",
};

export default function TelemetryPanel() {
  const { tel }        = useTel();
  const { ctrl }       = useCtrl();
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

  const isAuto      = ctrl.mode === "auto" && ctrl.armed;
  const autoColor   = STATE_COLORS[tel.auto_state] ?? "#516067";
  const detectColor = tel.detect_mode === "ball" ? "#8AABB8" : "#A74A43";

  const setAutoState = async (state: string) => {
    try {
      await fetch("/api/auto/state", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ state }),
      });
      addMessage(`Debug: jumping to ${state}`);
    } catch {
      addMessage("State override failed");
    }
  };

  const LABEL: React.CSSProperties = {
    fontFamily:    "StackSansNotch-Regular, sans-serif",
    fontSize:      "10px",
    letterSpacing: "0.1em",
    color:         "#9A9080",
    textTransform: "uppercase",
    width:         "52px",
    flexShrink:    0,
  };

  const VALUE = (color: string): React.CSSProperties => ({
    fontFamily:    "StackSansNotch-Bold, sans-serif",
    fontSize:      "10px",
    letterSpacing: "0.08em",
    color,
    transition:    "color 0.3s",
  });

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

        {/* Node status — 2 rows × 3 columns */}
        <div style={{
          display:             "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap:                 "6px 12px",
          flexShrink:          0,
        }}>
          <StatusIndicator label="Camera"  active={tel.camera_status}  fps={tel.camera_fps}  />
          <StatusIndicator label="Motor"   active={tel.motor_status}                         />
          <StatusIndicator label="Tracker" active={tel.tracker_status} fps={tel.tracker_fps} />
          <StatusIndicator label="Planner" active={tel.planner_status} fps={tel.planner_fps} />
          <StatusIndicator label="Stream"  active={tel.stream_status}                        />
        </div>

        <div style={{ display: "flex", alignItems: "stretch", gap: "12px", flexShrink: 0 }}>
     
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", gap: "5px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={LABEL}>Auto</span>
              <span style={VALUE(autoColor)}>{tel.auto_state}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={LABEL}>Vision</span>
              <span style={VALUE(detectColor)}>{tel.detect_mode}</span>
            </div>
          </div>

          <div style={{
            marginLeft:          "auto",
            display:             "grid",
            gridTemplateColumns: "repeat(3, 58px)",
            gridTemplateRows:    "1fr 1fr",
            gap:                 "3px",
            flexShrink:          0,
          }}>
            {(["SRCH B", "APPR B", "CAPTURE", "SRCH M", "APPR M", "DEPOSIT"] as const).map((label, i) => {
              const s        = AUTO_STATES[i];
              const isActive = tel.auto_state === s;
              const color    = STATE_COLORS[s];
              return (
                <button
                  key={s}
                  onClick={() => setAutoState(s)}
                  style={{
                    padding:         "0",
                    backgroundColor: isActive ? "#1E1B17" : "transparent",
                    border:          `1px solid ${isActive ? color : "#2A2420"}`,
                    borderRadius:    "3px",
                    color:           isActive ? color : "#3E3830",
                    fontFamily:      "StackSansNotch-Regular, sans-serif",
                    fontSize:        "7px",
                    letterSpacing:   "0.08em",
                    cursor:          "pointer",
                    transition:      "all 0.15s",
                    opacity:         isAuto ? 1 : 0.35,
                    textAlign:       "center",
                  }}
                >
                  {label}
                </button>
              );
            })}
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