I will upgrade the entire application stack, focusing on a "Goddess-tier" modernization of the Web App and backend integration.

### Phase 1: Backend Architecture Upgrade (Python)
**Goal:** Expose powerful AI capabilities to the frontend via a robust API.
1.  **Update `backend.py`**:
    *   Implement `POST /api/chat`: A unified endpoint that accepts messages and uses `ai_core.AIChatClient` to route to Gemini or DeepSeek.
    *   Implement `POST /api/completion`: An endpoint specifically for code editor autocompletion.
    *   Implement `POST /api/git/clone`: Expose the existing `github_handler.py` logic to the web interface.
2.  **Verify `ai_core.py` Integration**: Ensure the backend correctly initializes the AI client and handles API keys securely.

### Phase 2: Modern UI/UX Overhaul (React + Tailwind)
**Goal:** Transform the monolithic `App.tsx` into a professional, modular IDE interface.
1.  **Install Dependencies**:
    *   `lucide-react`: For modern, consistent SVG icons.
    *   `clsx`, `tailwind-merge`: For clean dynamic class handling.
2.  **Modular Refactoring**:
    *   Create `src/components/Layout/Sidebar.tsx`: A collapsible, icon-based navigation bar.
    *   Create `src/components/Editor/EditorPanel.tsx`: A wrapper around Monaco Editor with tabs and status bar.
    *   Create `src/components/Chat/ChatInterface.tsx`: A polished chat UI with distinct user/AI message bubbles, avatars, and markdown rendering.
3.  **Visual Polish**:
    *   Apply a dark/modern theme consistent with VS Code.
    *   Add smooth transitions and hover states.

### Phase 3: "Goddess" Performance Optimization
**Goal:** Ensure the app feels instant and handles heavy loads.
1.  **Chat Virtualization**: Implement rendering optimizations in the chat list to handle long conversations without lag.
2.  **Optimistic UI**: Display user messages immediately while waiting for the server response.
3.  **Memoization**: Apply `React.memo` to heavy components (Editor, Terminal) to prevent unnecessary re-renders during typing.

### Phase 4: Integration & Verification
1.  **End-to-End Test**: Verify that the Web App can read/write files, execute AI commands, and clone repos via the updated backend.
2.  **Build Check**: Ensure `npm run build` passes with the new component structure.
