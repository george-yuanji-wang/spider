"use client";

import { createContext, useContext, useState, Dispatch, SetStateAction, ReactNode } from "react";
import { Params, defaultParams } from "@/lib/params";

interface ParamsContextType {
  params:    Params;
  setParams: Dispatch<SetStateAction<Params>>;
}

const ParamsContext = createContext<ParamsContextType>({ params: defaultParams, setParams: () => {} });

export function ParamsProvider({ children }: { children: ReactNode }) {
  const [params, setParams] = useState<Params>(defaultParams);
  return <ParamsContext.Provider value={{ params, setParams }}>{children}</ParamsContext.Provider>;
}

export function useParams() { return useContext(ParamsContext); }