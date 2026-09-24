import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AttendancePage } from './AttendancePage';
import * as apiService from '../services/api';
import * as authContext from '../context/AuthContext';
import type { AttendanceTrackerData } from '../types/api';

vi.mock('../services/api', () => ({
  getAttendanceApi: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockMockData: AttendanceTrackerData = {
  student: 'Sai Sumanth',
  roll_number: '24691A31N1',
  overall: 86.19,
  required: 75,
  status: 'Requirement satisfied',
  subjects: [
    { name: 'DBMS', attended: 38, total: 42, percentage: 90.48 },
    { name: 'Operating Systems', attended: 35, total: 40, percentage: 87.5 },
    { name: 'Artificial Intelligence', attended: 31, total: 38, percentage: 81.58 },
    { name: 'Java', attended: 45, total: 50, percentage: 90.0 },
    { name: 'Mathematics', attended: 32, total: 40, percentage: 80.0 },
  ],
};

const mockLowAttendanceData: AttendanceTrackerData = {
  student: 'John Doe',
  roll_number: '24691A0501',
  overall: 60.0,
  required: 75,
  status: 'Critical',
  subjects: [
    { name: 'Computer Networks', attended: 24, total: 40, percentage: 60.0 },
    { name: 'Compiler Design', attended: 20, total: 40, percentage: 50.0 },
    { name: 'Cloud Computing', attended: 28, total: 40, percentage: 70.0 },
  ],
};

const mockExact75AttendanceData: AttendanceTrackerData = {
  student: 'Jane Smith',
  roll_number: '24691A0502',
  overall: 75.0,
  required: 75,
  status: 'Requirement satisfied',
  subjects: [
    { name: 'Software Engineering', attended: 30, total: 40, percentage: 75.0 },
  ],
};

describe('AttendancePage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authContext.useAuth).mockReturnValue({
      user: { id: 1, name: 'Sai Sumanth', email: 'sai@mits.ac.in', role: 'STUDENT', is_active: true, created_at: '', updated_at: '' },
      token: 'mock-jwt-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
  });

  // 1 & 2. Loading state
  it('renders independent loading state with "AI/Attendance data loading..." and not "Verifying session..."', () => {
    vi.mocked(apiService.getAttendanceApi).mockReturnValue(new Promise(() => {})); // Never resolves

    render(<AttendancePage />);

    expect(screen.getByTestId('attendance-page-loading')).toBeInTheDocument();
    expect(screen.getByText('AI/Attendance data loading...')).toBeInTheDocument();
    expect(screen.queryByText(/Verifying session/i)).not.toBeInTheDocument();
  });

  // 3 & 4. Error state & Retry
  it('renders clean error state when API fails and re-fetches when Retry button is clicked', async () => {
    vi.mocked(apiService.getAttendanceApi)
      .mockRejectedValueOnce(new Error('Network error. Unable to connect.'))
      .mockResolvedValueOnce(mockMockData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page-error')).toBeInTheDocument();
    });

    expect(screen.getByText('Unable to load attendance')).toBeInTheDocument();
    expect(screen.getByText('Network error. Unable to connect.')).toBeInTheDocument();

    const retryBtn = screen.getByTestId('attendance-retry-btn');
    expect(retryBtn).toBeInTheDocument();

    // Click retry
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page')).toBeInTheDocument();
      expect(screen.getByTestId('student-name')).toHaveTextContent('Sai Sumanth');
    });

    expect(apiService.getAttendanceApi).toHaveBeenCalledTimes(2);
  });

  // 5. Overall attendance renders
  it('renders overall attendance summary card with student identity and percentages', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockMockData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page')).toBeInTheDocument();
    });

    expect(screen.getByTestId('student-name')).toHaveTextContent('Sai Sumanth');
    expect(screen.getByTestId('student-roll')).toHaveTextContent('24691A31N1');
    expect(screen.getByTestId('overall-attendance-value')).toHaveTextContent('86.19%');
    expect(screen.getByTestId('required-attendance-value')).toHaveTextContent('75%');
    expect(screen.getByTestId('overall-status-badge')).toHaveTextContent('Requirement satisfied');
  });

  // 6. All subjects render via .map()
  it('renders all subject cards using map iteration', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockMockData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('subjects-grid')).toBeInTheDocument();
    });

    expect(screen.getByTestId('subject-card-dbms')).toBeInTheDocument();
    expect(screen.getByTestId('subject-card-operating-systems')).toBeInTheDocument();
    expect(screen.getByTestId('subject-card-artificial-intelligence')).toBeInTheDocument();
    expect(screen.getByTestId('subject-card-java')).toBeInTheDocument();
    expect(screen.getByTestId('subject-card-mathematics')).toBeInTheDocument();

    const dbmsCard = screen.getByTestId('subject-card-dbms');
    expect(dbmsCard).toHaveTextContent('38 / 42');
    expect(dbmsCard).toHaveTextContent('90.48%');
  });

  // 7. Subject status dynamic categories
  it('dynamically renders correct status tags: Safe (>=75%), Conditionally eligible (65-74.99%), Critical (<65%)', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockLowAttendanceData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('subjects-grid')).toBeInTheDocument();
    });

    // Cloud Computing: 70% -> Conditionally eligible
    const ccCard = screen.getByTestId('subject-card-cloud-computing');
    expect(ccCard).toHaveTextContent('Conditionally eligible');

    // Computer Networks: 60% -> Critical
    const cnCard = screen.getByTestId('subject-card-computer-networks');
    expect(cnCard).toHaveTextContent('Critical');

    // Compiler Design: 50% -> Critical
    const cdCard = screen.getByTestId('subject-card-compiler-design');
    expect(cdCard).toHaveTextContent('Critical');
  });

  // 8. Attendance Planner calculation displays correctly (above 75%)
  it('displays accurate attendance planner calculation for safe status', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockMockData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-planner-section')).toBeInTheDocument();
    });

    // Total attended: 181, Total classes: 210
    // floor((18100 - 75 * 210) / 75) = 31 classes can be missed!
    expect(screen.getByTestId('planner-safe-card')).toBeInTheDocument();
    expect(screen.getByTestId('bunkable-classes-count')).toHaveTextContent('31');
    expect(screen.queryByTestId('planner-critical-card')).not.toBeInTheDocument();
  });

  // 9. Attendance Planner calculation for below 75%
  it('displays consecutive classes required to reach 75% when attendance is below threshold', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockLowAttendanceData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-planner-section')).toBeInTheDocument();
    });

    // Total attended = 24 + 20 + 28 = 72. Total classes = 120 (60.0%).
    // ceil((75 * 120 - 100 * 72) / 25) = (9000 - 7200) / 25 = 1800 / 25 = 72 consecutive classes required.
    expect(screen.getByTestId('planner-critical-card')).toBeInTheDocument();
    expect(screen.getByTestId('required-classes-count')).toHaveTextContent('72');
    expect(screen.queryByTestId('planner-safe-card')).not.toBeInTheDocument();
  });

  // 10. Edge case: exactly 75%
  it('handles edge case of exactly 75% attendance without misleading messages', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockExact75AttendanceData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-planner-section')).toBeInTheDocument();
    });

    expect(screen.getByTestId('planner-exact-card')).toBeInTheDocument();
    expect(screen.getByTestId('planner-exact-message')).toHaveTextContent('exactly 75%');
    expect(screen.queryByTestId('planner-critical-card')).not.toBeInTheDocument();
  });

  // 11. Responsive layout container
  it('renders responsive structure without horizontal overflow containers', async () => {
    vi.mocked(apiService.getAttendanceApi).mockResolvedValue(mockMockData);

    render(<AttendancePage />);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page')).toBeInTheDocument();
    });

    const pageContainer = screen.getByTestId('attendance-page');
    expect(pageContainer).toHaveClass('attendance-page-container');
    expect(screen.getByTestId('attendance-refresh-btn')).toBeInTheDocument();
  });
});
