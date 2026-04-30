"use client";

import { createContext, useContext, useState, Dispatch, SetStateAction, ReactNode } from "react";
import { Ctrl, defaultCtrl } from "@/lib/ctrl";

interface CtrlContextType {
  ctrl:    Ctrl;
  setCtrl: Dispatch<SetStateAction<Ctrl>>;
}

const CtrlContext = createContext<CtrlContextType>({ ctrl: defaultCtrl, setCtrl: () => {} });

export function CtrlProvider({ children }: { children: ReactNode }) {
  const [ctrl, setCtrl] = useState<Ctrl>(defaultCtrl);
  return <CtrlContext.Provider value={{ ctrl, setCtrl }}>{children}</CtrlContext.Provider>;
}

export function useCtrl() { return useContext(CtrlContext); }