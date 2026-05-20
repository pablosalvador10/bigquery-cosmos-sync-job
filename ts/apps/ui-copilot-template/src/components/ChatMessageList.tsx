import { useRef, useEffect } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatEmptyState } from "./ChatEmptyState";
import { TypingIndicator } from "./TypingIndicator";
import type { Message } from "../types";

interface ChatMessageListProps {
  messages: Message[];
  isLoading: boolean;
  onPromptClick: (prompt: string) => void;
}

export function ChatMessageList({ messages, isLoading, onPromptClick }: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isLoading]);

  const lastMsg = messages[messages.length - 1];
  const showTyping = isLoading && (!lastMsg || lastMsg.role === "user" || (lastMsg.role === "assistant" && lastMsg.content.trim().length === 0));

  if (messages.length === 0 && !isLoading) {
    return <ChatEmptyState onPromptClick={onPromptClick} />;
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-thin">
      <div className="max-w-3xl mx-auto space-y-5">
        {messages.filter((msg) => !(isLoading && msg.id === lastMsg?.id && msg.role === "assistant" && msg.content.trim().length === 0)).map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {showTyping && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
