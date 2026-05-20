import { useState, useRef, useCallback, useEffect, type KeyboardEvent } from "react";
import { cn } from "../lib/utils";
import { ArrowUp } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, []);

  useEffect(() => { adjustHeight(); }, [value, adjustHeight]);
  useEffect(() => { ref.current?.focus(); }, []);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    requestAnimationFrame(() => {
      if (ref.current) { ref.current.style.height = "auto"; ref.current.focus(); }
    });
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }, [handleSend]);

  const canSend = value.trim().length > 0 && !disabled;

  return (
    <div className={cn("relative flex items-end gap-2 bg-card border border-foreground/[0.08] rounded-2xl px-4 py-2.5 shadow-[0_2px_12px_rgba(0,0,0,0.04)] focus-within:border-foreground/[0.15] focus-within:shadow-[0_2px_20px_rgba(0,0,0,0.07)] transition-all duration-200")}>
      <textarea ref={ref} value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask something..." disabled={disabled} rows={1} className="flex-1 resize-none bg-transparent text-[15px] text-foreground placeholder:text-foreground/30 leading-relaxed py-1 focus:outline-none disabled:opacity-50 max-h-[200px] scrollbar-thin" />
      <button type="button" onClick={handleSend} disabled={!canSend} className={cn("flex-shrink-0 h-9 w-9 rounded-xl flex items-center justify-center transition-all duration-200", canSend ? "bg-foreground text-background hover:bg-foreground/80 active:scale-95" : "bg-foreground/[0.06] text-foreground/20 cursor-not-allowed")} aria-label="Send message">
        <ArrowUp className="h-[18px] w-[18px]" strokeWidth={2} />
      </button>
    </div>
  );
}
