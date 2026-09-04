import type {
  WebsiteSource,
  WebsiteSourceCreate,
  WebsiteSourceUpdate,
  WebsiteSyncHistory,
  SyncTriggerResponse,
  SourceStatusResponse,
  SyncChangeReview,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(tokenOverride?: string): Record<string, string> {
  const token = tokenOverride || localStorage.getItem('campusai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function listWebsiteSourcesApi(tokenOverride?: string): Promise<WebsiteSource[]> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch sources' }));
    throw new Error(errorData.detail || 'Failed to fetch website sources');
  }

  const data = await response.json();
  if (Array.isArray(data)) {
    return data;
  }
  if (data && Array.isArray((data as any).items)) {
    return (data as any).items;
  }
  if (data && Array.isArray((data as any).sources)) {
    return (data as any).sources;
  }
  return [];
}

export async function createWebsiteSourceApi(
  payload: WebsiteSourceCreate,
  tokenOverride?: string
): Promise<WebsiteSource> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to create website source');
  }

  return data;
}

export async function getWebsiteSourceApi(id: number, tokenOverride?: string): Promise<WebsiteSource> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch source' }));
    throw new Error(errorData.detail || 'Failed to fetch website source');
  }

  return response.json();
}

export async function updateWebsiteSourceApi(
  id: number,
  payload: WebsiteSourceUpdate,
  tokenOverride?: string
): Promise<WebsiteSource> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to update website source');
  }

  return data;
}

export async function deleteWebsiteSourceApi(id: number, tokenOverride?: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}`, {
    method: 'DELETE',
    headers: {
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok && response.status !== 204) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to delete source' }));
    throw new Error(errorData.detail || 'Failed to delete website source');
  }
}

export async function triggerSyncApi(id: number, tokenOverride?: string): Promise<SyncTriggerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Failed to trigger synchronization');
  }

  return data;
}

export async function getSyncHistoryApi(id: number, tokenOverride?: string): Promise<WebsiteSyncHistory[]> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}/sync-history`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to load sync history' }));
    throw new Error(errorData.detail || 'Failed to load sync history');
  }

  const data = await response.json();
  if (Array.isArray(data)) {
    return data;
  }
  if (data && Array.isArray((data as any).items)) {
    return (data as any).items;
  }
  return [];
}

export async function getSourceStatusApi(id: number, tokenOverride?: string): Promise<SourceStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}/status`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch status' }));
    throw new Error(errorData.detail || 'Failed to fetch source status');
  }

  return response.json();
}

export async function pauseSourceSyncApi(id: number, tokenOverride?: string): Promise<WebsiteSource> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}/pause`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to pause auto-sync' }));
    throw new Error(errorData.detail || 'Failed to pause auto-sync');
  }

  return response.json();
}

export async function resumeSourceSyncApi(id: number, tokenOverride?: string): Promise<WebsiteSource> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${id}/resume`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to resume auto-sync' }));
    throw new Error(errorData.detail || 'Failed to resume auto-sync');
  }

  return response.json();
}

export async function getSourceChangesApi(
  id: number,
  statusFilter?: string,
  tokenOverride?: string
): Promise<SyncChangeReview[]> {
  const url = new URL(`${API_BASE_URL}/api/admin/sources/${id}/changes`);
  if (statusFilter) {
    url.searchParams.append('status_filter', statusFilter);
  }

  const response = await fetch(url.toString(), {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to load change reviews' }));
    throw new Error(errorData.detail || 'Failed to load change reviews');
  }

  return response.json();
}

export async function approveChangeApi(
  sourceId: number,
  changeId: number,
  tokenOverride?: string
): Promise<SyncChangeReview> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${sourceId}/changes/${changeId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to approve change' }));
    throw new Error(errorData.detail || 'Failed to approve change');
  }

  return response.json();
}

export async function rejectChangeApi(
  sourceId: number,
  changeId: number,
  tokenOverride?: string
): Promise<SyncChangeReview> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${sourceId}/changes/${changeId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to reject change' }));
    throw new Error(errorData.detail || 'Failed to reject change');
  }

  return response.json();
}

export async function approveAllChangesApi(
  sourceId: number,
  tokenOverride?: string
): Promise<{ message: string; approved_count: number }> {
  const response = await fetch(`${API_BASE_URL}/api/admin/sources/${sourceId}/changes/approve-all`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to approve all changes' }));
    throw new Error(errorData.detail || 'Failed to approve all changes');
  }

  return response.json();
}
