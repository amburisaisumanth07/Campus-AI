import type {
  HealthResponse,
  User,
  TokenResponse,
  ChatMessageRequest,
  ChatMessageResponse,
  ConversationListResponse,
  ConversationResponse,
  ConversationDetailResponse,
  FeedbackCreateRequest,
  FeedbackResponse,
  AttendanceResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function extractErrorMessage(data: any, fallback: string): string {
  if (!data) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
  }
  if (typeof data.message === 'string') return data.message;
  return fallback;
}

function isNetworkError(error: any): boolean {
  if (!error) return false;
  if (error.name === 'TypeError') {
    const msg = (error.message || '').toLowerCase();
    if (
      msg.includes('fetch') ||
      msg.includes('network') ||
      msg.includes('load failed') ||
      msg.includes('failed to fetch') ||
      msg.includes('connection')
    ) {
      return true;
    }
  }
  return false;
}

export function handleAuthStatus(response: Response): void {
  if (response.status === 401 || response.status === 403) {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('campusai:unauthorized'));
    }
  }
}

export const checkHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/health/`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error: any) {
    if (isNetworkError(error)) {
      throw new Error(`Unable to connect to backend server at ${API_BASE_URL}. Please ensure the backend is running.`);
    }
    throw error;
  }
};

export const registerApi = async (name: string, email: string, password: string): Promise<User> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(extractErrorMessage(data, 'Registration failed'));
    }
    return data;
  } catch (error: any) {
    if (isNetworkError(error)) {
      throw new Error('Unable to connect to backend server at ' + API_BASE_URL + '. Please ensure the backend is running.');
    }
    throw error;
  }
};

export const loginApi = async (email: string, password: string): Promise<TokenResponse> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(extractErrorMessage(data, 'Invalid email or password'));
    }
    return data;
  } catch (error: any) {
    if (isNetworkError(error)) {
      throw new Error('Unable to connect to backend server at ' + API_BASE_URL + '. Please ensure the backend is running.');
    }
    throw error;
  }
};

export const getMeApi = async (token: string): Promise<User> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      handleAuthStatus(response);
      throw new Error(extractErrorMessage(data, 'Failed to authenticate user'));
    }
    return data;
  } catch (error: any) {
    if (isNetworkError(error)) {
      throw new Error('Unable to connect to backend server at ' + API_BASE_URL + '. Please ensure the backend is running.');
    }
    throw error;
  }
};

// ── Chat & Conversation API Methods ──────────────────────────────────────────

export const sendChatMessageApi = async (
  token: string,
  payload: ChatMessageRequest
): Promise<ChatMessageResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    handleAuthStatus(response);
    throw new Error(data.detail || 'Failed to send message');
  }
  return data;
};

export const listConversationsApi = async (token: string): Promise<ConversationListResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    handleAuthStatus(response);
    throw new Error(data.detail || 'Failed to list conversations');
  }
  return data;
};

export const createConversationApi = async (
  token: string,
  title: string = 'New Chat'
): Promise<ConversationResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ title }),
  });

  const data = await response.json();
  if (!response.ok) {
    handleAuthStatus(response);
    throw new Error(data.detail || 'Failed to create conversation');
  }
  return data;
};

export const getConversationDetailApi = async (
  token: string,
  conversationId: number
): Promise<ConversationDetailResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/conversations/${conversationId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
  });

  const data = await response.json();
  if (!response.ok) {
    handleAuthStatus(response);
    throw new Error(data.detail || 'Failed to load conversation details');
  }
  return data;
};

export const deleteConversationApi = async (
  token: string,
  conversationId: number
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok && response.status !== 204) {
    handleAuthStatus(response);
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to delete conversation');
  }
};

export const submitFeedbackApi = async (
  token: string,
  payload: FeedbackCreateRequest
): Promise<FeedbackResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    handleAuthStatus(response);
    throw new Error(data.detail || 'Failed to submit feedback');
  }
  return data;
};

// ── Official MITS Knowledge Hub API Methods ──────────────────────────────────

export interface AnnouncementItem {
  id: number;
  title: string;
  description?: string | null;
  content?: string | null;
  category: string;
  published_date?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  document_url?: string | null;
  source_name: string;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface AcademicCalendarItem {
  id: number;
  academic_year: string;
  program: string;
  year?: string | null;
  semester?: string | null;
  event_name: string;
  event_description?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  document_url?: string | null;
  source_name: string;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface ExaminationItem {
  id: number;
  title: string;
  exam_type: string;
  program?: string | null;
  year?: string | null;
  semester?: string | null;
  published_date?: string | null;
  exam_date?: string | null;
  description?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  document_url?: string | null;
  source_name: string;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface FacultyItem {
  id: number;
  name: string;
  designation?: string | null;
  qualification?: string | null;
  department?: string | null;
  email?: string | null;
  phone?: string | null;
  profile_url?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface DepartmentItem {
  id: number;
  code: string;
  name: string;
  school?: string | null;
  description?: string | null;
  hod?: string | null;
  hod_name?: string | null;
  hod_designation?: string | null;
  hod_profile_url?: string | null;
  phone?: string | null;
  email?: string | null;
  faculty?: string | null;
  programs?: string | null;
  courses?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface PlacementItem {
  id: number;
  company: string;
  job_role?: string | null;
  drive_date?: string | null;
  eligibility?: string | null;
  description?: string | null;
  package_details?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  document_url?: string | null;
  is_valid?: boolean;
  last_verified_at?: string | null;
  created_at: string;
}

export interface CollegeInfoItem {
  id: number;
  key: string;
  title: string;
  content: string;
  category: string;
  source_url?: string | null;
  canonical_url?: string | null;
  is_valid?: boolean;
  last_verified_at?: string | null;
}

export interface ImportantLinkItem {
  id: number;
  title: string;
  description?: string | null;
  url: string;
  canonical_url?: string | null;
  category: string;
  icon?: string | null;
  display_order: number;
  is_valid?: boolean;
  is_active: boolean;
  last_verified_at?: string | null;
}

export interface SearchResultItem {
  id: number;
  type: string;
  title: string;
  category?: string | null;
  date?: string | null;
  description?: string | null;
  source_url?: string | null;
  canonical_url?: string | null;
  is_valid?: boolean;
  link_url: string;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  results: SearchResultItem[];
}

export const getAnnouncementsApi = async (category?: string, limit: number = 20): Promise<AnnouncementItem[]> => {
  const url = new URL(`${API_BASE_URL}/api/announcements`);
  if (category) url.searchParams.set('category', category);
  url.searchParams.set('limit', limit.toString());
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to load announcements');
  return res.json();
};

export const getAnnouncementByIdApi = async (id: number): Promise<AnnouncementItem> => {
  const res = await fetch(`${API_BASE_URL}/api/announcements/${id}`);
  if (!res.ok) throw new Error('Failed to load announcement details');
  return res.json();
};

export const getAcademicCalendarApi = async (params?: {
  academic_year?: string;
  program?: string;
  year?: string;
  semester?: string;
  upcoming_only?: boolean;
  limit?: number;
}): Promise<AcademicCalendarItem[]> => {
  const url = new URL(`${API_BASE_URL}/api/academic-calendar`);
  if (params?.academic_year) url.searchParams.set('academic_year', params.academic_year);
  if (params?.program) url.searchParams.set('program', params.program);
  if (params?.year) url.searchParams.set('year', params.year);
  if (params?.semester) url.searchParams.set('semester', params.semester);
  if (params?.upcoming_only) url.searchParams.set('upcoming_only', 'true');
  if (params?.limit) url.searchParams.set('limit', params.limit.toString());
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to load academic calendar');
  return res.json();
};

export const getExaminationsApi = async (params?: {
  exam_type?: string;
  program?: string;
  year?: string;
  semester?: string;
}): Promise<ExaminationItem[]> => {
  const url = new URL(`${API_BASE_URL}/api/examinations`);
  if (params?.exam_type) url.searchParams.set('exam_type', params.exam_type);
  if (params?.program) url.searchParams.set('program', params.program);
  if (params?.year) url.searchParams.set('year', params.year);
  if (params?.semester) url.searchParams.set('semester', params.semester);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to load examinations');
  return res.json();
};

export const getDepartmentsApi = async (): Promise<DepartmentItem[]> => {
  const res = await fetch(`${API_BASE_URL}/api/departments`);
  if (!res.ok) throw new Error('Failed to load departments');
  return res.json();
};

export const getDepartmentByCodeApi = async (codeOrId: string): Promise<DepartmentItem> => {
  const res = await fetch(`${API_BASE_URL}/api/departments/${codeOrId}`);
  if (!res.ok) throw new Error('Failed to load department details');
  return res.json();
};

export const getDepartmentFacultyApi = async (codeOrId: string): Promise<FacultyItem[]> => {
  const res = await fetch(`${API_BASE_URL}/api/departments/${codeOrId}/faculty`);
  if (!res.ok) throw new Error('Failed to load department faculty');
  return res.json();
};

export const getPlacementsApi = async (): Promise<PlacementItem[]> => {
  const res = await fetch(`${API_BASE_URL}/api/placements`);
  if (!res.ok) throw new Error('Failed to load placements');
  return res.json();
};

export const getCollegeInfoApi = async (): Promise<CollegeInfoItem[]> => {
  const res = await fetch(`${API_BASE_URL}/api/college/info`);
  if (!res.ok) throw new Error('Failed to load college information');
  return res.json();
};

export const getImportantLinksApi = async (): Promise<ImportantLinkItem[]> => {
  const res = await fetch(`${API_BASE_URL}/api/college/links`);
  if (!res.ok) throw new Error('Failed to load important links');
  return res.json();
};

export const searchCollegeApi = async (query: string): Promise<SearchResponse> => {
  const res = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
};

export const checkAttendanceApi = async (
  rollNumber: string,
  password: string
): Promise<AttendanceResponse> => {
  const response = await fetch(`${API_BASE_URL}/api/attendance/check`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ roll_number: rollNumber.trim().toUpperCase(), password }),
  });

  if (!response.ok) {
    let errData: any;
    try {
      errData = await response.json();
    } catch {
      errData = null;
    }
    const msg = extractErrorMessage(
      errData,
      response.status === 503
        ? 'Official attendance integration is currently unavailable.'
        : 'Failed to retrieve attendance from official system.'
    );
    throw new Error(msg);
  }

  return await response.json();
};



