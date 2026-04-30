import type { Metadata } from "next";
import "./globals.css";
import { CtrlProvider }   from "@/context/CtrlContext";
import { TelProvider }    from "@/context/TelContext";
import { CliProvider }    from "@/context/CliContext";
import { ParamsProvider } from "@/context/ParamsContext";

export const metadata: Metadata = {
  title: "Spider Studio V2",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CtrlProvider>
          <TelProvider>
            <CliProvider>
              <ParamsProvider>
                {children}
              </ParamsProvider>
            </CliProvider>
          </TelProvider>
        </CtrlProvider>
      </body>
    </html>
  );
}