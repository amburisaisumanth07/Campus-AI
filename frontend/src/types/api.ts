export interface HealthResponse {
  status: string;
  database: string;
  [key: string]: any;
}

export type Role = 'STUDENT' | 'ADMIN' | 'FACULTY';
export type UserRole = Role;

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ApiErrorResponse {
  detail: string;
}

// ── Chat & Conversation types ──────────────────────────────────────────────────

export interface SourceCitation {
  document_id?: number | null;
  document_version_id?: number | null;
  title?: string | null;
  document_type?: string | null;
  department?: string | null;
  academic_year?: string | null;
  page_number?: number | null;
  source_pages?: number[];
  snippet?: string | null;
  source_type?: string | null;
  source_url?: string | null;
}

export interface CitationItem {
  doc_id?: number | null;
  document_id?: number | null;
  document_version_id?: number | null;
  title?: string | null;
  document_type?: string | null;
  department?: string | null;
  academic_year?: string | null;
  page_number?: number | null;
  source_pages?: number[];
  snippet?: string | null;
  source_type?: string | null;
  source_url?: string | null;
}

export type FeedbackRating = 'thumbs_up' | 'thumbs_down';

export interface FeedbackResponse {
  id: number;
  message_id: number;
  user_id: number;
  rating: FeedbackRating;
  comment?: string | null;
  created_at: string;
}

export interface MessageResponse {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationItem[] | null;
  feedback?: FeedbackResponse | null;
  created_at: string;
}

export interface ChatUIMessage extends Omit<Partial<MessageResponse>, 'feedback'> {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  citations?: (CitationItem | SourceCitation)[] | null;
  grounded?: boolean;
  feedback?: FeedbackResponse | { rating: FeedbackRating; comment?: string | null } | null;
  retrieval_error?: boolean;
  generation_error?: boolean;
  status?: string;
}

export interface ConversationResponse {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetailResponse {
  id: number;
  user_id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageResponse[];
}

export interface ConversationListResponse {
  items: ConversationResponse[];
  total: number;
}

export interface ChatMessageRequest {
  conversation_id?: number | null;
  message?: string;
  content?: string;
  department?: string;
  academic_year?: string;
}

export interface ChatMessageResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  grounded: boolean;
  retrieval_count: number;
  sources: SourceCitation[];
  user_message?: MessageResponse | null;
  assistant_message?: MessageResponse | null;
  retrieval_error?: boolean;
  generation_error?: boolean;
  status?: string;
}

export interface FeedbackCreateRequest {
  message_id: number;
  rating: FeedbackRating;
  comment?: string;
}

// ── Document types ────────────────────────────────────────────────────────────

export type DocumentType =
  | 'regulation'
  | 'academic_calendar'
  | 'examination'
  | 'attendance'
  | 'placement'
  | 'scholarship'
  | 'course'
  | 'notice'
  | 'department_document'
  | 'other';

export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED';

export interface DocumentVersion {
  id: number;
  version: string;
  file_checksum: string;
  file_size: number;
  mime_type: string;
  page_count: number | null;
  is_active: boolean;
  created_at: string;
}

export interface DocumentItem {
  id: number;
  title: string;
  filename: string;
  document_type: DocumentType;
  department: string | null;
  academic_year: string | null;
  status: DocumentStatus;
  uploaded_by_id: number;
  created_at: string;
  updated_at: string;
  active_version: DocumentVersion | null;
}

export interface DocumentDetail extends DocumentItem {
  versions: DocumentVersion[];
  page_count: number | null;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

// ── Website Source & Sync types ───────────────────────────────────────────────

export type WebsiteSourceStatus = 'ACTIVE' | 'IDLE' | 'SYNCING' | 'ERROR' | 'DISABLED';
export type SyncStatus = 'SUCCESS' | 'FAILED' | 'IN_PROGRESS';

export interface WebsiteSource {
  id: number;
  name: string;
  base_url: string;
  allowed_domains: string;
  allowed_paths?: string | null;
  active: boolean;
  auto_sync_enabled?: boolean;
  sync_interval: string;
  max_pages: number;
  last_checked_at?: string | null;
  last_successful_sync_at?: string | null;
  next_scheduled_sync_at?: string | null;
  status: WebsiteSourceStatus;
  last_error?: string | null;
  created_by_id: number;
  document_count: number;
  pending_review_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SyncChangeReview {
  id: number;
  source_id: number;
  history_id?: number | null;
  url: string;
  title: string;
  entity_type: string;
  change_type: 'NEW' | 'UPDATED' | 'REMOVED' | 'INVALID_URL' | 'FAILED';
  status: 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';
  previous_content?: string | null;
  new_content?: string | null;
  content_hash?: string | null;
  http_status?: number | null;
  error_reason?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebsiteSourceCreate {
  name: string;
  base_url: string;
  allowed_domains: string;
  allowed_paths?: string;
  active?: boolean;
  sync_interval?: string;
  max_pages?: number;
}

export interface WebsiteSourceUpdate {
  name?: string;
  base_url?: string;
  allowed_domains?: string;
  allowed_paths?: string;
  active?: boolean;
  sync_interval?: string;
  max_pages?: number;
}

export interface WebsiteSyncHistory {
  id: number;
  source_id: number;
  started_at: string;
  completed_at?: string | null;
  status: SyncStatus;
  documents_discovered: number;
  documents_added: number;
  documents_updated: number;
  documents_unchanged: number;
  documents_failed: number;
  error_message?: string | null;
}

export interface SyncTriggerResponse {
  message: string;
  source_id: number;
  history_id?: number | null;
  status: string;
}

export interface SourceStatusResponse {
  source_id: number;
  name: string;
  status: WebsiteSourceStatus;
  last_checked_at?: string | null;
  last_successful_sync_at?: string | null;
  total_documents: number;
  latest_history?: WebsiteSyncHistory | null;
}

// ── Official Attendance types ───────────────────────────────────────────────────

export interface AttendanceSubject {
  code: string;
  name: string;
  attended: number;
  total: number;
  percentage: number;
}

export interface AttendanceResponse {
  success: boolean;
  student_name: string;
  roll_number: string;
  overall_percentage: number;
  attended_classes: number;
  total_classes: number;
  absent_classes: number;
  required_percentage: number;
  is_safe: boolean;
  status_text: string;
  subjects: AttendanceSubject[];
  official_source: string;
  last_updated: string;
}

export interface AttendanceCheckRequest {
  roll_number: string;
  password: string;
}



