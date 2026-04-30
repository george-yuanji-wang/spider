interface Props {
  label:  string;
  active: boolean;
  fps?:   number;
}

export default function StatusIndicator({ label, active, fps }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
      <div style={{
        width:           "7px",
        height:          "7px",
        borderRadius:    "50%",
        flexShrink:      0,
        backgroundColor: active ? "#4A7060" : "#A74A43",
        boxShadow:       active ? "0 0 4px #4A706088" : "0 0 4px #A74A4388",
      }} />

      <span style={{
        fontFamily:    "StackSansNotch-Regular, sans-serif",
        fontSize:      "10px",
        letterSpacing: "0.1em",
        color:         "#9A9080",
        textTransform: "uppercase",
      }}>
        {label}
      </span>

      {fps !== undefined && (
        <span style={{ display: "flex", alignItems: "baseline", gap: "2px", marginLeft: "6px" }}>
          <span style={{
            fontFamily:    "StackSansNotch-Bold, sans-serif",
            fontSize:      "10px",
            letterSpacing: "0.05em",
            color:         "#C38D4F",
          }}>
            {fps}
          </span>
          <span style={{
            fontFamily:    "StackSansNotch-ExtraLight, sans-serif",
            fontSize:      "9px",
            color:         "#516067",
            letterSpacing: "0.05em",
          }}>
            fps
          </span>
        </span>
      )}
    </div>
  );
}