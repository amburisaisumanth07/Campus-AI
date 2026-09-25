import React, { useState, useEffect } from 'react';
import { X, Lock, ShieldCheck, Loader2, AlertTriangle } from 'lucide-react';
import { checkAttendanceApi } from '../../services/api';
import type { AttendanceTrackerData, AttendanceResponse } from '../../types/api';

interface GemsSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSyncSuccess: (data: AttendanceTrackerData) => void;
  initialRollNumber?: string;
}

export const GemsSyncModal: React.FC<GemsSyncModalProps> = ({
  isOpen,
  onClose,
  onSyncSuccess,
  initialRollNumber = '',
}) => {
  const [rollNumber, setRollNumber] = useState(initialRollNumber);
  const [password, setPassword] = useState('');
  const [syncStep, setSyncStep] = useState<
    'idle' | 'connecting' | 'authenticating' | 'fetching' | 'success'
  >('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialRollNumber && !rollNumber) {
      setRollNumber(initialRollNumber);
    }
  }, [initialRollNumber]);

  if (!isOpen) return null;

  const handleClose = () => {
    // SECURITY: Clear password immediately from memory when modal closes
    setPassword('');
    setErrorMessage(null);
    setSyncStep('idle');
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rollNumber.trim() || !password.trim()) {
      setErrorMessage('Please enter both your MITS Roll Number and GEMS Password.');
      return;
    }

    setErrorMessage(null);
    setSyncStep('connecting');

    // Sequential loading steps:
    // 1. "Connecting to MITS GEMS..." -> 2. "Authenticating..." -> 3. "Fetching live attendance..."
    const authTimer = setTimeout(() => {
      setSyncStep('authenticating');
    }, 250);

    const fetchTimer = setTimeout(() => {
      setSyncStep('fetching');
    }, 500);

    try {
      const response: AttendanceResponse = await checkAttendanceApi(
        rollNumber.trim().toUpperCase(),
        password
      );
      clearTimeout(authTimer);
      clearTimeout(fetchTimer);

      // SECURITY: Explicitly clear password from state immediately
      setPassword('');

      setSyncStep('success');

      // Normalize into standard AttendanceTrackerData
      const normalizedData: AttendanceTrackerData = {
        student: response.student || response.student_name || 'MITS Student',
        roll_number: response.roll_number || rollNumber.trim().toUpperCase(),
        overall: response.overall ?? response.overall_percentage ?? 0,
        required: response.required ?? response.required_percentage ?? 75,
        status: response.status || response.status_text || 'Requirement satisfied',
        subjects: (response.subjects || []).map((s) => ({
          name: s.name,
          code: s.code,
          attended: s.attended,
          total: s.total,
          percentage: s.percentage,
        })),
        semester: response.semester,
        academic_year: response.academic_year,
        last_synced: response.last_synced || response.last_updated || new Date().toLocaleString(),
        last_updated: response.last_updated || new Date().toLocaleString(),
        attended_classes: response.attended_classes,
        total_classes: response.total_classes,
        absent_classes: response.absent_classes,
        is_safe: response.is_safe,
        status_text: response.status_text,
        official_source: response.official_source || 'http://mitsims.in',
        success: true,
      };

      setTimeout(() => {
        setSyncStep('idle');
        onSyncSuccess(normalizedData);
        handleClose();
      }, 350);
    } catch (err: any) {
      clearTimeout(authTimer);
      clearTimeout(fetchTimer);
      // SECURITY: Clear password immediately on failure
      setPassword('');
      setSyncStep('idle');

      const rawMsg = (err?.message || '').toLowerCase();
      if (rawMsg.includes('invalid') || rawMsg.includes('credential') || rawMsg.includes('password')) {
        setErrorMessage('Invalid MITS GEMS roll number or password.');
      } else if (rawMsg.includes('too many') || rawMsg.includes('rate limit') || rawMsg.includes('wait a few minutes')) {
        setErrorMessage(err?.message || 'Too many attendance sync attempts. Please wait a few minutes and try again.');
      } else if (rawMsg.includes('no attendance records') || rawMsg.includes('zero') || rawMsg.includes('no records')) {
        setErrorMessage('No attendance records were returned by MITS GEMS.');
      } else if (rawMsg.includes('unavailable') || rawMsg.includes('timeout') || rawMsg.includes('unable to connect')) {
        setErrorMessage('Unable to connect to MITS GEMS right now. Please try again later.');
      } else if (rawMsg.includes('could not read') || rawMsg.includes('unable to read') || rawMsg.includes('malformed')) {
        setErrorMessage('Could not read attendance data from MITS GEMS.');
      } else {
        setErrorMessage(err?.message || 'Could not read attendance data from MITS GEMS.');
      }
    }
  };

  const isLoading = syncStep !== 'idle';

  return (
    <div
      className="attendance-modal-backdrop"
      onClick={handleClose}
      data-testid="gems-sync-modal"
    >
      <div
        className="attendance-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gems-sync-modal-title"
      >
        {/* Header */}
        <div className="attendance-modal-header">
          <div className="header-title-wrap">
            <div className="attendance-header-icon">
              <ShieldCheck size={22} />
            </div>
            <div>
              <h3 id="gems-sync-modal-title">Sync from MITS GEMS</h3>
              <p>Direct live student attendance verification</p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={handleClose}
            disabled={isLoading}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="attendance-modal-body">
          {isLoading ? (
            <div className="gems-sync-loading-state" data-testid="gems-sync-loading">
              <Loader2 className="attendance-spinner" size={38} />
              {syncStep === 'connecting' && (
                <div data-testid="gems-sync-connecting">
                  <h4 className="gems-sync-status-title">Connecting to MITS GEMS...</h4>
                  <p className="gems-sync-status-sub">Establishing isolated in-memory session</p>
                </div>
              )}
              {syncStep === 'authenticating' && (
                <div data-testid="gems-sync-authenticating">
                  <h4 className="gems-sync-status-title">Authenticating...</h4>
                  <p className="gems-sync-status-sub">Verifying student credentials with MITS portal</p>
                </div>
              )}
              {syncStep === 'fetching' && (
                <div data-testid="gems-sync-fetching">
                  <h4 className="gems-sync-status-title">Fetching live attendance...</h4>
                  <p className="gems-sync-status-sub">Extracting and validating verified subject tables</p>
                </div>
              )}
              {syncStep === 'success' && (
                <div data-testid="gems-sync-success">
                  <h4 className="gems-sync-status-title">Attendance synced successfully</h4>
                  <p className="gems-sync-status-sub">Live records received from MITS GEMS</p>
                </div>
              )}
            </div>
          ) : (
            <form onSubmit={handleSubmit} data-testid="gems-sync-form" className="gems-sync-form">
              {errorMessage && (
                <div className="gems-sync-error-banner" data-testid="gems-sync-error" role="alert">
                  <AlertTriangle size={18} className="error-icon" />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div className="form-field-group">
                <label htmlFor="gems-roll-input" className="field-label">
                  MITS Roll Number
                </label>
                <div className="input-wrap">
                  <input
                    id="gems-roll-input"
                    data-testid="gems-roll-input"
                    type="text"
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value.toUpperCase())}
                    placeholder="e.g. 24691A31N1"
                    maxLength={20}
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div className="form-field-group">
                <label htmlFor="gems-password-input" className="field-label">
                  GEMS Student Password
                </label>
                <div className="input-wrap">
                  <input
                    id="gems-password-input"
                    data-testid="gems-password-input"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your GEMS password"
                    autoComplete="off"
                    required
                  />
                </div>
              </div>

              <div className="security-notice-card">
                <Lock size={15} className="security-icon" />
                <p>
                  <strong>Volatile Security:</strong> Your password exists only in volatile memory for the
                  request duration and is never saved, logged, or stored.
                </p>
              </div>

              <div className="modal-actions-wrap">
                <button
                  type="button"
                  className="modal-cancel-btn"
                  onClick={handleClose}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-submit-btn"
                  data-testid="gems-submit-sync-btn"
                >
                  Sync Live Attendance
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
