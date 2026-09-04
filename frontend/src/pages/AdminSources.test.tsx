import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AdminSources } from './AdminSources';
import * as sourcesService from '../services/sources';

vi.mock('../services/sources', () => ({
  listWebsiteSourcesApi: vi.fn(),
  createWebsiteSourceApi: vi.fn(),
  updateWebsiteSourceApi: vi.fn(),
  deleteWebsiteSourceApi: vi.fn(),
  triggerSyncApi: vi.fn(),
  getSyncHistoryApi: vi.fn(),
  getSourceStatusApi: vi.fn(),
  pauseSourceSyncApi: vi.fn(),
  resumeSourceSyncApi: vi.fn(),
  getSourceChangesApi: vi.fn(),
  approveChangeApi: vi.fn(),
  rejectChangeApi: vi.fn(),
  approveAllChangesApi: vi.fn(),
}));

describe('AdminSources Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(sourcesService.listWebsiteSourcesApi).mockResolvedValue([]);
    vi.mocked(sourcesService.getSyncHistoryApi).mockResolvedValue([]);
  });

  it('renders loading state and then lists configured website sources', async () => {
    const mockSources = [
      {
        id: 1,
        name: 'Official College Portal',
        base_url: 'https://college.edu',
        allowed_domains: 'college.edu',
        allowed_paths: '/academics',
        active: true,
        sync_interval: '6h',
        max_pages: 50,
        last_checked_at: '2026-08-22T10:00:00Z',
        last_successful_sync_at: '2026-08-22T10:00:00Z',
        status: 'ACTIVE' as const,
        created_by_id: 1,
        document_count: 12,
        created_at: '2026-08-20T10:00:00Z',
        updated_at: '2026-08-22T10:00:00Z',
      },
    ];

    vi.mocked(sourcesService.listWebsiteSourcesApi).mockResolvedValue(mockSources);

    render(<AdminSources />);

    expect(screen.getByText(/Loading configured website sources/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Official College Portal')).toBeInTheDocument();
    });

    expect(screen.getByText('https://college.edu')).toBeInTheDocument();
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(screen.getAllByText('12').length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty state when no sources are configured', async () => {
    vi.mocked(sourcesService.listWebsiteSourcesApi).mockResolvedValue([]);

    render(<AdminSources />);

    await waitFor(() => {
      expect(screen.getByText(/No Website Sources Configured/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Add the official MITS website URL/i)).toBeInTheDocument();
  });

  it('renders friendly error banner when API fails without crashing', async () => {
    vi.mocked(sourcesService.listWebsiteSourcesApi).mockRejectedValue(new Error('Network error. Unable to connect.'));

    render(<AdminSources />);

    await waitFor(() => {
      expect(screen.getByText(/Network error. Unable to connect./i)).toBeInTheDocument();
    });

    expect(screen.getByText(/No Website Sources Configured/i)).toBeInTheDocument();
  });

  it('allows opening Add Source modal and submitting', async () => {
    vi.mocked(sourcesService.listWebsiteSourcesApi).mockResolvedValue([]);
    vi.mocked(sourcesService.createWebsiteSourceApi).mockResolvedValue({
      id: 2,
      name: 'Engineering Portal',
      base_url: 'https://eng.college.edu',
      allowed_domains: 'eng.college.edu',
      active: true,
      sync_interval: '6h',
      max_pages: 50,
      status: 'IDLE' as const,
      created_by_id: 1,
      document_count: 0,
      created_at: '2026-08-22T12:00:00Z',
      updated_at: '2026-08-22T12:00:00Z',
    });

    render(<AdminSources />);

    await waitFor(() => {
      expect(screen.getByText(/No Website Sources Configured/i)).toBeInTheDocument();
    });

    // Click Add Source button
    const addBtns = screen.getAllByRole('button', { name: /Add Website Source|Configure First Source/i });
    fireEvent.click(addBtns[0]);

    expect(screen.getByLabelText(/Source Name \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Base URL/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Source Name \*/i), { target: { value: 'Engineering Portal' } });
    fireEvent.change(screen.getByLabelText(/Base URL/i), { target: { value: 'https://eng.college.edu' } });
    fireEvent.change(screen.getByLabelText(/Allowed Domains/i), { target: { value: 'eng.college.edu' } });

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /Create Source/i }));

    await waitFor(() => {
      expect(sourcesService.createWebsiteSourceApi).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Engineering Portal',
          base_url: 'https://eng.college.edu',
          allowed_domains: 'eng.college.edu',
        })
      );
    });
  });

  it('allows opening Sync History modal and viewing history records', async () => {
    const mockSources = [
      {
        id: 1,
        name: 'Main Portal',
        base_url: 'https://college.edu',
        allowed_domains: 'college.edu',
        active: true,
        sync_interval: '6h',
        max_pages: 50,
        status: 'ACTIVE' as const,
        created_by_id: 1,
        document_count: 5,
        created_at: '2026-08-20T10:00:00Z',
        updated_at: '2026-08-22T10:00:00Z',
      },
    ];

    const mockHistory = [
      {
        id: 101,
        source_id: 1,
        started_at: '2026-08-22T08:00:00Z',
        completed_at: '2026-08-22T08:02:00Z',
        status: 'SUCCESS' as const,
        documents_discovered: 10,
        documents_added: 3,
        documents_updated: 2,
        documents_unchanged: 5,
        documents_failed: 0,
        error_message: null,
      },
    ];

    vi.mocked(sourcesService.listWebsiteSourcesApi).mockResolvedValue(mockSources);
    vi.mocked(sourcesService.getSyncHistoryApi).mockResolvedValue(mockHistory);

    render(<AdminSources />);

    await waitFor(() => {
      expect(screen.getByText('Main Portal')).toBeInTheDocument();
    });

    // Click Sync History button
    fireEvent.click(screen.getByRole('button', { name: /Sync History/i }));

    await waitFor(() => {
      expect(screen.getByText(/Synchronization History — Main Portal/i)).toBeInTheDocument();
    });

    expect(screen.getByText('+3')).toBeInTheDocument();
    expect(screen.getByText('~2')).toBeInTheDocument();
    expect(screen.getByText('SUCCESS')).toBeInTheDocument();
  });
});
