"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { CliMessage, INITIAL_CLI_MESSAGES } from "@/lib/cli";

interface CliContextType {
  messages:   CliMessage[];
  addMessage: (text: string) => void;
}

const CliContext = createContext<CliContextType>({ messages: [], addMessage: () => {} });

export function CliProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<CliMessage[]>(INITIAL_CLI_MESSAGES);

  const addMessage = useCallback((text: string) => {
    setMessages(prev => [...prev, { timestamp: new Date().toISOString(), text }]);
  }, []);

  return <CliContext.Provider value={{ messages, addMessage }}>{children}</CliContext.Provider>;
}

export function useCli() { return useContext(CliContext); }