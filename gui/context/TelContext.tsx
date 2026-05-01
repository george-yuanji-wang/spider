"use client";

import { createContext, useContext, useState, useEffect, Dispatch, SetStateAction, ReactNode } from "react";
import { Tel, defaultTel } from "@/lib/tel";

interface TelContextType {
  tel:    Tel;
  setTel: Dispatch<SetStateAction<Tel>>;
}

const TelContext = createContext<TelContextType>({ tel: defaultTel, setTel: () => {} });

export function TelProvider({ children }: { children: ReactNode }) {
  const [tel, setTel] = useState<Tel>(defaultTel);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/tel");
        if (!res.ok) return;
        const data = await res.json();
        if (data) setTel(data);
      } catch {}
    };

    poll();
    const id = setInterval(poll, 200);
    return () => clearInterval(id);
  }, []);

  return <TelContext.Provider value={{ tel, setTel }}>{children}</TelContext.Provider>;
}

export function useTel() { return useContext(TelContext); }