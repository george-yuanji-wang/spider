"use client";

import { createContext, useContext, useState, useEffect, useRef, Dispatch, SetStateAction, ReactNode } from "react";
import { Ctrl, defaultCtrl } from "@/lib/ctrl";

interface CtrlContextType {
  ctrl:    Ctrl;
  setCtrl: Dispatch<SetStateAction<Ctrl>>;
}

const CtrlContext = createContext<CtrlContextType>({ ctrl: defaultCtrl, setCtrl: () => {} });

export function CtrlProvider({ children }: { children: ReactNode }) {
  const [ctrl, setCtrl]   = useState<Ctrl>(defaultCtrl);
  const mountedRef        = useRef(false);

  /* Fire POST on every ctrl change after initial mount */
  useEffect(() => {
    if (!mountedRef.current) { mountedRef.current = true; return; }
    fetch("/api/ctrl", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(ctrl),
    }).catch(() => {});
  }, [ctrl]);

  return <CtrlContext.Provider value={{ ctrl, setCtrl }}>{children}</CtrlContext.Provider>;
}

export function useCtrl() { return useContext(CtrlContext); }