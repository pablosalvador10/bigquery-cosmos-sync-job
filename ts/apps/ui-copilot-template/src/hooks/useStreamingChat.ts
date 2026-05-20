import { useCallback, useMemo, useState } from "react";

import { streamChat } from "../lib/api";
import type { Message, ToolEvent } from "../types";

function id() {
  return crypto.randomUUID();
}

export function useStreamingChat() {
  const [sessionId] = useState(() => id());
  const [messages, setMessages] = useState<Message[]>([]);
  const [toolEvent, setToolEvent] = useState<ToolEvent | null>(null);
  const [loading, setLoading] = useState(false);

  const sendMessage = useCallback(async (content: string) => {
    const now = Date.now();
    setMessages((prev) => [...prev, { id: id(), role: "user", content, timestamp: now }]);
    const assistantId = id();
    setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: "", timestamp: now }]);
    setLoading(true);

    try {
      await streamChat(
        content,
        sessionId,
        (token) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId ? { ...msg, content: `${msg.content}${token}` } : msg
            )
          );
        },
        (event) => setToolEvent(event)
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return useMemo(
    () => ({ sessionId, messages, toolEvent, loading, sendMessage }),
    [sessionId, messages, toolEvent, loading, sendMessage]
  );
}
