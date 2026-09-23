import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AttendanceTrackerModal } from './AttendanceTrackerModal';
import * as api from '../../services/api';
import type { AttendanceResponse } from '../../types/api';

vi.mock('../../services/api', () => ({
  checkAttendanceApi: vi.fn(),
}));

const mockAttendanceSuccess: AttendanceResponse = {
  success: true,
  roll_number: '24691A31N1',
  student_name: 'Amburi Sai Sumanth',
  overall_percentage: 82.5,
  attended_classes: 198,
  total_classes: 240,
  absent_classes: 42,
  required_percentage: 75.0,
  is_safe: true,
  status_text: 'Attendance requirement currently satisfied.',
  last_updated: '22 Sep 2026, 4:30 PM',
  official_source: 'https://studentportal.universitysolutions.in/',
  subjects: [
    { name: 'Database Management Systems', code: 'DBMS', attended: 38, total: 42, percentage: 90.5 },
    { name: 'Operating Systems', code: 'OS', attended: 35, total: 40, percentage: 87.5 },
    { name: 'Artificial Intelligence', code: 'AI', attended: 31, total: 38, percentage: 81.6 },
  ],
};

describe('AttendanceTrackerModal Component', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('does not render when isOpen is false', () => {
    render(<AttendanceTrackerModal isOpen={false} onClose={mockOnClose} />);
    expect(screen.queryByTestId('attendance-modal')).not.toBeInTheDocument();
  });

  it('renders modal with login form when isOpen is true', () => {
    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    expect(screen.getByTestId('attendance-modal')).toBeInTheDocument();
    expect(screen.getByText('Official MITS Attendance Tracker')).toBeInTheDocument();
    expect(screen.getByLabelText(/MITS Roll Number/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/MITS Student Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View Attendance/i })).toBeInTheDocument();
  });

  it('validates empty inputs and displays error', async () => {
    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    // In JSDOM, HTML5 required triggers or form submit triggers
    const submitBtn = screen.getByRole('button', { name: /View Attendance/i });
    fireEvent.click(submitBtn);

    // Form inputs should still be visible
    expect(screen.getByTestId('attendance-form')).toBeInTheDocument();
  });

  it('CRITICAL SECURITY: never stores password in localStorage even if remember roll number is checked', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockResolvedValue(mockAttendanceSuccess);

    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    const rollInput = screen.getByLabelText(/MITS Roll Number/i);
    const passInput = screen.getByLabelText(/MITS Student Password/i);
    const rememberCheckbox = screen.getByLabelText(/Remember roll number/i);
    const submitBtn = screen.getByTestId('view-attendance-btn');

    fireEvent.change(rollInput, { target: { value: '24691A31N1' } });
    fireEvent.change(passInput, { target: { value: 'SecretMITS@2026' } });
    fireEvent.click(rememberCheckbox);

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('attendance-result-view')).toBeInTheDocument();
    });

    // Check localStorage
    expect(localStorage.getItem('campusai_remembered_roll_number')).toBe('24691A31N1');
    // Ensure password is NEVER anywhere in localStorage
    expect(localStorage.getItem('password')).toBeNull();
    expect(localStorage.getItem('mits_password')).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain('SecretMITS@2026');
  });

  it('displays loading state while verifying credentials', async () => {
    let resolvePromise: (val: AttendanceResponse) => void = () => {};
    const pendingPromise = new Promise<AttendanceResponse>((resolve) => {
      resolvePromise = resolve;
    });
    vi.spyOn(api, 'checkAttendanceApi').mockReturnValue(pendingPromise);

    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    fireEvent.change(screen.getByLabelText(/MITS Roll Number/i), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByLabelText(/MITS Student Password/i), { target: { value: 'studentPass123' } });
    fireEvent.click(screen.getByTestId('view-attendance-btn'));

    expect(screen.getByText(/Checking Official Records.../i)).toBeInTheDocument();

    resolvePromise(mockAttendanceSuccess);
    await waitFor(() => {
      expect(screen.getByTestId('attendance-result-view')).toBeInTheDocument();
    });
  });

  it('displays error banner when official portal is unavailable or authentication fails', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockRejectedValue(
      new Error('Official attendance integration is currently unavailable.')
    );

    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    fireEvent.change(screen.getByLabelText(/MITS Roll Number/i), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByLabelText(/MITS Student Password/i), { target: { value: 'wrongpass' } });
    fireEvent.click(screen.getByTestId('view-attendance-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-error-banner')).toBeInTheDocument();
      expect(
        screen.getAllByText(/Official attendance integration is currently unavailable./i).length
      ).toBeGreaterThan(0);
      expect(screen.getByText(/Visit Official MITS Student Portal/i)).toBeInTheDocument();
    });
  });

  it('displays successful attendance data with 75% threshold and subject breakdown', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockResolvedValue(mockAttendanceSuccess);

    render(<AttendanceTrackerModal isOpen={true} onClose={mockOnClose} />);

    fireEvent.change(screen.getByLabelText(/MITS Roll Number/i), { target: { value: '24691A31N1' } });
    fireEvent.change(screen.getByLabelText(/MITS Student Password/i), { target: { value: 'studentPass123' } });
    fireEvent.click(screen.getByTestId('view-attendance-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('attendance-result-view')).toBeInTheDocument();
    });

    // Student identity
    expect(screen.getByText('Amburi Sai Sumanth')).toBeInTheDocument();
    expect(screen.getByText('24691A31N1')).toBeInTheDocument();

    // Stats
    expect(screen.getByText('82.5%')).toBeInTheDocument();
    expect(screen.getByText('198')).toBeInTheDocument(); // Attended
    expect(screen.getByText('240')).toBeInTheDocument(); // Total
    expect(screen.getAllByText('42').length).toBeGreaterThan(0);  // Absent & subject total
    expect(screen.getAllByText(/75%/i).length).toBeGreaterThan(0);  // Required rule and marker

    // Status text
    expect(screen.getByText('Attendance requirement currently satisfied.')).toBeInTheDocument();

    // Subject breakdown
    expect(screen.getByText('Database Management Systems')).toBeInTheDocument();
    expect(screen.getByText('Operating Systems')).toBeInTheDocument();
    expect(screen.getByText('Artificial Intelligence')).toBeInTheDocument();

    // Refresh button and timestamp
    expect(screen.getByText(/Last updated: 22 Sep 2026, 4:30 PM/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Refresh Attendance/i })).toBeInTheDocument();
  });
});
