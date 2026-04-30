"use client";

import { useTel }        from "@/context/TelContext";
import VideoPanel        from "@/components/panels/VideoPanel";
import JoystickPanel     from "@/components/panels/JoystickPanel";
import TelemetryPanel    from "@/components/panels/TelemetryPanel";
import ControlPanel      from "@/components/panels/ControlPanel";

function VerticalDivider() {
  return (
    <div className="flex items-center justify-center flex-shrink-0" style={{ width: "48px" }}>
      <div style={{ width: "2px", height: "55%", backgroundColor: "#516067" }} />
    </div>
  );
}

function HorizontalDivider({ width }: { width?: number }) {
  return (
    <div className="flex items-center justify-center flex-shrink-0" style={{ height: "36px" }}>
      <div style={{ height: "2px", width: width ? `${width}px` : "65%", backgroundColor: "#516067" }} />
    </div>
  );
}

export default function Home() {
  const { tel } = useTel();

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-background">

      <header className="flex items-center gap-3 px-10 py-4 flex-shrink-0">
        <h1 className="font-stack-bold text-text-primary text-4xl tracking-wide">
          Spider Studio V1
        </h1>
        <div
          className="flex items-center gap-1.5 px-3 py-0.5 border-2 rounded-full font-stack-medium text-xs tracking-widest"
          style={
            tel.connected
              ? { backgroundColor: "#1A2E27", borderColor: "#4A7060", color: "#7AAF99" }
              : { backgroundColor: "#2A1614", borderColor: "#A74A43", color: "#C97870" }
          }
        >
          <div
            className="w-1.5 h-1.5 rounded-full"
            style={{ backgroundColor: tel.connected ? "#7AAF99" : "#C97870" }}
          />
          {tel.connected ? "ONLINE" : "OFFLINE"}
        </div>
      </header>

      <div className="flex-1 flex items-stretch justify-center overflow-hidden" style={{ paddingBottom: "40px" }}>
        <div className="flex flex-shrink-0" style={{ width: "1188px" }}>

          {/* Left Column */}
          <div className="flex flex-col overflow-hidden flex-shrink-0" style={{ width: "700px" }}>
            <div className="flex-none" style={{ paddingTop: "16px" }}>
              <VideoPanel />
            </div>
            <HorizontalDivider width={640} />
            <div className="flex-1 overflow-hidden">
              <ControlPanel />
            </div>
          </div>

          <VerticalDivider />

          {/* Right Column */}
          <div className="flex flex-col flex-shrink-0 overflow-hidden" style={{ width: "440px" }}>
            <div style={{ flex: "0 0 45%" }}>
              <JoystickPanel />
            </div>
            <HorizontalDivider />
            <div className="flex-1 overflow-hidden">
              <TelemetryPanel />
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}