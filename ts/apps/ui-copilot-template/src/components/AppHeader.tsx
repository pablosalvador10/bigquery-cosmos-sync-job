import { cn } from "../lib/utils";
import { Sparkles } from "lucide-react";

export function AppHeader() {
  return (
    <header className={cn("fixed top-0 left-0 right-0 z-40 flex items-center justify-between px-4 md:px-6 lg:px-8 h-[60px] md:h-[64px] bg-background/70 backdrop-blur-md border-b border-foreground/[0.04]")}>
      <div className="flex items-center gap-2.5">
        <div className="h-8 w-8 rounded-lg bg-primary/[0.08] border border-primary/15 flex items-center justify-center">
          <Sparkles className="h-4 w-4 text-primary" strokeWidth={1.5} />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-foreground leading-tight">Agentic Template</span>
          <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-foreground/30 leading-tight hidden sm:block">Azure AI Copilot</span>
        </div>
      </div>
    </header>
  );
}
