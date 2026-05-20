---
name: add-chat-feature
description: 'Adds a new feature to the React chat UI — new event types, components, or interactions. Use when extending the chat interface, adding new SSE event rendering, or building new UI components.'
argument-hint: 'Describe the feature (e.g., "show agent thinking indicator", "render code blocks")'
---

## Purpose
Step-by-step workflow for adding a new feature to the React chat UI in `ts/apps/ui-copilot-template`.

## When to Use
- Adding a new SSE event type to the UI.
- Building a new chat component (e.g., code blocks, images, status cards).
- Extending the `useStreamingChat` hook with new state.

## Flow

1. **Define types** in `ts/apps/ui-copilot-template/src/types.ts`:
   - Add new type for the feature data:
     ```typescript
     export type ThinkingEvent = {
       status: "started" | "completed";
       thought?: string;
     };
     ```

2. **Update the SSE parser** in `src/lib/api.ts` → `streamChat()`:
   - Add a new callback parameter for the event.
   - Add parser branch for the new SSE event name:
     ```typescript
     if (event === "thinking") {
       const parsed: ThinkingEvent = JSON.parse(data);
       onThinking(parsed);
     }
     ```

3. **Update the hook** in `src/hooks/useStreamingChat.ts`:
   - Add state: `const [thinking, setThinking] = useState<ThinkingEvent | null>(null);`
   - Pass handler to `streamChat()`.
   - Expose in return value.

4. **Build the component** in `src/components/`:
   - Create `{Feature}Card.tsx` — follow `ToolCard.tsx` pattern:
     - Accept data via props.
     - Keep presentational — no API calls inside.
     - Handle null/loading states.

5. **Wire into App.tsx**:
   - Import the new component.
   - Render conditionally based on hook state.

6. **Verify backend emits the event**:
   - Ensure the backend `_stream_reply()` yields the matching SSE event.
   - If backend changes needed, follow `add-api-endpoint` skill.

## Decision Logic
- **New event type from backend**: Steps 1-5 (full flow).
- **UI-only feature** (no new events): Steps 4-5 only.
- **Restyling existing**: Modify component directly, no hook/type changes.

## Checklist
- [ ] TypeScript type defined in `types.ts`
- [ ] Parser branch added in `streamChat()`
- [ ] State + handler added in `useStreamingChat`
- [ ] Component built following `ToolCard.tsx` pattern
- [ ] Wired into `App.tsx`
- [ ] Backend emits matching event (if applicable)
- [ ] Responsive / mobile-safe layout
