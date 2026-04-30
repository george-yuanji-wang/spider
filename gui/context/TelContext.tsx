"use client";

import { createContext, useContext, useState, Dispatch, SetStateAction, ReactNode } from "react";
import { Tel, defaultTel } from "@/lib/tel";

interface TelContextType {
  tel:    Tel;
  setTel: Dispatch<SetStateAction<Tel>>;
}

const TelContext = createContext<TelContextType>({ tel: defaultTel, setTel: () => {} });

export function TelProvider({ children }: { children: ReactNode }) {
  const [tel, setTel] = useState<Tel>(defaultTel);
  return <TelContext.Provider value={{ tel, setTel }}>{children}</TelContext.Provider>;
}

export function useTel() { return useContext(TelContext); }