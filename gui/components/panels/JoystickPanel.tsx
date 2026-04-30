"use client";

import { useEffect, useState, useRef } from "react";
import DPad, { Direction } from "@/components/ui/DPad";
import AnalogStick          from "@/components/ui/AnalogStick";
import SpeedBar             from "@/components/ui/SpeedBar";
import Toggle               from "@/components/ui/Toggle";
import { useCtrl }          from "@/context/CtrlContext";
import { useCli }           from "@/context/CliContext";

const KEY_MAP: Record<string, { up?: boolean; down?: boolean; left?: boolean; right?: boolean }> = {
  w: { up: true },    arrowup:    { up: true },
  s: { down: true },  arrowdown:  { down: true },
  a: { left: true },  arrowleft:  { left: true },
  d: { right: true }, arrowright: { right: true },
};

function getDirection(keys: Set<string>): Direction | null {
  let up = false, down = false, left = false, right = false;
  keys.forEach(k => {
    const m = KEY_MAP[k];
    if (m?.up)    up    = true;
    if (m?.down)  down  = true;
    if (m?.left)  left  = true;
    if (m?.right) right = true;
  });
  if (up   && left)  return "up-left";
  if (up   && right) return "up-right";
  if (down && left)  return "down-left";
  if (down && right) return "down-right";
  if (up)    return "up";
  if (down)  return "down";
  if (left)  return "left";
  if (right) return "right";
  return null;
}

const DPAD_TANK: Record<string, { l: number; r: number }> = {
  "up":         { l:  100, r:  100 },
  "down":       { l: -100, r: -100 },
  "left":       { l:  -80, r:   80 },
  "right":      { l:   80, r:  -80 },
  "up-left":    { l:   50, r:  100 },
  "up-right":   { l:  100, r:   50 },
  "down-left":  { l: -100, r:  -50 },
  "down-right": { l:  -50, r: -100 },
};

function dpadToTank(dir: Direction | null) {
  if (!dir) return { left: 0, right: 0 };
  const b = DPAD_TANK[dir];
  return { left: b.l, right: b.r };
}

function analogToTank(x: number, y: number) {
  const fwd   = -y;
  const clamp = (v: number) => Math.max(-1, Math.min(1, v));
  return {
    left:  Math.round(clamp(fwd + x) * 100),
    right: Math.round(clamp(fwd - x) * 100),
  };
}

function valueColor(val: number, isSpeed = false): string {
  if (isSpeed) return "#C38D4F";
  if (val === 0) return "#516067";
  return val > 0 ? "#8AABB8" : "#A74A43";
}

interface NumInputProps {
  label: string; value: string; min: number; max: number; onChange: (v: string) => void;
}

function NumInput({ label, value, min, max, onChange }: NumInputProps) {
  const handle = (raw: string) => {
    const filtered = raw.replace(/[^0-9\-]/g, "").replace(/(?!^)-/g, "");
    if (filtered === "" || filtered === "-") { onChange(filtered); return; }
    const n = parseInt(filtered, 10);
    if (isNaN(n)) return;
    onChange(String(Math.max(min, Math.min(max, n))));
  };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px", width: "100%" }}>
      <span style={{ fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "9px", letterSpacing: "0.12em", color: "#9A9080" }}>
        {label}
      </span>
      <input
        type="text" inputMode="numeric" value={value}
        onChange={e => handle(e.target.value)}
        style={{ width: "100%", backgroundColor: "#151210", border: "1.5px solid #3E3830", borderRadius: "4px", color: "#D8CFC0", fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "11px", padding: "4px 6px", outline: "none", textAlign: "center" }}
      />
    </div>
  );
}

export default function JoystickPanel() {
  const { ctrl, setCtrl }     = useCtrl();
  const { addMessage }        = useCli();

  const [mode,            setMode]            = useState<"dpad" | "analog">("dpad");
  const [activeDir,       setActiveDir]       = useState<Direction | null>(null);
  const [joystickEnabled, setJoystickEnabled] = useState(true);
  const [analogPos,       setAnalogPos]       = useState({ x: 0, y: 0 });
  const [manualL,         setManualL]         = useState("0");
  const [manualR,         setManualR]         = useState("0");
  const [manualSpd,       setManualSpd]       = useState("50");

  const pressedKeys   = useRef<Set<string>>(new Set());
  const holdInterval  = useRef<ReturnType<typeof setInterval> | null>(null);
  const holdTimeout   = useRef<ReturnType<typeof setTimeout>  | null>(null);
  const holdStartTime = useRef<number>(0);
  const speedKeyRef   = useRef<"q" | "e" | null>(null);
  const joystickRef   = useRef(false);

  const joystickActive    = ctrl.armed && joystickEnabled;
  joystickRef.current     = joystickActive;

  /* Direction → ctrl */
  useEffect(() => {
    if (!joystickActive) return;
    const computed = mode === "dpad"
      ? dpadToTank(activeDir)
      : analogToTank(analogPos.x, analogPos.y);
    setCtrl(c => ({ ...c, input_left: computed.left, input_right: computed.right }));
  }, [joystickActive, mode, activeDir, analogPos]);

  /* Speed bar */
  const handleSpeedChange = (v: number) => {
    if (!joystickActive) return;
    setCtrl(c => ({ ...c, speed: v }));
  };

  /* Q/E */
  const clearSpeedHold = () => {
    if (holdTimeout.current)  { clearTimeout(holdTimeout.current);   holdTimeout.current  = null; }
    if (holdInterval.current) { clearInterval(holdInterval.current); holdInterval.current = null; }
    speedKeyRef.current = null;
  };

  const startSpeedHold = (key: "q" | "e") => {
    if (!joystickRef.current) return;
    if (speedKeyRef.current === key) return;
    clearSpeedHold();
    speedKeyRef.current   = key;
    holdStartTime.current = Date.now();
    const apply = () => {
      const ms   = Date.now() - holdStartTime.current;
      const step = ms < 1000 ? 1 : ms < 2500 ? 2 : 3;
      setCtrl(c => ({ ...c, speed: key === "e" ? Math.min(100, c.speed + step) : Math.max(0, c.speed - step) }));
    };
    apply();
    holdTimeout.current = setTimeout(() => { holdInterval.current = setInterval(apply, 140); }, 600);
  };

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (Object.keys(KEY_MAP).includes(key)) {
        if (!joystickRef.current) return;
        e.preventDefault();
        pressedKeys.current.add(key);
        if (mode === "dpad") setActiveDir(getDirection(pressedKeys.current));
      }
      if (key === "e") startSpeedHold("e");
      if (key === "q") startSpeedHold("q");
    };
    const onKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      pressedKeys.current.delete(key);
      if (mode === "dpad") setActiveDir(getDirection(pressedKeys.current));
      if (key === "q" || key === "e") clearSpeedHold();
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup",   onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup",   onKeyUp);
      clearSpeedHold();
    };
  }, [mode]);

  /* Arm toggle */
  const handleArmToggle = () => {
    const newArmed = !ctrl.armed;
    if (newArmed) {
      setCtrl(c => ({ ...c, armed: true }));
      addMessage("ARM - ready to drive");
    } else {
      setCtrl(c => ({ ...c, armed: false, input_left: 0, input_right: 0, speed: 50 }));
      addMessage("DISARM — inputs reset");
    }
  };

  /* Joystick toggle */
  const handleJoystickToggle = () => {
    const newEnabled = !joystickEnabled;
    setJoystickEnabled(newEnabled);
    if (newEnabled) {
      addMessage("Joystick enabled");
    } else {
      setCtrl(c => ({ ...c, input_left: 0, input_right: 0, speed: 50 }));
      addMessage("Joystick disabled — inputs reset");
    }
  };

  /* Manual send */
  const handleSend = () => {
    const l = parseInt(manualL,   10) || 0;
    const r = parseInt(manualR,   10) || 0;
    const s = parseInt(manualSpd, 10) || 0;
    setCtrl(prev => ({ ...prev, input_left: l, input_right: r, speed: s }));
    addMessage(`Manual drive — L:${l}  R:${r}  S:${s}`);
  };

  /* Manual reset */
  const handleReset = () => {
    setManualL("0");
    setManualR("0");
    setManualSpd("50");
    setCtrl(prev => ({ ...prev, input_left: 0, input_right: 0, speed: 50 }));
    addMessage("Manual drive reset");
  };

  const LABEL: React.CSSProperties = {
    fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "10px", letterSpacing: "0.1em", color: "#9A9080",
  };

  return (
    <div className="flex flex-col h-full" style={{ padding: "4px 12px", boxSizing: "border-box", width: "440px", flexShrink: 0 }}>

      <span style={{ fontFamily: "StackSansNotch-SemiBold, sans-serif", fontSize: "13px", letterSpacing: "0.12em", color: "#D8CFC0", textTransform: "uppercase", marginBottom: "4px" }}>
        Joystick
      </span>

      <div className="flex flex-row flex-1 overflow-hidden" style={{ gap: "16px" }}>

        {/* Pad */}
        <div style={{ opacity: joystickActive ? 1 : 0.3, pointerEvents: joystickActive ? "auto" : "none", transition: "opacity 0.25s", display: "flex", alignItems: "center", flexShrink: 0, width: "210px" }}>
          {mode === "dpad" ? (
            <DPad activeDir={activeDir} onPress={dir => setActiveDir(dir)} onRelease={() => setActiveDir(getDirection(pressedKeys.current))} />
          ) : (
            <AnalogStick size={210} onChange={(x, y) => setAnalogPos({ x, y })} />
          )}
        </div>

        {/* Speed bar */}
        <div style={{ opacity: joystickActive ? 1 : 0.3, pointerEvents: joystickActive ? "auto" : "none", transition: "opacity 0.25s", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, width: "32px" }}>
          <SpeedBar value={ctrl.speed} onChange={handleSpeedChange} height={210} />
        </div>

        {/* Readout + Manual */}
        <div className="flex flex-col justify-center" style={{ width: "130px", flexShrink: 0, gap: "10px" }}>

          <div className="flex flex-col" style={{ gap: "6px" }}>
            {([
              { label: "LEFT",  value: ctrl.input_left,  spd: false },
              { label: "RIGHT", value: ctrl.input_right, spd: false },
              { label: "SPEED", value: ctrl.speed,       spd: true  },
            ] as const).map(({ label, value, spd }) => (
              <div key={label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={LABEL}>{label}</span>
                <span style={{ fontFamily: "StackSansNotch-Bold, sans-serif", fontSize: "12px", color: valueColor(value, spd), transition: "color 0.3s", minWidth: "36px", textAlign: "right" }}>
                  {value}
                </span>
              </div>
            ))}
          </div>

          <div style={{ height: "1px", backgroundColor: "#2A2420" }} />

          <div style={{ opacity: ctrl.armed ? 1 : 0.3, pointerEvents: ctrl.armed ? "auto" : "none", transition: "opacity 0.25s" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div style={{ display: "flex", gap: "4px" }}>
                <NumInput label="Left"  value={manualL}   min={-100} max={100} onChange={setManualL}   />
                <NumInput label="Right" value={manualR}   min={-100} max={100} onChange={setManualR}   />
                <NumInput label="Speed" value={manualSpd} min={0}    max={100} onChange={setManualSpd} />
              </div>
              <div style={{ display: "flex", gap: "4px" }}>
                <button onClick={handleSend} style={{ flex: 1, padding: "4px 0", backgroundColor: "#1E1B17", border: "1.5px solid #516067", borderRadius: "4px", color: "#D8CFC0", fontFamily: "StackSansNotch-Medium, sans-serif", fontSize: "10px", letterSpacing: "0.1em", cursor: "pointer" }}>
                  SEND
                </button>
                <button onClick={handleReset} style={{ padding: "4px 8px", backgroundColor: "transparent", border: "1.5px solid #516067", borderRadius: "4px", color: "#516067", fontFamily: "StackSansNotch-Bold, sans-serif", fontSize: "12px", cursor: "pointer" }}>
                  ↺
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "6px", flexShrink: 0 }}>
        <div style={{ display: "flex", backgroundColor: "#1E1B17", borderRadius: "9999px", border: "1.5px solid #516067", padding: "2px", gap: "2px" }}>
          {(["dpad", "analog"] as const).map(m => (
            <button key={m} onClick={() => setMode(m)} style={{ padding: "2px 10px", borderRadius: "9999px", fontSize: "9px", letterSpacing: "0.12em", fontFamily: "StackSansNotch-Medium, sans-serif", cursor: "pointer", border: "none", transition: "background-color 0.15s, color 0.15s", backgroundColor: mode === m ? "#516067" : "transparent", color: mode === m ? "#D8CFC0" : "#9A9080" }}>
              {m === "dpad" ? "D-PAD" : "ANALOG"}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <Toggle label="ARM"      enabled={ctrl.armed}      onToggle={handleArmToggle}      />
          <Toggle label="JOYSTICK" enabled={joystickEnabled} onToggle={handleJoystickToggle} />
        </div>
      </div>

    </div>
  );
}