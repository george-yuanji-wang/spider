"use client";

interface Props {
  closed:   boolean;
  onChange: (closed: boolean) => void;
}

export default function ClawLever({ closed, onChange }: Props) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>

      <span style={{
        fontFamily:    "StackSansNotch-Regular, sans-serif",
        fontSize:      "9px",
        letterSpacing: "0.12em",
        textTransform: "uppercase",
        color:         !closed ? "#8AABB8" : "#2A2420",
        transition:    "color 0.3s",
      }}>
        Open
      </span>

      <div
        onClick={() => onChange(!closed)}
        style={{
          width:           "36px",
          height:          "58px",
          borderRadius:    "18px",
          backgroundColor: closed ? "#1C1410" : "#101418",
          border:          `1.5px solid ${closed ? "#A74A43" : "#516067"}`,
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
          top:             closed ? "calc(100% - 10px)" : "10px",
          transform:       "translate(-50%, -50%)",
          width:           "28px",
          height:          "20px",
          borderRadius:    "10px",
          backgroundColor: closed ? "#A74A43" : "#516067",
          border:          `1px solid ${closed ? "#C97870" : "#7A8FA0"}`,
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
        color:         closed ? "#A74A43" : "#2A2420",
        transition:    "color 0.3s",
      }}>
        Close
      </span>

    </div>
  );
}