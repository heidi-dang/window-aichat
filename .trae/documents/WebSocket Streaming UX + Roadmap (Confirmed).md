## WebSocket Streaming UX (Implementation)
### 1) Expand Chat hook API (no UI changes yet)
- Update `useChat.ts` to expose:
  - `isStreaming` state (derived from active stream)
  - `cancel()` method: sends `{type:"cancel"}`, closes socket, stops loading, preserves partial text
  - `regenerate()` method: replays the last request snapshot (model + user message + history)
  - `lastRequestRef`: stores `{ message, model, history, keysUsed }` at send time
- Keep the hook as the single source of truth for streaming state and request snapshots.

### 2) Typing indicator UX
- Update `ChatInterface.tsx`:
  - If the last assistant bubble is streaming and empty, render animated typing dots inside that bubble.
  - Remove/avoid the global “Thinking…” row; rely on per-message streaming state.

### 3) Cancel button
- Update `ChatInterface.tsx`:
  - Show a Cancel button in the header when `isStreaming`.
  - Wire it to `chat.cancel()` from `App.tsx`.

### 4) Partial-render markdown (safe)
- Add dependencies:
  - `react-markdown` + `remark-gfm`
- Update `ChatInterface.tsx`:
  - Render assistant messages using `react-markdown` (no raw HTML) and keep user messages as plain text.
  - Ensure code blocks render correctly (no HTML injection).

### 5) Regenerate UX
- Update `ChatInterface.tsx`:
  - Add “Regenerate” button (only when not streaming and when last request exists).
  - Behavior: starts a new stream using the stored request snapshot.

### 6) App wiring (hook structure)
- Update `App.tsx` to pass:
  - `onCancel`, `onRegenerate`, `isStreaming`, and `canRegenerate` into `ChatInterface`.

### 7) Verification
- Frontend: `npm run build`, `npm test`
- Optional smoke check via `npm run dev`:
  - streaming renders progressively
  - cancel stops the stream
  - regenerate works
  - markdown renders correctly

## Roadmap (Feature Ideas → Implementation Seams)
### A) Project Sessions (MVP → scalable)
- MVP: localStorage sessions
  - `session = {id,name,model,pinnedFiles,messageHistory,updatedAt}`
- Next: server persistence (SQLite via SQLAlchemy), per-user ownership.

### B) Streaming Agent Tools
- Standardize tool stream frames: `{type:"tool", stage, message, progress}`.
- Bridge to AgentLoop logs + optional WebContainer output.

### C) Patch Review Workflow
- Extend DiffModal:
  - “Run tests” before apply
  - auto-run `npm test` / `python -m pytest` (via backend runner or WebContainer)
  - only enable Apply if checks pass (with optional override)

### D) Security + Multi-user
- JWT auth + per-user workspace root enforcement.
- Rate limiting + audit log table for file writes.

### E) Context Controls
- UI: pinned files, exclude patterns, context window size.
- Backend: store per-session prefs; add summarization job.

### F) Developer Productivity Add-ons
- Commands: generate unit tests, explain stack traces, PR descriptions, repo Q&A with citations.
- Implementation: prompt templates + vector store retrieval + cite file ranges in responses.

## Definition of Done (for Streaming UX)
- Typing indicator shows inside the streaming assistant bubble.
- Cancel stops streaming and keeps partial text.
- Regenerate replays the last request snapshot.
- Markdown renders safely during streaming.
- Build + tests pass.