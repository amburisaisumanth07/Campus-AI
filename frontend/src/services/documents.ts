import type { DocumentListResponse, DocumentDetail } from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem('campusai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function uploadDocumentApi(formData: FormData): Promise<DocumentDetail> {
  const response = await fetch(`${API_BASE_URL}/api/documents`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || 'Upload failed');
  }

  return response.json();
}

export async function listDocumentsApi(
  page = 1,
  pageSize = 20,
  statusFilter?: string
): Promise<DocumentListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (statusFilter) {
    params.append('status', statusFilter);
  }

  const response = await fetch(`${API_BASE_URL}/api/documents?${params.toString()}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch documents' }));
    throw new Error(errorData.detail || 'Failed to fetch documents');
  }

  return response.json();
}

export async function getDocumentApi(id: number): Promise<DocumentDetail> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch document' }));
    throw new Error(errorData.detail || 'Failed to fetch document');
  }

  return response.json();
}

export async function deleteDocumentApi(id: number): Promise<{ message: string; document_id: number }> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to delete document' }));
    throw new Error(errorData.detail || 'Failed to delete document');
  }

  return response.json();
}
