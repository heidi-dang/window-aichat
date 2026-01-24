## Where You Are Today (Repo Reality)
- **Backend packaged runtime path** is `window_aichat/api/server.py` (FastAPI + `/ws/chat` streaming) and Vercel points to it: [index.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/api/index.py), [server.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/api/server.py).
- **Core “super-context primitives” already exist but are not orchestrated**:
  - Prompt templating: [context.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/core/context.py)
  - Token utilities: [tokens.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/core/tokens.py)
  - Model engine: [engine.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/core/engine.py)
- **Frontend has the beginnings of the “moat”**:
  - In-browser RAG + embeddings: [VectorStoreService.ts](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/utils/VectorStoreService.ts)
  - Task/agent loop: [AgentLoop.ts](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/agent/AgentLoop.ts)
  - Patch review UI: [DiffModal.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/components/DiffModal.tsx)
  - WebSocket streaming UX controls (cancel/regenerate): [useChat.ts](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/hooks/useChat.ts)
- **Key risk:** the repo contains multiple legacy copies (`window-aichat/**`, root `backend.py`, etc.). V1 should treat `window_aichat/**` + `webapp/**` as the only execution path.

## Architecture Diagram (Text)
**Goal:** Context is an independent pipeline, not an emergent side-effect of chat.

```
UI (Chat / Task / Memory / Artifacts)
  |   
  | emits: TaskIntent + UserMessage + UIState + PinnedItems
  v
Context Orchestrator (client-first in V1; server-assisted in V2)
  - Collect: immediate turns, working set, pinned files, retrieved chunks
  - Score: recency + relevance + pin + task affinity
  - Route: decide what goes to which model
  - Compress: summarize older context to fit budget
  - Produce: ModelRequest (structured)
  v
Model Router / Registry
  - choose model(s) by latency/cost/task type
  - optional consensus
  v
Execution Layer
  - Chat stream (/ws/chat)
  - Tool streams (clone/index/test/run)
  - Artifact writes + diffs
  v
Memory + Artifact Stores
  - V1: localStorage + workspace files + in-browser vector index
  - V2: DB + embeddings table + audit logs + multi-user
```

## Non-Obvious MVP Cut (Still “Revolutionary”)
**Ship V1 as “Task OS with Transparent Context”** (not a chat app):
- **Project Sessions (local-first)**: sessions contain `goal`, `model`, `pinned files`, `chat timeline`, and `task artifacts references`.
- **Context Visibility Panel**: always shows exactly what context the model will see, with scores and reasons.
- **One-click “Explain Why”**: show why a chunk/file/message was included (recency/relevance/pin/task affinity).
- **Deterministic Context Pack**: every run stores the exact context pack used (enables replay and trust).

This gives you the moat feel without needing DB/auth/migrations yet.

## V1 vs V2 Implementation Plan
### V1 (Foundational, product-shippable, minimal backend churn)
1. **Context Orchestrator v0 (client-side first)**
   - Create a `ContextItem` model + buckets: Immediate / Working / LongTerm / Artifacts.
   - Implement scoring + selection + token budgeting using existing RAG results and pinned files.
   - Output a structured `ModelRequest` and store the generated “context pack” per message.

2. **Project Sessions (localStorage)**
   - Session schema: `{id,name,model,pinnedFiles,messageHistory,artifactsIndex,updatedAt}`.
   - Add Session switcher + “New session from current task” flow.

3. **Artifact-first UX improvements**
   - Upgrade DiffModal workflow to record provenance: which task, which context pack, which model.
   - Add “Run tests before apply” (WebContainer runner first, since it already exists).

4. **Streaming Agent Tools (UI-level)**
   - Standardize tool progress frames in the UI (even if backend isn’t emitting them yet).
   - AgentLoop emits `{type:'tool', stage, message, progress}` into the UI stream.

5. **Backend alignment (small but critical)**
   - Replace remaining prompt string concatenation with the existing `PromptTemplate`.
   - Apply `Tokenizer.trim_context` before calling models.

### V2 (Platform features: multi-user, persistence, security, cost engineering)
1. **Server-side memory + embeddings**
   - Add DB + migrations (Alembic), embeddings table, retrieval endpoints.
   - Move “long-term memory” from browser-only to server-backed and encrypted.

2. **Security + Multi-user**
   - JWT auth, per-user workspace root enforcement, rate limiting, audit logs.

3. **Model-agnostic intelligence layer**
   - Capability registry, dynamic routing, fallback/degradation, multi-model consensus.

4. **Autonomous mode**
   - Planning mode → execution mode with approval gates + background tasks.

## Competitive Moat Analysis (What Becomes Hard to Copy)
- **Context packs + explainability + deterministic replay**: competitors can’t easily replicate the trust + reproducibility story.
- **Task objects + artifact provenance**: outputs become assets with lineage (not chat text).
- **Hybrid memory (local-first + server-backed)**: fast UX + secure sync.
- **Tool streaming as a first-class protocol**: visible progress and interruption control.

## Definition of Done for V1
- Session system exists and restores state.
- Context panel shows “what the model sees” + scoring.
- Context packs are stored per response (replayable).
- Artifacts are created with provenance + optional test gate.
- Backend uses PromptTemplate + token trimming instead of raw concatenation.

If you confirm, I will implement V1 in the repo using the existing `webapp/src/hooks` structure and the existing backend `window_aichat/api/server.py`, keeping legacy folders untouched.