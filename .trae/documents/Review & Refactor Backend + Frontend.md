## Key Findings (Current Pain Points)
- Duplicate backend implementations cause drift: legacy [backend.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/backend.py) vs packaged [server.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/api/server.py).
- Vercel entrypoints still reference legacy backend: [api/index.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/api/index.py).
- Frontend calls a non-existent endpoint: `/api/fs/upload` referenced in [App.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/App.tsx#L415-L426).
- Path safety is not enforced (potential traversal): [server.py get_safe_path](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/api/server.py#L47-L52).
- Frontend state and side-effects are centralized in [App.tsx](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/webapp/src/App.tsx), making changes risky and hard to test.

## Backend Refactor Plan
1. **Unify to a single FastAPI app**
   - Make `backend.py` a compatibility shim that re-exports the packaged app from `window_aichat.api.server`.
   - Update [api/index.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/api/index.py) to import the packaged app.
   - Outcome: One routing surface, no drift.

2. **Fix schema correctness + normalize contracts**
   - Fix mutable defaults (e.g., history lists) in [api_models.py](file:///c:/Users/bi/Desktop/window-aichat-branch/window-aichat/window_aichat/schemas/api_models.py).
   - Add explicit response models (`ChatResponse`, `ErrorResponse`) and return them consistently.
   - Outcome: Frontend stops guessing response shapes.

3. **Close the “broken endpoint” gap**
   - Either implement `/api/fs/upload` in the backend OR remove the upload wiring from the frontend.
   - Outcome: No dead UI paths.

4. **Security hardening for filesystem endpoints**
   - Introduce a single configured workspace root and enforce containment in `get_safe_path()`.
   - Ensure list/read/write do not escape the workspace.
   - Outcome: Safe to deploy.

5. **Centralized error handling**
   - Add global exception handlers with a stable error envelope `{ error: { code, message }, requestId }`.
   - Outcome: Better UX + no raw exception leakage.

6. **Streaming protocol refinement (WebSocket)**
   - Standardize WS messages as JSON frames (e.g., `{type:'chunk', content}` / `{type:'done'}` / `{type:'error'}`), add cancellation support.
   - Outcome: Reliable “live typing” in UI.

## Frontend Refactor Plan
1. **Add a typed API client layer**
   - Create `api/client.ts` that handles fetch, JSON parsing, and the backend error envelope.
   - Create `api/routes.ts` with functions for `chat`, `completion`, `fs`, `tool`, `clone`, `upload`, and `wsChat`.

2. **Split App.tsx into focused hooks**
   - Extract hooks like `useChat`, `useWorkspaceFs`, `useSettings`, `useAgent`.
   - Keep `App.tsx` as orchestration only.
   - Outcome: Smaller diffs, easier testing.

3. **Make streaming first-class in UI**
   - Add a WS client that streams tokens into the last assistant message.
   - Add retry/backoff, and clear user-visible error states.

4. **Stability improvements for code intelligence**
   - Isolate Tree-sitter + indexing work in a single service boundary; add guards and consistent initialization.
   - Outcome: fewer runtime surprises and easier debugging.

## Tests & CI Plan
1. **Backend tests (pytest)**
   - Add contract tests for `/api/chat`, fs safety tests for traversal, and upload behavior.

2. **Frontend tests (Vitest + RTL)**
   - Test API client error decoding + `useSettings` persistence + streaming reducer logic.

3. **Wire tests into CI**
   - Update workflow to run backend + frontend tests in addition to build.

## Suggested App Ideas (High-Leverage Features)
- **Project Sessions**: named workspaces with chat history, indexed context, and per-session settings.
- **Streaming Agent Tools**: tool calls that stream progress (clone repo, index files, run tests) into chat.
- **Patch Review Mode**: show diffs with accept/reject + auto-run tests before applying.
- **Secure Multi-User**: JWT auth + per-user workspace roots + rate limiting.
- **Observability**: request IDs, trace spans, usage metrics per model/tool.
- **Context Controls**: user-configurable context window, pinned files, “don’t include” rules, summarization.

## Definition of Done
- One backend entrypoint used everywhere (local + deploy), no duplicated servers.
- Frontend has a single API client + WS streaming integrated.
- `/api/fs/upload` is either implemented or removed end-to-end.
- Filesystem endpoints are containment-safe.
- Basic test suites run in CI and pass.

If you confirm this plan, I’ll execute it in the safest order: backend unification → contract fixes → upload gap → fs hardening → frontend API client + hooks → streaming UI → tests + CI.