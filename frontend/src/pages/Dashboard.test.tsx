import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Dashboard } from './Dashboard';
import * as authContext from '../context/AuthContext';
import type { User } from '../types/api';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: null, pathname: '/dashboard' }),
}));

vi.mock('../context/AuthContext', async () => {
  const actual = await vi.importActual<typeof authContext>('../context/AuthContext');
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

const studentUser: User = {
  id: 101,
  name: 'Sai Sumanth',
  email: 'sai@campusai.edu',
  role: 'STUDENT',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const adminUser: User = {
  id: 1,
  name: 'Administrator',
  email: 'admin@campusai.edu',
  role: 'ADMIN',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('Student Dashboard (Home Page)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  it('renders welcome header and main navigation elements for STUDENT', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    // Welcome heading
    expect(screen.getByTestId('dashboard-welcome')).toBeInTheDocument();
    expect(screen.getByText(/Welcome back, Sai/i)).toBeInTheDocument();
    expect(screen.getByText(/Your intelligent college information hub/i)).toBeInTheDocument();

    // Hero card
    expect(screen.getByTestId('hero-card')).toBeInTheDocument();
    expect(screen.getAllByText(/Ask CampusAI/i).length).toBeGreaterThan(0);

    // Student should NOT see staff banner
    expect(screen.queryByTestId('staff-banner')).not.toBeInTheDocument();
  });

  it('clicking Ask CampusAI button with empty search does not navigate', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const askBtn = screen.getByTestId('ask-campusai-btn');
    fireEvent.click(askBtn);

    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('submitting search navigates to /chat with initialMessage state', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const input = screen.getByPlaceholderText(/What are the rules for semester attendance/i);
    fireEvent.change(input, { target: { value: 'How do I check my grades?' } });
    
    const askBtn = screen.getByTestId('ask-campusai-btn');
    fireEvent.click(askBtn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat', {
        state: { initialMessage: 'How do I check my grades?' }
      });
    });
  });

  it('clicking a suggestion pill navigates to /chat', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const pillBtn = screen.getByText('Minimum attendance requirement');
    fireEvent.click(pillBtn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat', {
        state: { initialMessage: 'Minimum attendance requirement' }
      });
    });
  });

  it('renders admin sources link and banner for ADMIN role', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: adminUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    // Admin should see staff banner
    expect(screen.getByTestId('staff-banner')).toBeInTheDocument();
    expect(screen.getByText(/Staff Knowledge Management/i)).toBeInTheDocument();
    
    const manageBtn = screen.getByTestId('admin-manage-btn');
    fireEvent.click(manageBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/admin/sources');
  });
});
