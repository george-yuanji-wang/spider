"use client";

import { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from "react";
import { CliMessage, INITIAL_CLI_MESSAGES } from "@/lib/cli";

interface CliContextType {
  messages:   CliMessage[];
  addMessage: (text: string) => void;
}

const CliContext = createContext<CliContextType>({ messages: [], addMessage: () => {} });

export function CliProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages]   = useState<CliMessage[]>(INITIAL_CLI_MESSAGES);
  const seenCountRef              = useRef(0);

  const addMessage = useCallback((text: string) => {
    setMessages(prev => [...prev, {
      timestamp: new Date().toISOString(),
      text,
    }]);
  }, []);

  /* Poll bridge CLI — only append messages we haven't seen yet */
  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch("/api/cli");
        if (!res.ok) return;
        const data = await res.json();
        const incoming: CliMessage[] = data.messages ?? [];
        if (incoming.length > seenCountRef.current) {
          const newOnes = incoming.slice(seenCountRef.current);
          seenCountRef.current = incoming.length;
          setMessages(prev => [...prev, ...newOnes]);
        }
      } catch {}
    };

    const id = setInterval(poll, 500);
    return () => clearInterval(id);
  }, []);

  return <CliContext.Provider value={{ messages, addMessage }}>{children}</CliContext.Provider>;
}

export function useCli() { return useContext(CliContext); }