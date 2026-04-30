"use client";

import { useState }      from "react";
import { useCtrl }       from "@/context/CtrlContext";
import { useParams }     from "@/context/ParamsContext";
import { useCli }        from "@/context/CliContext";
import { defaultParams } from "@/lib/params";
import { DriveMode }     from "@/lib/ctrl";
import ModeLever         from "@/components/ui/ModeLever";

const INPUT_STYLE: React.CSSProperties = {
  width:           "44px",
  backgroundColor: "#151210",
  border:          "1.5px solid #2A2420",
  borderRadius:    "3px",
  color:           "#D8CFC0",
  fontFamily:      "StackSansNotch-Regular, sans-serif",
  fontSize:        "10px",
  padding:         "2px 4px",
  outline:         "none",
  textAlign:       "center",
  flexShrink:      0,
};

function clampInput(raw: string, min: number, max: number): string | null {
  const f = raw.replace(/[^0-9]/g, "");
  if (f === "") return "";
  const n = parseInt(f, 10);
  if (isNaN(n)) return null;
  return String(Math.max(min, Math.min(max, n)));
}

function RangeInput({ label, low, high, min, max, onLow, onHigh }: {
  label: string; low: string; high: string;
  min: number; max: number;
  onLow: (v: string) => void; onHigh: (v: string) => void;
}) {
  const handle = (raw: string, setter: (v: string) => void) => {
    const result = clampInput(raw, min, max);
    if (result !== null) setter(result);
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
      <span style={{ fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "9px", color: "#9A9080", width: "10px", flexShrink: 0 }}>
        {label}
      </span>
      <input type="text" inputMode="numeric" value={low}  onChange={e => handle(e.target.value, onLow)}  style={INPUT_STYLE} />
      <span style={{ fontFamily: "StackSansNotch-ExtraLight, sans-serif", fontSize: "9px", color: "#3E3830", flexShrink: 0 }}>—</span>
      <input type="text" inputMode="numeric" value={high} onChange={e => handle(e.target.value, onHigh)} style={INPUT_STYLE} />
    </div>
  );
}

function SingleInput({ label, value, min, max, onChange }: {
  label: string; value: string; min: number; max: number; onChange: (v: string) => void;
}) {
  const handle = (raw: string) => {
    const result = clampInput(raw, min, max);
    if (result !== null) onChange(result);
  };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
      <span style={{ fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "9px", color: "#9A9080", flexShrink: 0 }}>
        {label}
      </span>
      <input type="text" inputMode="numeric" value={value} onChange={e => handle(e.target.value)} style={INPUT_STYLE} />
    </div>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <span style={{ fontFamily: "StackSansNotch-Medium, sans-serif", fontSize: "8px", letterSpacing: "0.18em", color: "#516067", textTransform: "uppercase" }}>
      {children}
    </span>
  );
}

function Placeholder() {
  return (
    <span style={{ fontFamily: "StackSansNotch-ExtraLight, sans-serif", fontSize: "9px", color: "#3E3830" }}>
      Not configured
    </span>
  );
}

function ColDivider() {
  return <div style={{ width: "1px", backgroundColor: "#2A2420", flexShrink: 0, alignSelf: "stretch" }} />;
}

export default function ControlPanel() {
  const { ctrl, setCtrl }     = useCtrl();
  const { params, setParams } = useParams();
  const { addMessage }        = useCli();

  const b = params.ball;
  const [draft, setDraft] = useState({
    hue_low:     String(b.hue_low),
    hue_high:    String(b.hue_high),
    sat_low:     String(b.sat_low),
    sat_high:    String(b.sat_high),
    val_low:     String(b.val_low),
    val_high:    String(b.val_high),
    min_radius:  String(b.min_radius),
    blur_kernel: String(b.blur_kernel),
    dilate_iter: String(b.dilate_iter),
  });

  const f = (key: keyof typeof draft) => (v: string) => setDraft(d => ({ ...d, [key]: v }));

  const handleSend = () => {
    const n = (k: keyof typeof draft) => parseInt(draft[k], 10) || 0;
    const u = {
      hue_low:     n("hue_low"),    hue_high:    n("hue_high"),
      sat_low:     n("sat_low"),    sat_high:    n("sat_high"),
      val_low:     n("val_low"),    val_high:    n("val_high"),
      min_radius:  n("min_radius"),
      blur_kernel: n("blur_kernel"),
      dilate_iter: n("dilate_iter"),
    };
    setParams(p => ({ ...p, ball: u }));
    addMessage(`Ball params — H:${u.hue_low}-${u.hue_high} S:${u.sat_low}-${u.sat_high} V:${u.val_low}-${u.val_high} r:${u.min_radius} k:${u.blur_kernel} d:${u.dilate_iter}`);
  };

  const handleReset = () => {
    const d = defaultParams.ball;
    setDraft({
      hue_low:     String(d.hue_low),    hue_high:    String(d.hue_high),
      sat_low:     String(d.sat_low),    sat_high:    String(d.sat_high),
      val_low:     String(d.val_low),    val_high:    String(d.val_high),
      min_radius:  String(d.min_radius),
      blur_kernel: String(d.blur_kernel),
      dilate_iter: String(d.dilate_iter),
    });
    setParams(p => ({ ...p, ball: { ...d } }));
    addMessage("Ball params reset to defaults");
  };

  const handleModeChange = (m: DriveMode) => {
    setCtrl(c => ({ ...c, mode: m }));
    addMessage(`Drive mode → ${m}`);
  };

  return (
    <div style={{
      display:        "flex",
      alignItems:     "center",
      justifyContent: "center",
      height:         "100%",
      padding:        "8px 12px",
      boxSizing:      "border-box",
    }}>
      <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "0" }}>

        {/* Mode */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", flexShrink: 0, width: "100px", padding: "0 12px" }}>
          <span style={{ fontFamily: "StackSansNotch-SemiBold, sans-serif", fontSize: "13px", letterSpacing: "0.12em", color: "#D8CFC0", textTransform: "uppercase" }}>
            Mode
          </span>
          <ModeLever mode={ctrl.mode} onChange={handleModeChange} />
        </div>

        <ColDivider />
        <div style={{ width: "14px", flexShrink: 0 }} />

        {/* Parameters */}
        <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
          <span style={{ fontFamily: "StackSansNotch-SemiBold, sans-serif", fontSize: "13px", letterSpacing: "0.12em", color: "#D8CFC0", textTransform: "uppercase", flexShrink: 0 }}>
            Parameters
          </span>

          <div style={{ paddingLeft: "6px", display: "flex", flexDirection: "row", gap: "14px", alignItems: "flex-start" }}>

            {/* Col 1: Ball HSV */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0 }}>
              <SectionLabel>Ball HSV</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <RangeInput label="H" low={draft.hue_low} high={draft.hue_high} min={0} max={179} onLow={f("hue_low")} onHigh={f("hue_high")} />
                <RangeInput label="S" low={draft.sat_low} high={draft.sat_high} min={0} max={255} onLow={f("sat_low")} onHigh={f("sat_high")} />
                <RangeInput label="V" low={draft.val_low} high={draft.val_high} min={0} max={255} onLow={f("val_low")} onHigh={f("val_high")} />
              </div>
            </div>

            <ColDivider />

            {/* Col 2: Detection */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0 }}>
              <SectionLabel>Detection</SectionLabel>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <SingleInput label="Min r"  value={draft.min_radius}  min={1} max={200} onChange={f("min_radius")}  />
                <SingleInput label="Kernel" value={draft.blur_kernel} min={1} max={31}  onChange={f("blur_kernel")} />
                <SingleInput label="Dilate" value={draft.dilate_iter} min={0} max={10}  onChange={f("dilate_iter")} />
              </div>
            </div>

            <ColDivider />

            {/* Col 3: Path */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0, width: "80px" }}>
              <SectionLabel>Path</SectionLabel>
              <Placeholder />
            </div>

            <ColDivider />

            {/* Col 4: System */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0, width: "80px" }}>
              <SectionLabel>System</SectionLabel>
              <Placeholder />
            </div>

            <ColDivider />

            {/* Col 5: Apply */}
            <div style={{ display: "flex", flexDirection: "column", gap: "5px", flexShrink: 0, alignItems: "flex-start" }}>
              <SectionLabel>Apply</SectionLabel>
              <button
                onClick={handleSend}
                style={{ width: "56px", padding: "4px 0", backgroundColor: "#1E1B17", border: "1.5px solid #516067", borderRadius: "4px", color: "#D8CFC0", fontFamily: "StackSansNotch-Medium, sans-serif", fontSize: "10px", letterSpacing: "0.1em", cursor: "pointer" }}
              >
                SEND
              </button>
              <button
                onClick={handleReset}
                style={{ width: "56px", padding: "4px 0", backgroundColor: "transparent", border: "1.5px solid #516067", borderRadius: "4px", color: "#516067", fontFamily: "StackSansNotch-Bold, sans-serif", fontSize: "12px", cursor: "pointer" }}
              >
                ↺
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}