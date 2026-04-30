"use client";

type Direction =
  | "up-left" | "up" | "up-right"
  | "left"    |        "right"
  | "down-left" | "down" | "down-right";

export type { Direction };

const ARROWS: Record<Direction, string> = {
  "up-left":   "↖", "up":   "↑", "up-right":   "↗",
  "left":      "←",               "right":       "→",
  "down-left": "↙", "down": "↓", "down-right":  "↘",
};

const LAYOUT: (Direction | null)[] = [
  "up-left",   "up",   "up-right",
  "left",       null,   "right",
  "down-left", "down", "down-right",
];

interface Props {
  activeDir: Direction | null;
  onPress:   (dir: Direction) => void;
  onRelease: () => void;
}

export default function DPad({ activeDir, onPress, onRelease }: Props) {
  return (
    <div
      style={{
        display:             "grid",
        gridTemplateColumns: "repeat(3, 64px)",
        gridTemplateRows:    "repeat(3, 64px)",
        gap:                 "6px",
        flexShrink:          0,
      }}
    >
      {LAYOUT.map((dir, i) => {
        if (dir === null) {
          return (
            <div
              key={i}
              style={{
                width:           64,
                height:          64,
                borderRadius:    "12px",
                backgroundColor: "#0E0C0A",
                border:          "1.5px solid #2A2420",
              }}
            />
          );
        }

        const isActive = activeDir === dir;

        return (
          <button
            key={i}
            onMouseDown={() => onPress(dir)}
            onMouseUp={onRelease}
            onMouseLeave={() => { if (isActive) onRelease(); }}
            style={{
              width:           64,
              height:          64,
              borderRadius:    "12px",
              backgroundColor: isActive ? "#1A2530" : "#2A2420",
              border:          `1.5px solid ${isActive ? "#5C7A8A" : "#3E3830"}`,
              color:           isActive ? "#8AABB8"  : "#516067",
              fontSize:        "18px",
              display:         "flex",
              alignItems:      "center",
              justifyContent:  "center",
              cursor:          "pointer",
              transition:      "background-color 0.08s, border-color 0.08s, color 0.08s",
              userSelect:      "none",
              outline:         "none",
            }}
          >
            {ARROWS[dir]}
          </button>
        );
      })}
    </div>
  );
}