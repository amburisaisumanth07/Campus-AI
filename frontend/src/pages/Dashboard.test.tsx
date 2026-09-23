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

describe('Redesigned CampusAI Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
  });

  it('renders modern redesigned dashboard: CampusAI, subtitle, user greeting, and input', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    // Welcome & Brand
    expect(screen.getByTestId('dashboard-welcome')).toBeInTheDocument();
    expect(screen.getByText('CampusAI')).toBeInTheDocument();
    expect(screen.getByText('College Knowledge Assistant')).toBeInTheDocument();
    expect(screen.getByText(/Welcome back,/i)).toBeInTheDocument();

    // Ask CampusAI Search input & button
    expect(screen.getByTestId('ask-campusai-input')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ask CampusAI anything...')).toBeInTheDocument();
    expect(screen.getByTestId('ask-campusai-btn')).toBeInTheDocument();

    // Two featured action cards
    expect(screen.getByTestId('ask-with-voice-card')).toBeInTheDocument();
    expect(screen.getByTestId('attendance-tracker-card')).toBeInTheDocument();

    // Student should NOT see staff banner
    expect(screen.queryByTestId('staff-banner')).not.toBeInTheDocument();
  });

  it('CRITICAL: four legacy institutional cards are completely removed', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    // PART 1 Requirement: Ensure the four old cards are NOT in the document
    expect(screen.queryByText(/Academic & Grading Rules/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Departments & Faculty/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Examination Policies/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Placement & Career Cell/i)).not.toBeInTheDocument();
  });

  it('renders microphone button directly inside or beside search input', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const micBtn = screen.getByRole('button', { name: /voice input/i });
    expect(micBtn).toBeInTheDocument();
  });

  it('clicking Ask button with empty input does not navigate', async () => {
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

  it('typing a question and submitting navigates to /chat with initialMessage state', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const input = screen.getByTestId('ask-campusai-input');
    fireEvent.change(input, { target: { value: 'Who is the current HOD of CSE?' } });

    const askBtn = screen.getByTestId('ask-campusai-btn');
    fireEvent.click(askBtn);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat', {
        state: { initialMessage: 'Who is the current HOD of CSE?' },
      });
    });
  });

  it('renders official example query pills and clicking one navigates to /chat', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const hodPill = screen.getByText('"Who is the current HOD of CSE?"');
    expect(hodPill).toBeInTheDocument();
    expect(screen.getByText('"What is the minimum attendance requirement?"')).toBeInTheDocument();
    expect(screen.getByText('"When are the semester examinations?"')).toBeInTheDocument();
    expect(screen.getByText('"Show me the CSE faculty."')).toBeInTheDocument();

    fireEvent.click(hodPill);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/chat', {
        state: { initialMessage: 'Who is the current HOD of CSE?' },
      });
    });
  });

  it('clicking Attendance Tracker opens the official attendance modal', async () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    // Attendance modal should initially be closed
    expect(screen.queryByTestId('attendance-modal')).not.toBeInTheDocument();

    const attendanceCard = screen.getByTestId('attendance-tracker-card');
    fireEvent.click(attendanceCard);

    // Modal should now be open
    await waitFor(() => {
      expect(screen.getByTestId('attendance-modal')).toBeInTheDocument();
      expect(screen.getByText('Official MITS Attendance Tracker')).toBeInTheDocument();
      expect(screen.getByText('MITS Roll Number')).toBeInTheDocument();
      expect(screen.getByText('MITS Student Password')).toBeInTheDocument();
    });
  });

  it('renders staff knowledge management banner for ADMIN role', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: adminUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    expect(screen.getByTestId('staff-banner')).toBeInTheDocument();
    expect(screen.getByText(/Staff Knowledge Management/i)).toBeInTheDocument();

    const manageBtn = screen.getByTestId('admin-manage-btn');
    fireEvent.click(manageBtn);
    expect(mockNavigate).toHaveBeenCalledWith('/admin/sources');
  });

  it('renders responsive layout structure: modern clean container and featured action grid', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: studentUser,
      token: 'mock-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(<Dashboard />);

    const dashboard = screen.getByTestId('student-dashboard');
    expect(dashboard).toHaveClass('modern-clean-dashboard');

    const featuredGrid = screen.getByTestId('dashboard-featured-actions');
    expect(featuredGrid).toHaveClass('dashboard-featured-actions-grid');

    const voiceCard = screen.getByTestId('ask-with-voice-card');
    const attendanceCard = screen.getByTestId('attendance-tracker-card');
    expect(featuredGrid).toContainElement(voiceCard);
    expect(featuredGrid).toContainElement(attendanceCard);
  });
});

