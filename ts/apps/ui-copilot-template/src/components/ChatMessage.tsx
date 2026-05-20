import { cn } from "../lib/utils";
import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";

interface ChatMessageProps {
  message: Message;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 animate-fade-in-up opacity-0", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary/[0.08] text-primary flex items-center justify-center border border-primary/15 mt-0.5">
          <Bot className="h-4 w-4" strokeWidth={1.5} />
        </div>
      )}
      <div className={cn("rounded-2xl", isUser ? "max-w-[85%] sm:max-w-[70%] bg-foreground text-background rounded-br-md px-4 py-3" : "max-w-[90%] sm:max-w-[80%] rounded-bl-md px-1")}>
        <div className={cn("text-[15px] leading-[1.7]", isUser ? "text-background/90" : "text-foreground/75")}>
          {isUser ? message.content : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
              p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
              strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
              code: ({ children }) => <code className="px-1.5 py-0.5 rounded-md bg-foreground/[0.05] text-[13px] font-mono text-foreground/75 border border-foreground/[0.04]">{children}</code>,
              ul: ({ children }) => <ul className="mb-3 last:mb-0 space-y-1.5 pl-1">{children}</ul>,
              li: ({ children }) => <li className="flex gap-2 text-[15px] leading-relaxed"><span className="text-primary/50 select-none mt-0.5 flex-shrink-0">•</span><span className="flex-1">{children}</span></li>,
            }}>{message.content}</ReactMarkdown>
          )}
        </div>
        <p className={cn("text-[10px] mt-2", isUser ? "text-background/30 text-right" : "text-foreground/20")}>{formatTime(message.timestamp)}</p>
      </div>
      {isUser && (
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-foreground/[0.08] text-foreground/50 flex items-center justify-center border border-foreground/[0.08] mt-0.5">
          <User className="h-4 w-4" strokeWidth={1.5} />
        </div>
      )}
    </div>
  );
}
