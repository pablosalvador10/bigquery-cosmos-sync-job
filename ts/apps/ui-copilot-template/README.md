# ui-copilot-template

React chat UI template with SSE streaming support for agentic applications.

## Stack

- React 19 + TypeScript
- Vite (dev server + build)
- nginx (Docker reverse proxy)

## Architecture

```
src/
├── App.tsx              ← Main chat UI component
├── main.tsx             ← Entry point
├── styles.css           ← Chat styles
├── types.ts             ← TypeScript types (Message, ToolEvent)
├── components/
│   └── ToolCard.tsx     ← Tool execution status card
├── hooks/
│   └── useStreamingChat.ts  ← Chat state + SSE parsing hook
└── lib/
    └── api.ts           ← API calls (postChat, streamChat)
```

## Key Patterns

### `useStreamingChat` hook

Manages chat session state (messages, tool events, loading) and calls `streamChat()`:

```typescript
const { sessionId, messages, toolEvent, loading, sendMessage } = useStreamingChat();
```

### `streamChat()` SSE parser

Posts to `/api/v1/chat/stream` and parses the SSE event stream:
- `event: delta` → appends token to current assistant message
- `event: tool_event` → updates `ToolEvent` state
- `event: done` → marks stream complete

### Adding a new event type

1. Add type to `types.ts`
2. Add parser branch in `streamChat()` (`lib/api.ts`)
3. Add state + handler in `useStreamingChat` hook
4. Add display component in `components/`

## Development

```bash
cd ts
pnpm install
pnpm --filter ui-copilot-template dev     # Start dev server on :5173
pnpm --filter ui-copilot-template build   # Production build
pnpm --filter ui-copilot-template lint    # ESLint
pnpm --filter ui-copilot-template typecheck  # TypeScript check
```

## Docker

```bash
docker compose up --build frontend
# Serves on :5173, proxies /api to backend via nginx
```
