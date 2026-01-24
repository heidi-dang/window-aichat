## What You Asked For (Scope)
- Implement a richer WebSocket streaming chat UX: typing indicator, cancel button, partial-render markdown, and “regenerate” using the new hook structure.
- Keep the bigger feature ideas (Project Sessions, Streaming Agent Tools, Patch Review, Security, Context Controls, Dev Add-ons) as a structured roadmap with clear implementation seams.

## Current State (What We Have)
- WebSocket `/ws/chat` already streams JSON frames (`start/chunk/done/error`) and supports cancel (`{type:"cancel"}`) in [server.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/api/server.py).
- Frontend hook [useChat.ts](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/hooks/useChat.ts) streams chunks into the last assistant message, but the UI still shows a generic “Thinking…” and there’s no explicit Cancel/Regenerate UX.
- Web chat rendering is plain text in [ChatInterface.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/Chat/ChatInterface.tsx) (no markdown renderer dependency yet).

## Plan: WebSocket Streaming UX (Implementation)
### 1) Expand Chat hook API (no UI changes yet)
- Add to [useChat.ts](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/hooks/useChat.ts):
  - `isStreaming` state (derived from active stream)
  - `cancel()` method: sends `{type:"cancel"}`, closes socket, stops loading, preserves partial text
  - `regenerate()` method: reuses the last request snapshot (model + user message + history) and starts a new stream
  - Track `lastRequestRef` that stores `{ message, model, history, keysUsed }` at send time

### 2) Typing indicator UX
- Update [ChatInterface.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/Chat/ChatInterface.tsx):
  - If the last assistant bubble is streaming and currently empty, render an animated typing indicator (dots) inside that bubble.
  - Replace the old global “Thinking…” row with per-message streaming state (so it feels like the assistant is typing in-place).

### 3) Cancel button
- Update [ChatInterface.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/Chat/ChatInterface.tsx):
  - Add a Cancel button in the header when `isStreaming`.
  - Wire it to `chat.cancel()` from App.

### 4) Partial-render markdown (safe)
- Add dependencies:
  - `react-markdown` + `remark-gfm`
- Update [ChatInterface.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/Chat/ChatInterface.tsx):
  - Render assistant messages via `react-markdown` (no raw HTML) and keep user messages as plain text.
  - Ensure code blocks are displayed correctly (no HTML injection).

### 5) Regenerate UX
- Update [ChatInterface.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/Chat/ChatInterface.tsx):
  - Add “Regenerate” (only when not streaming, and when there is a last request).
  - Behavior: starts a new streaming response using the same conversation history snapshot and model.

### 6) App wiring (hook structure)
- Update [App.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/App.tsx) to pass:
  - `onCancel`, `onRegenerate`, and `isStreaming` into `ChatInterface`.

### 7) Verification
- Frontend: `npm run build`, `npm test`
- Optional: a small Playwright-less manual smoke test script by running `npm run dev` and verifying:
  - stream renders progressively
  - cancel stops the stream
  - regenerate works
  - markdown renders correctly

## Roadmap: Your Bigger Feature Ideas (How We’ll Implement Them)
### A) Project Sessions (MVP → scalable)
- MVP: localStorage sessions (fast, no backend migrations)
  - session = `{id,name,model,pinnedFiles,messageHistory,updatedAt}`
- Next: persist sessions server-side (SQLite via SQLAlchemy) with per-user ownership.

### B) Streaming Agent Tools
- Standardize “tool run events” as stream frames (similar to chat): `{type:"tool", stage, message, progress}`.
- Tie into existing AgentLoop logs and optionally WebContainer execution output.

### C) Patch Review Workflow
- Extend existing DiffModal to:
  - show “Run tests” before apply
  - auto-run `npm test` / `python -m pytest` (via backend runner or WebContainer)
  - only enable “Apply” if checks pass (or allow override)

### D) Security + Multi-user
- Add JWT auth + per-user workspace root enforcement (builds on current workspace containment).
- Add rate limiting middleware + audit log table for file writes.

### E) Context Controls
- UI for pinned files, exclude patterns, context window size.
- Backend: store per-session context prefs; add summarization job.

### F) Developer Productivity Add-ons
- Commands: generate unit tests, explain stack traces, PR descriptions, repo Q&A with citations.
- Implementation: prompt templates + vector store retrieval + “cite file ranges” in responses.

## Definition of Done (for this next step)
- Chat shows in-place typing indicator.
- Cancel button stops streaming and keeps partial text.
- Markdown renders progressively (safe rendering).
- Regenerate replays the last request (same model + history snapshot).
- Build + tests pass.
