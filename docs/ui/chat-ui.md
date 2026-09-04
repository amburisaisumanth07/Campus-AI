# CampusAI — Chat UI Architecture & User Experience

## 1. Overview
The **Chat UI** is the primary interactive student interface for CampusAI. It connects the React single-page frontend application with the document-grounded RAG Chat API backend (`POST /api/chat`, `GET /api/conversations`, `POST /api/feedback`).

## 2. Component Architecture
```text
ChatPage (Container & State Orchestrator)
├── ConversationSidebar
│   ├── NewConversationButton ("+ New Chat")
│   └── ConversationList
│       └── ConversationItem (Title, Date, Active Indicator, Delete Action)
│
└── ChatWindow
    ├── ChatHeader (Title, Grounded Badge, System Subtitle)
    ├── MessageStream
    │   ├── WelcomeState / PromptChips
    │   └── MessageBubble (User vs CampusAI Assistant)
    │       ├── GroundedBadge
    │       ├── CitationList (Expandable source document cards & page numbers)
    │       └── FeedbackControls (Thumbs Up / Thumbs Down & Comment Form)
    └── ChatInput
        ├── RAGFilterPanel (Department & Academic Year search filters)
        └── MessageForm (Textarea, Keyboard shortcuts, Loading spinner, Send button)
```

## 3. Key Components & Responsibilities

### 3.1 `ChatPage` (`frontend/src/pages/Chat.tsx`)
- Maintains global active session state (`activeId`).
- Orchestrates network requests to `sendChatMessageApi`, `listConversationsApi`, `createConversationApi`, `getConversationDetailApi`, `deleteConversationApi`, and `submitFeedbackApi`.
- Manages user and assistant message stream state, optimistic UI rendering, loading states, and error handling.

### 3.2 `ConversationSidebar` (`frontend/src/components/chat/ConversationSidebar.tsx`)
- Renders list of user conversation sessions sorted by recency.
- Handles conversation creation ("+ New Chat") and session deletion with confirmation dialogs.

### 3.3 `ChatWindow` (`frontend/src/components/chat/ChatWindow.tsx`)
- Renders conversation header, message list, loading indicators, and fixed chat input.
- Automatically scrolls to bottom on new messages.

### 3.4 `MessageBubble` (`frontend/src/components/chat/MessageBubble.tsx`)
- Renders user speech bubbles and assistant response bubbles.
- Displays `Grounded Answer` badges when response is backed by retrieved documents.
- Includes interactive feedback controls (👍 / 👎) connected to `/api/feedback`.

### 3.5 `CitationList` (`frontend/src/components/chat/CitationList.tsx`)
- Renders authoritative source provenance returned by the backend.
- Displays document title, page numbers (`Page X` / `Pages X, Y`), department, academic year, and snippet previews.

### 3.6 `ChatInput` (`frontend/src/components/chat/ChatInput.tsx`)
- Controlled textarea preventing empty or whitespace-only submissions.
- Keyboard support (`Enter` to submit, `Shift+Enter` for line break).
- RAG metadata filter toggle for targeted department or academic year search.

## 4. API Integration & Authentication
- Authenticated via JWT Bearer token supplied by `useAuth()`.
- API base URL resolved dynamically via `VITE_API_BASE_URL`.
- Endpoints used:
  - `POST /api/chat`: Send query & retrieve grounded answer with citations.
  - `GET /api/conversations`: Retrieve user's conversation sessions.
  - `POST /api/conversations`: Create new conversation session.
  - `GET /api/conversations/{id}`: Load messages for a session.
  - `DELETE /api/conversations/{id}`: Delete conversation session.
  - `POST /api/feedback`: Submit thumbs up/down and comments for assistant responses.

## 5. User Flows & Error UX
- **Loading State**: Disables send button, displays `CampusAI is thinking...` spinner bubble.
- **Error Handling**: Catches network/API exceptions and displays user-friendly error banners without exposing technical backend stack traces.
