import { cn } from "../lib/utils";
import { Bot } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in opacity-0">
      <div className={cn("flex-shrink-0 h-8 w-8 rounded-full bg-primary/[0.08] text-primary flex items-center justify-center border border-primary/15 mt-0.5")}>
        <Bot className="h-4 w-4" strokeWidth={1.5} />
      </div>
      <div className="rounded-2xl rounded-bl-md bg-card border border-foreground/[0.06]">
        <div className="flex items-center gap-1.5 px-3 py-2.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className={cn("h-[7px] w-[7px] rounded-full bg-foreground/25 animate-pulse-dot", i === 1 && "animation-delay-200", i === 2 && "animation-delay-400")} />
          ))}
        </div>
      </div>
    </div>
  );
}
