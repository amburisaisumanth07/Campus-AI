# Milestone 11 — Chat UI

## 1. Objective
Build a responsive, modern React frontend Chat UI connecting students to the backend RAG Chat API (`POST /api/chat`, `GET /api/conversations`, `POST /api/feedback`), allowing users to create sessions, view chat history, ask questions, review document citations, and submit feedback.

## 2. Summary of Implementation
- Extended TypeScript types in `frontend/src/types/api.ts` to support `ChatMessageRequest`, `ChatMessageResponse`, `SourceCitation`, `CitationItem`, `ConversationResponse`, `ConversationDetailResponse`, `MessageResponse`, `FeedbackCreateRequest`, and `FeedbackResponse`.
- Extended service layer in `frontend/src/services/api.ts` with `sendChatMessageApi`, `listConversationsApi`, `createConversationApi`, `getConversationDetailApi`, `deleteConversationApi`, and `submitFeedbackApi`.
- Developed modular presentation components under `frontend/src/components/chat/`:
  - `ConversationSidebar.tsx`: Sidebar list of sessions, new chat creation, session deletion.
  - `ChatWindow.tsx`: Header, message stream, loading indicators, welcome chips.
  - `MessageBubble.tsx`: User vs assistant speech bubbles, grounded badges, feedback controls.
  - `CitationList.tsx`: Source document cards, page numbers, department/year tags, snippet previews.
  - `ChatInput.tsx`: Input box, keyboard shortcuts, loading states, optional RAG search filters.
- Created `ChatPage.tsx` container (`frontend/src/pages/Chat.tsx`) orchestrating session state, messaging flow, and API error handling.
- Added `/chat` protected route in `App.tsx` and updated `MainLayout.tsx` with sidebar navigation link.
- Added comprehensive styling in `frontend/src/index.css`.

## 3. Files Created & Modified

### New Files Created
- [frontend/src/pages/Chat.tsx](file:///c:/projects%20AI/campusAI/frontend/src/pages/Chat.tsx)
- [frontend/src/pages/Chat.test.tsx](file:///c:/projects%20AI/campusAI/frontend/src/pages/Chat.test.tsx)
- [frontend/src/components/chat/ConversationSidebar.tsx](file:///c:/projects%20AI/campusAI/frontend/src/components/chat/ConversationSidebar.tsx)
- [frontend/src/components/chat/ChatWindow.tsx](file:///c:/projects%20AI/campusAI/frontend/src/components/chat/ChatWindow.tsx)
- [frontend/src/components/chat/MessageBubble.tsx](file:///c:/projects%20AI/campusAI/frontend/src/components/chat/MessageBubble.tsx)
- [frontend/src/components/chat/CitationList.tsx](file:///c:/projects%20AI/campusAI/frontend/src/components/chat/CitationList.tsx)
- [frontend/src/components/chat/ChatInput.tsx](file:///c:/projects%20AI/campusAI/frontend/src/components/chat/ChatInput.tsx)
- [docs/ui/chat-ui.md](file:///c:/projects%20AI/campusAI/docs/ui/chat-ui.md)
- [docs/milestones/milestone-11.md](file:///c:/projects%20AI/campusAI/docs/milestones/milestone-11.md)

### Existing Files Modified
- [frontend/src/types/api.ts](file:///c:/projects%20AI/campusAI/frontend/src/types/api.ts)
- [frontend/src/services/api.ts](file:///c:/projects%20AI/campusAI/frontend/src/services/api.ts)
- [frontend/src/App.tsx](file:///c:/projects%20AI/campusAI/frontend/src/App.tsx)
- [frontend/src/layouts/MainLayout.tsx](file:///c:/projects%20AI/campusAI/frontend/src/layouts/MainLayout.tsx)
- [frontend/src/index.css](file:///c:/projects%20AI/campusAI/frontend/src/index.css)

## 4. API Endpoints Integrated
- `POST /api/chat`
- `GET /api/conversations`
- `POST /api/conversations`
- `GET /api/conversations/{id}`
- `DELETE /api/conversations/{id}`
- `POST /api/feedback`

## 5. Verification & Test Results
- **Frontend Test Suite**: 4 Test Files Passed, 17 Tests Passed in total (`vitest run`).
- **Frontend Build**: TypeScript type check (`tsc -b`) and Vite production build (`vite build`) passed clean with 0 errors.
- **Backend Test Suite**: 126 Passed, 10 Skipped, 0 Failed (`pytest backend/tests`).
