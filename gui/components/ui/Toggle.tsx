"use client";

interface ToggleProps {
  enabled:  boolean;
  onToggle: () => void;
  label:    string;
}

export default function Toggle({ enabled, onToggle, label }: ToggleProps) {
  return (
    <div className="flex items-center gap-2 cursor-pointer select-none" onClick={onToggle}>
      {/* Track */}
      <div
        style={{
          position:        "relative",
          width:           "32px",
          height:          "16px",
          borderRadius:    "9999px",
          border:          enabled ? "1.5px solid #4A7060" : "1.5px solid #A74A43",
          backgroundColor: enabled ? "#1A2E27" : "#2A1614",
          transition:      "background-color 0.2s, border-color 0.2s",
          flexShrink:      0,
        }}
      >
        {/* Thumb */}
        <div
          style={{
            position:        "absolute",
            top:             "2px",
            left:            "2px",
            width:           "10px",
            height:          "10px",
            borderRadius:    "9999px",
            backgroundColor: enabled ? "#7AAF99" : "#C97870",
            transition:      "transform 0.2s, background-color 0.2s",
            transform:       enabled ? "translateX(16px)" : "translateX(0px)",
          }}
        />
      </div>

      {/* Label */}
      <span
        className="font-stack-regular tracking-wide"
        style={{ fontSize: "10px", color: "#9A9080" }}
      >
        {label}
      </span>
    </div>
  );
}