import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GemsSyncModal } from './GemsSyncModal';
import * as api from '../../services/api';
import type { AttendanceResponse } from '../../types/api';

vi.mock('../../services/api', () => ({
  checkAttendanceApi: vi.fn(),
}));

const mockGemsSuccessResponse: AttendanceResponse = {
  student: 'Amburi Sai Sumanth',
  student_name: 'Amburi Sai Sumanth',
  roll_number: '24691A31N1',
  overall: 86.19,
  overall_percentage: 86.19,
  attended_classes: 73,
  total_classes: 82,
  absent_classes: 9,
  required: 75.0,
  required_percentage: 75.0,
  is_safe: true,
  status: 'Requirement satisfied',
  status_text: 'Attendance requirement currently satisfied.',
  subjects: [
    { code: '20CSE301', name: 'Database Management Systems', attended: 38, total: 42, percentage: 90.48 },
    { code: '20CSE302', name: 'Operating Systems', attended: 35, total: 40, percentage: 87.5 },
  ],
};

describe('GemsSyncModal Component', () => {
  const mockOnClose = vi.fn();
  const mockOnSyncSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('does not render when isOpen is false', () => {
    render(
      <GemsSyncModal
        isOpen={false}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
      />
    );
    expect(screen.queryByTestId('gems-sync-modal')).not.toBeInTheDocument();
  });

  it('renders modal with ephemeral login fields when isOpen is true', () => {
    render(
      <GemsSyncModal
        isOpen={true}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
        initialRollNumber="24691A31N1"
      />
    );

    expect(screen.getByTestId('gems-sync-modal')).toBeInTheDocument();
    expect(screen.getByText('Sync from MITS GEMS')).toBeInTheDocument();
    expect(screen.getByTestId('gems-roll-input')).toHaveValue('24691A31N1');
    expect(screen.getByTestId('gems-password-input')).toBeInTheDocument();
    expect(screen.getByTestId('gems-submit-sync-btn')).toBeInTheDocument();
  });

  it('CRITICAL SECURITY: password is never stored in localStorage or sessionStorage', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockResolvedValue(mockGemsSuccessResponse);

    render(
      <GemsSyncModal
        isOpen={true}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
        initialRollNumber="24691A31N1"
      />
    );

    const passInput = screen.getByTestId('gems-password-input');
    const secret = 'EphemeralPass999!';
    fireEvent.change(passInput, { target: { value: secret } });

    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(mockOnSyncSuccess).toHaveBeenCalled();
    });

    // Check storage
    expect(localStorage.getItem('password')).toBeNull();
    expect(sessionStorage.getItem('password')).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain(secret);
    expect(JSON.stringify(sessionStorage)).not.toContain(secret);
  });

  it('displays "Connecting to MITS GEMS..." transition during sync', async () => {
    let resolveFn: (val: AttendanceResponse) => void = () => {};
    const pendingPromise = new Promise<AttendanceResponse>((resolve) => {
      resolveFn = resolve;
    });
    vi.spyOn(api, 'checkAttendanceApi').mockReturnValue(pendingPromise);

    render(
      <GemsSyncModal
        isOpen={true}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
        initialRollNumber="24691A31N1"
      />
    );

    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'Secret123' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    expect(screen.getByText('Connecting to MITS GEMS...')).toBeInTheDocument();

    resolveFn(mockGemsSuccessResponse);
    await waitFor(() => {
      expect(mockOnSyncSuccess).toHaveBeenCalled();
    });
  });

  it('displays "Invalid MITS GEMS roll number or password." error when authentication fails', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockRejectedValue(new Error('Invalid MITS GEMS roll number or password.'));

    render(
      <GemsSyncModal
        isOpen={true}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
        initialRollNumber="24691A31N1"
      />
    );

    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'WrongPass' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('gems-sync-error')).toBeInTheDocument();
      expect(screen.getByText('Invalid MITS GEMS roll number or password.')).toBeInTheDocument();
    });

    // Ensure password was cleared immediately from the input
    expect(screen.getByTestId('gems-password-input')).toHaveValue('');
  });

  it('displays "Unable to connect to MITS GEMS right now. Please try again later." when server is down', async () => {
    vi.spyOn(api, 'checkAttendanceApi').mockRejectedValue(
      new Error('Unable to connect to MITS GEMS right now. Please try again later.')
    );

    render(
      <GemsSyncModal
        isOpen={true}
        onClose={mockOnClose}
        onSyncSuccess={mockOnSyncSuccess}
        initialRollNumber="24691A31N1"
      />
    );

    fireEvent.change(screen.getByTestId('gems-password-input'), { target: { value: 'SomePass' } });
    fireEvent.click(screen.getByTestId('gems-submit-sync-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('gems-sync-error')).toBeInTheDocument();
      expect(screen.getByText('Unable to connect to MITS GEMS right now. Please try again later.')).toBeInTheDocument();
    });
  });
});
