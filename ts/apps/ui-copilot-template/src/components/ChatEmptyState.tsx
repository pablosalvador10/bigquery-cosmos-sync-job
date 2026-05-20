import { cn } from "../lib/utils";
import { MessageSquare, Sparkles, Wrench, Send } from "lucide-react";

interface ChatEmptyStateProps {
  onPromptClick: (prompt: string) => void;
}

const SUGGESTIONS = [
  { icon: MessageSquare, text: "What can you help me with?" },
  { icon: Sparkles,      text: "Summarize a concept in one paragraph" },
  { icon: Wrench,        text: "Generate a sample API response" },
  { icon: Send,          text: "Explain SSE streaming step by step" },
] as const;

export function ChatEmptyState({ onPromptClick }: ChatEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 pb-8">
      <div className={cn("h-16 w-16 rounded-2xl bg-primary/[0.06] border border-primary/15 flex items-center justify-center mb-6 animate-fade-in opacity-0")}>
        <Sparkles className="h-8 w-8 text-primary/60" strokeWidth={1.5} />
      </div>
      <h1 className="font-serif text-2xl sm:text-3xl md:text-[34px] font-medium text-foreground leading-tight text-center mb-2 animate-fade-in-up opacity-0 [animation-delay:100ms]">
        Agentic Template
      </h1>
      <p className="text-sm text-foreground/35 text-center max-w-md mb-10 animate-fade-in-up opacity-0 [animation-delay:200ms]">
        A reusable chat interface for Azure-based agentic applications with real-time streaming.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg animate-fade-in-up opacity-0 [animation-delay:350ms]">
        {SUGGESTIONS.map((s) => {
          const Icon = s.icon;
          return (
            <button key={s.text} onClick={() => onPromptClick(s.text)} className={cn("group flex items-start gap-3 px-4 py-4 rounded-xl bg-card border border-foreground/[0.06] hover:border-primary/20 hover:bg-primary/[0.02] hover:shadow-[0_2px_12px_rgba(0,0,0,0.04)] active:scale-[0.98] transition-all duration-200 text-left")}>
              <Icon className="h-[18px] w-[18px] mt-0.5 flex-shrink-0 text-foreground/30 group-hover:text-primary/60 transition-colors" strokeWidth={1.5} />
              <span className="text-[15px] leading-snug text-foreground/55 group-hover:text-foreground/80 transition-colors">{s.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
