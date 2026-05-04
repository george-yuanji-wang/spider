"use client";

import { useEffect, useRef, useState } from "react";
import { useCli } from "@/context/CliContext";

function formatTime(iso: string): string {
  const d    = new Date(iso);
  let hours  = d.getHours();
  const mins = String(d.getMinutes()).padStart(2, "0");
  const secs = String(d.getSeconds()).padStart(2, "0");
  const ampm = hours >= 12 ? "p.m." : "a.m.";
  hours      = hours % 12 || 12;
  return `${String(hours).padStart(2, "0")}:${mins}:${secs} ${ampm}`;
}

function Checkbox({ checked, onToggle, label }: { checked: boolean; onToggle: () => void; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "5px", cursor: "pointer" }} onClick={onToggle}>
      <div style={{ width: "12px", height: "12px", borderRadius: "2px", border: `1.5px solid ${checked ? "#516067" : "#3E3830"}`, backgroundColor: checked ? "#516067" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, transition: "background-color 0.15s, border-color 0.15s" }}>
        {checked && (
          <svg width="8" height="8" viewBox="0 0 8 8">
            <polyline points="1,4 3,6 7,2" stroke="#D8CFC0" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </div>
      <span style={{ fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "9px", letterSpacing: "0.1em", color: "#9A9080", userSelect: "none" }}>
        {label}
      </span>
    </div>
  );
}

export default function CliOutput() {
  const { messages }                         = useCli();
  const [showTime,       setShowTime]        = useState(true);
  const [scrollToBottom, setScrollToBottom]  = useState(true);
  const [clearedIndex,   setClearedIndex]    = useState(0);
  const [mounted,        setMounted]         = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setMounted(true); }, []);

  const visible = messages.slice(clearedIndex);

  useEffect(() => {
    if (scrollToBottom && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [visible.length, scrollToBottom]);

  if (!mounted) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: "8px" }}>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <span style={{ fontFamily: "StackSansNotch-SemiBold, sans-serif", fontSize: "11px", letterSpacing: "0.12em", color: "#9A9080", textTransform: "uppercase" }}>
          CLI Output
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Checkbox checked={showTime}       onToggle={() => setShowTime(v => !v)}       label="SHOW TIME" />
          <Checkbox checked={scrollToBottom} onToggle={() => setScrollToBottom(v => !v)} label="SCROLL"    />
          <button
            onClick={() => setClearedIndex(messages.length)}
            style={{ padding: "2px 8px", backgroundColor: "transparent", border: "1.5px solid #3E3830", borderRadius: "3px", color: "#516067", fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "9px", letterSpacing: "0.1em", cursor: "pointer" }}
          >
            CLEAR
          </button>
        </div>
      </div>

      <div style={{ flex: 1, backgroundColor: "#171C1F", border: "1.5px solid #516067", borderRadius: "4px", overflowY: "auto", padding: "10px", display: "flex", flexDirection: "column", gap: "5px", minHeight: 0 }}>
        {visible.length === 0 ? (
          <span style={{ fontFamily: "StackSansNotch-Light, sans-serif", fontSize: "10px", color: "#3E3830", letterSpacing: "0.08em", margin: "auto" }}>
            No message at this time
          </span>
        ) : (
          visible.map((msg, i) => (
            <div key={i} style={{ display: "flex", gap: "7px", alignItems: "baseline" }}>
              {showTime && (
                <span style={{ fontFamily: "StackSansNotch-ExtraLight, sans-serif", fontSize: "9px", color: "#516067", letterSpacing: "0.05em", flexShrink: 0, whiteSpace: "nowrap" }}>
                  [{formatTime(msg.timestamp)}]
                </span>
              )}
              <span style={{ fontFamily: "StackSansNotch-Light, sans-serif", fontSize: "10px", color: "#516067", letterSpacing: "0.03em", flexShrink: 0 }}>
                &gt;&gt;&gt;
              </span>
              <span style={{ fontFamily: "StackSansNotch-Regular, sans-serif", fontSize: "10px", color: "#D8CFC0", letterSpacing: "0.05em", wordBreak: "break-word" }}>
                {msg.text}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

    </div>
  );
}