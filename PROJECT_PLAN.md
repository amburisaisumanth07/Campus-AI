# CampusAI — AI-Powered College Knowledge & Student Support System
## Project Implementation Plan

### 1. Complete System Architecture
The system follows a modern three-tier architecture augmented with an AI/RAG layer:
- **Presentation Layer (Frontend)**: React + TypeScript (Vite) Single Page Application.
- **Application Layer (Backend)**: Python + FastAPI providing RESTful APIs.
- **AI/RAG Layer**: LangChain orchestrating data ingestion, retrieval, and LLM interactions.
- **Data Layer**: 
  - **Relational DB**: PostgreSQL (Users, Roles, Chat History, Feedback, Document Metadata).
  - **Vector DB**: Chroma (Document embeddings for semantic search).
- **Infrastructure Layer**: Dockerized containers managed via Docker Compose.

### 2. Component Responsibilities
- **React Frontend**: Handles UI rendering, state management, user interactions (chat interface, document upload dashboard), and API communication.
- **FastAPI Backend**: Acts as the central orchestrator. Handles authentication, routing, input validation, and business logic.
- **LangChain Core**: Manages the RAG pipeline (document loaders, text splitters, vector store integration, prompt templates, and LLM chains).
- **Gemini LLM**: Generates contextual responses based on retrieved context.
- **PostgreSQL**: Maintains stateful data with ACID properties.
- **Chroma**: Provides fast similarity search across embedded document chunks.

### 3. Database Design
**PostgreSQL Schema:**
- `users`: id, email, hashed_password, role (student/admin), created_at.
- `documents`: id, filename, original_name, category, department, academic_year, version, uploaded_by, uploaded_at, is_active.
- `conversations`: id, user_id, title, created_at, updated_at.
- `messages`: id, conversation_id, role (user/assistant), content, citations (JSON), created_at.
- `feedback`: id, message_id, user_id, rating (thumbs_up/thumbs_down), comments, created_at.

**Chroma Schema (Vector Store):**
- Collection: `campus_docs`
- Metadata: `doc_id`, `department`, `academic_year`, `page_number`, `chunk_index`.

### 4. RAG Architecture
1. **Query Processing**: User query is translated/optimized if needed (support for English + Telugu).
2. **Retrieval**: Query is embedded; Chroma performs similarity search with metadata filtering (department, academic year).
3. **Context Assembly**: Top-k chunks are retrieved and formatted into a context window.
4. **Generation**: The context and original query are passed to the Gemini LLM with a strict system prompt (Hallucination Control).
5. **Post-processing**: The response is structured with citations (source document and page number).

### 5. Document Ingestion Architecture
1. **Upload**: Admin uploads a PDF via the dashboard (metadata included).
2. **Text Extraction**: PDF parsed using robust libraries (e.g., PyMuPDF or pdfplumber) to preserve layout and tables.
3. **Cleaning**: Removal of headers/footers, special characters, and normalization.
4. **Intelligent Chunking**: LangChain's RecursiveCharacterTextSplitter or semantic chunking (respecting paragraphs/sections).
5. **Embedding**: Text chunks passed through an embedding model (e.g., Gemini Embeddings or HuggingFace).
6. **Storage**: Embeddings + Metadata stored in Chroma; File metadata stored in PostgreSQL.

### 6. API Architecture
RESTful endpoints built with FastAPI:
- `/api/auth/*`: Login, register, token refresh.
- `/api/admin/docs/*`: Upload, list, delete, update metadata, trigger indexing.
- `/api/chat/*`: Send message, retrieve conversation history.
- `/api/feedback/*`: Submit thumbs up/down and comments.

### 7. Authentication Architecture
- **Standard**: JWT (JSON Web Tokens) based authentication.
- **Flow**: User logs in -> Backend validates credentials against PostgreSQL -> Returns Access & Refresh tokens.
- **Authorization**: Role-Based Access Control (RBAC). Admin routes are protected by middleware checking the `role` claim in the JWT.

### 8. Frontend Architecture
- **Framework**: React with TypeScript for type safety.
- **State Management**: React Context or Zustand for global state (Auth, Theme).
- **Routing**: React Router for navigation (Login, Chat Interface, Admin Dashboard).
- **Styling**: Tailwind CSS (or Vanilla CSS with CSS Modules) for a responsive, modern aesthetic.
- **i18n**: `react-i18next` for English and Telugu UI support.

### 9. Security Considerations
- **Data Protection**: Passwords hashed using bcrypt.
- **API Security**: CORS configuration, rate limiting, and input validation (Pydantic).
- **Hallucination Control**: Strict LLM prompts instructing it to say "I don't know" if the answer is not in the context. Temperature set to 0 or 0.1 for deterministic output.
- **Document Access**: Only admins can upload/modify documents.

### 10. Testing Strategy
- **Unit Tests**: `pytest` for backend utilities and LangChain logic. Jest/React Testing Library for frontend components.
- **Integration Tests**: Testing FastAPI endpoints with test database instances.
- **E2E Tests**: Cypress or Playwright for critical flows (Login -> Ask Question -> View Answer).

### 11. Evaluation Strategy
- **RAG Evaluation**: Use frameworks like Ragas or TruLens to evaluate:
  - Context Precision (Did we retrieve the right chunks?)
  - Faithfulness (Is the answer derived *only* from the context?)
  - Answer Relevance (Does it answer the user's query?)
- **Continuous Monitoring**: Track thumbs down feedback in production to identify gaps in retrieval.

### 12. Docker Architecture
`docker-compose.yml` defining multiple services:
1. `frontend`: Node.js/Nginx serving the React app.
2. `backend`: Uvicorn server running FastAPI.
3. `db`: PostgreSQL container with persistent volumes.
4. `vector_db`: ChromaDB container with persistent volumes.

### 13. Development Milestones
- **Phase 1: Foundation**: Project setup, Docker configuration, Database schemas, Auth APIs.
- **Phase 2: Ingestion Engine**: PDF upload, extraction, chunking, embedding, Chroma integration.
- **Phase 3: RAG Engine**: Retrieval logic, LangChain orchestration, Gemini integration, Hallucination prompts.
- **Phase 4: API Integration**: Chat APIs, history, feedback, metadata filtering.
- **Phase 5: Frontend Interface**: React UI for Chat, Admin Dashboard, i18n support.
- **Phase 6: Polish & QA**: RAG evaluation, automated tests, UI refinements, production readiness.

### 14. Recommended Folder Structure
```text
campusAI/
├── docker-compose.yml
├── .env.example
├── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── i18n/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
└── backend/
    ├── app/
    │   ├── api/
    │   │   └── routes/
    │   ├── core/
    │   │   ├── config.py
    │   │   └── security.py
    │   ├── db/
    │   │   ├── models.py
    │   │   └── session.py
    │   ├── rag/
    │   │   ├── ingestion.py
    │   │   ├── retrieval.py
    │   │   └── llm.py
    │   ├── schemas/
    │   ├── services/
    │   └── main.py
    ├── tests/
    ├── requirements.txt
    └── Dockerfile
```
