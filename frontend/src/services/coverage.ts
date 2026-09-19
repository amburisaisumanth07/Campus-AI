export interface CoverageCategory {
  id: number;
  category: string;
  model: string;
  count: number;
  source_url: string;
  coverage_area: string;
}

export interface CoverageResponse {
  total_categories: number;
  covered_categories: number;
  coverage_percentage: number;
  total_records: number;
  categories: CoverageCategory[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(tokenOverride?: string): Record<string, string> {
  const token = tokenOverride || localStorage.getItem('campusai_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function getInstitutionalCoverageApi(tokenOverride?: string): Promise<CoverageResponse> {
  const response = await fetch(`${API_BASE_URL}/api/admin/coverage`, {
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(tokenOverride),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Failed to fetch coverage' }));
    throw new Error(errorData.detail || 'Failed to fetch institutional knowledge coverage');
  }

  return response.json();
}
