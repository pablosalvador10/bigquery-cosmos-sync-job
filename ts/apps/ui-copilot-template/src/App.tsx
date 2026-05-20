import { AppHeader } from "./components/AppHeader";
import { ChatMessageList } from "./components/ChatMessageList";
import { ChatInput } from "./components/ChatInput";
import { useStreamingChat } from "./hooks/useStreamingChat";

export function App() {
  const { messages, loading, sendMessage } = useStreamingChat();

  return (
    <div className="relative bg-background h-screen flex flex-col overflow-hidden">
      <AppHeader />
      <main className="pt-[60px] md:pt-[64px] flex-1 flex flex-col min-h-0">
        <div className="flex flex-col h-full">
          <ChatMessageList messages={messages} isLoading={loading} onPromptClick={sendMessage} />
          <div className="border-t border-foreground/[0.04] bg-background/80 backdrop-blur-md">
            <div className="max-w-3xl mx-auto px-4 py-4">
              <ChatInput onSend={sendMessage} disabled={loading} />
              <p className="text-[10px] text-foreground/20 text-center mt-2.5 select-none">
                AI-generated responses may not always be accurate. Verify critical details.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
