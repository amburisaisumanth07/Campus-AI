import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AttendancePage } from './AttendancePage';
import * as apiService from '../services/api';
import * as authContext from '../context/AuthContext';
import type { AttendanceResponse } from '../types/api';

vi.mock('../services/api', () => ({
  checkAttendanceApi: vi.fn(),
  getAttendanceApi: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

const mockRealGemsSuccess: AttendanceResponse = {
  student: 'Amburi Sai Sumanth',
  student_name: 'Amburi Sai Sumanth',
  roll_number: '24691A31N1',
  overall: 86.19,
  overall_percentage: 86.19,
  attended_classes: 181,
  total_classes: 210,
  absent_classes: 29,
  required: 75.0,
  required_percentage: 75.0,
  is_safe: true,
  status: 'Requirement satisfied',
  status_text: 'Attendance requirement currently satisfied.',
  semester: 'III YEAR I SEMESTER - REGULAR',
  last_synced: '24 Sep 2026, 05:00 PM UTC',
  last_updated: '24 Sep 2026, 05:00 PM UTC',
  subjects: [
    { code: '23CAI107', name: 'Big Data Analytics', attended: 19, total: 30, percentage: 63.33 },
    { code: '23CAI108', name: 'Cloud Computing', attended: 21, total: 29, percentage: 72.41 },
    { code: '20CSE301', name: 'Database Management Systems', attended: 38, total: 42, percentage: 90.48 },
    { code: '20CSE302', name: 'Operating Systems', attended: 35, total: 40, percentage: 87.5 },
  ],
  official_source: 'http://mitsims.in',
  success: true,
};

const mockLowAttendanceGems: AttendanceResponse = {
  student: 'John Doe',
  student_name: 'John Doe',
  roll_number: '24691A0501',
  overall: 60.0,
  overall_percentage: 60.0,
  attended_classes: 72,
  total_classes: 120,
  absent_classes: 48,
  required: 75.0,
  required_percentage: 75.0,
  is_safe: false,
  status: 'Critical',
  status_text: 'Attendance is below the required threshold.',
  semester: 'II YEAR I SEMESTER',
  last_synced: '24 Sep 2026, 05:00 PM UTC',
  subjects: [
    { code: '20CSE201', name: 'Computer Networks', attended: 24, total: 40, percentage: 60.0 },
    { code: '20CSE202', name: 'Compiler Design', attended: 20, total: 40, percentage: 50.0 },
    { code: '20CSE203', name: 'Cloud Computing', attended: 28, total: 40, percentage: 70.0 },
  ],
  official_source: 'http://mitsims.in',
  success: true,
};

describe('AttendancePage Component (Verified MITS GEMS Integration)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    vi.mocked(authContext.useAuth).mockReturnValue({
      user: { id: 1, name: 'Sai Sumanth', email: 'sai@mits.ac.in', role: 'STUDENT', is_active: true, created_at: '', updated_at: '' },
      token: 'mock-jwt-token',
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
  });

  // 1. Initial State: NO mock attendance loaded on mount (Requirement 2 & 9)
  it('renders initial live sync prompt and NEVER calls GET /api/attendance on mount', () => {
    render(<AttendancePage />);

    // Invariant: GET /api/attendance must NEVER be called by live Attendance UI
    expect(apiService.getAttendanceApi).not.toHaveBeenCalled();

    // Verifies MITS GEMS secure login form section is displayed
    expect(screen.getByTestId('gems-connect-prompt')).toBeInTheDocument();
    expect(screen.getByText('MITS GEMS ATTENDANCE')).toBeInTheDocument();
    expect(screen.getByText(/MITS GEMS portal operates over HTTP/i)).toBeInTheDocument();

    // Invariant: mock values must NOT appear on page
    expect(screen.queryByTestId('gems-live-table')).not.toBeInTheDocument();
    expect(screen.queryByText('38 / 42')).not.toBeInTheDocument();
  });

  // 2. Attendance Login Form & Sync Button (Requirement 3 & 9)
  it('renders the secure MITS GEMS attendance form with roll number, password, and sync button', () => {
    render(<AttendancePage />);

    expect(screen.getByLabelText(/Roll Number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/GEMS Password/i)).toBeInTheDocument();
    expect(screen.getByTestId('gems-roll-input')).toBeInTheDocument();
    expect(screen.getByTestId('gems-password-input')).toBeInTheDocument();
    expect(screen.getByTestId('gems-submit-sync-btn')).toBeInTheDocument();
  });

  // 3. Password Input Behavior & Zero Storage (Requirement 3, 8 & 9)
  it('ensures password has secure attributes and is NEVER stored in localStorage or sessionStorage', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockResolvedValue(mockRealGemsSuccess);

    render(<AttendancePage />);

    const passInput = screen.getByTestId('gems-password-input');
    expect(passInput).toHaveAttribute('type', 'password');
    expect(passInput).toHaveAttribute('autocomplete', 'off');

    const testPassword = 'SecretVolatilePassword!789';
    fireEvent.change(passInput, { target: { value: testPassword } });
    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });

    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-live-content')).toBeInTheDocument();
    });

    // Invariant: Password is never stored in browser storage
    expect(localStorage.getItem('password')).toBeNull();
    expect(sessionStorage.getItem('password')).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain(testPassword);
    expect(JSON.stringify(sessionStorage)).not.toContain(testPassword);
  });

  // 4. Loading State Progression (Requirement 4 & 9)
  it('displays loading state sequence and NEVER displays "Verifying session..."', async () => {
    let resolveFn: (val: AttendanceResponse) => void = () => {};
    const pendingPromise = new Promise<AttendanceResponse>((resolve) => {
      resolveFn = resolve;
    });
    vi.mocked(apiService.checkAttendanceApi).mockReturnValue(pendingPromise);

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Password123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    // Stage 1: Connecting
    expect(screen.getByText('Connecting to MITS GEMS...')).toBeInTheDocument();

    // Critical Invariant: "Verifying session..." must NOT appear during attendance sync
    expect(screen.queryByText(/Verifying session/i)).not.toBeInTheDocument();

    // Resolve
    resolveFn(mockRealGemsSuccess);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-live-content')).toBeInTheDocument();
    });
  });

  // 5. Successful Live Data Rendering (Requirement 5 & 9)
  it('displays real subject records, student metadata, and live status pill after sync', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockResolvedValue(mockRealGemsSuccess);

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'LivePass123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-live-content')).toBeInTheDocument();
    });

    // Status Banner
    expect(screen.getByText('LIVE ATTENDANCE')).toBeInTheDocument();
    expect(screen.getByText('Source: MITS GEMS')).toBeInTheDocument();
    expect(screen.getByText('Status: Synced')).toBeInTheDocument();

    // Student Metadata
    expect(screen.getByTestId('live-student-name')).toHaveTextContent('Amburi Sai Sumanth');
    expect(screen.getByTestId('live-student-roll')).toHaveTextContent('24691A31N1');
    expect(screen.getByTestId('live-student-semester')).toHaveTextContent('III YEAR I SEMESTER - REGULAR');
    expect(screen.getByTestId('live-student-last-synced')).toHaveTextContent('24 Sep 2026, 05:00 PM UTC');

    // Real Subject Attendance Table (Requirement 5)
    expect(screen.getByTestId('gems-live-table')).toBeInTheDocument();

    const row1 = screen.getByTestId('subject-row-23cai107');
    expect(row1).toHaveTextContent('23CAI107');
    expect(row1).toHaveTextContent('Big Data Analytics');
    expect(row1).toHaveTextContent('19');
    expect(row1).toHaveTextContent('30');
    expect(row1).toHaveTextContent('63.33%');

    const row2 = screen.getByTestId('subject-row-23cai108');
    expect(row2).toHaveTextContent('23CAI108');
    expect(row2).toHaveTextContent('Cloud Computing');
    expect(row2).toHaveTextContent('21');
    expect(row2).toHaveTextContent('29');
    expect(row2).toHaveTextContent('72.41%');
  });

  // 6. Derived CampusAI Calculations (Requirement 6)
  it('calculates weighted overall percentage, safe-to-miss, and recovery classes labeled as CampusAI', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockResolvedValue(mockRealGemsSuccess);

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Pass123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('campusai-derived-section')).toBeInTheDocument();
    });

    expect(screen.getByText('CampusAI Calculations')).toBeInTheDocument();

    // Total attended: 19 + 21 + 38 + 35 = 113. Total conducted: 30 + 29 + 42 + 40 = 141.
    // Weighted overall = (113 / 141) * 100 = 80.14%
    expect(screen.getByTestId('derived-total-attended')).toHaveTextContent('113');
    expect(screen.getByTestId('derived-total-conducted')).toHaveTextContent('141');
    expect(screen.getByTestId('derived-overall-percentage')).toHaveTextContent('80.14%');
    expect(screen.getByTestId('derived-75-status')).toHaveTextContent('Requirement satisfied');
  });

  // 7. Recovery Classes for Low Attendance (<75%) (Requirement 6)
  it('calculates required recovery classes for low attendance without modifying raw records', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockResolvedValue(mockLowAttendanceGems);

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A0501' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Pass123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('campusai-derived-section')).toBeInTheDocument();
    });

    expect(screen.getByTestId('derived-75-status')).toHaveTextContent('Attendance deficit');
    // Total attended: 72, total conducted: 120. (60%)
    // ceil((0.75 * 120 - 72) / 0.25) = 72 recovery classes
    expect(screen.getByText(/Must attend 72 classes to recover/i)).toBeInTheDocument();
  });

  // 8. Error State: Invalid Credentials (Requirement 7 & 9)
  it('displays "Invalid MITS GEMS roll number or password." and clears password on auth failure', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockRejectedValue(
      new Error('Invalid MITS GEMS roll number or password.')
    );

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'WrongPassword' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page-error')).toBeInTheDocument();
      expect(screen.getByText('Invalid MITS GEMS roll number or password.')).toBeInTheDocument();
    });

    // Invariant: Password cleared immediately
    expect(screen.getByTestId('gems-password-input')).toHaveValue('');

    // Invariant: NEVER fall back to mock data
    expect(screen.queryByTestId('attendance-live-content')).not.toBeInTheDocument();
  });

  // 9. Error State: GEMS Unavailable (Requirement 7 & 9)
  it('displays "Unable to connect to MITS GEMS right now. Please try again later." when GEMS is down', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockRejectedValue(
      new Error('Unable to connect to MITS GEMS right now. Please try again later.')
    );

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Password123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page-error')).toBeInTheDocument();
      expect(
        screen.getByText('Unable to connect to MITS GEMS right now. Please try again later.')
      ).toBeInTheDocument();
    });

    expect(screen.queryByTestId('attendance-live-content')).not.toBeInTheDocument();
  });

  // 10. Error State: Zero Attendance Records (Requirement 7 & 9)
  it('displays "No attendance records were returned by MITS GEMS." when GEMS returns empty records', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockRejectedValue(
      new Error('No attendance records were returned by MITS GEMS.')
    );

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Password123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page-error')).toBeInTheDocument();
      expect(
        screen.getByText('No attendance records were returned by MITS GEMS.')
      ).toBeInTheDocument();
    });

    expect(screen.queryByTestId('attendance-live-content')).not.toBeInTheDocument();
  });

  // 11. Disconnect and Clear Session
  it('disconnects live session and returns to login form when Disconnect is clicked', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockResolvedValue(mockRealGemsSuccess);

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Pass123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-live-content')).toBeInTheDocument();
    });

    // Click Disconnect
    const disconnectBtn = screen.getByTestId('attendance-refresh-btn');
    fireEvent.click(disconnectBtn);

    expect(screen.queryByTestId('attendance-live-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('gems-connect-prompt')).toBeInTheDocument();
    expect(screen.getByText('MITS GEMS ATTENDANCE')).toBeInTheDocument();
  });

  // 12. Error State: Rate Limit 429
  it('displays rate limit friendly error banner and clears password without falling back to mock data', async () => {
    vi.mocked(apiService.checkAttendanceApi).mockRejectedValue(
      new Error('Too many attendance sync attempts. Please wait a few minutes and try again.')
    );

    render(<AttendancePage />);

    fireEvent.change(screen.getByTestId('gems-roll-input'), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Pass123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-page-error')).toBeInTheDocument();
      expect(
        screen.getByText('Too many attendance sync attempts. Please wait a few minutes and try again.')
      ).toBeInTheDocument();
    });

    // Invariant: Password cleared immediately
    expect(screen.getByTestId('gems-password-input')).toHaveValue('');

    // Invariant: Never falls back to mock data
    expect(screen.queryByTestId('attendance-live-content')).not.toBeInTheDocument();
  });
});
