import React, { useState, useEffect } from 'react';
import {
  X,
  Lock,
  User,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  ExternalLink,
  ShieldCheck,
  Loader2,
  CalendarCheck,
} from 'lucide-react';
import { checkAttendanceApi } from '../../services/api';
import type { AttendanceResponse } from '../../types/api';

interface AttendanceTrackerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const STORAGE_KEY_ROLL_NUMBER = 'campusai_remembered_roll_number';

export const AttendanceTrackerModal: React.FC<AttendanceTrackerModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [rollNumber, setRollNumber] = useState('');
  const [password, setPassword] = useState('');
  const [rememberRoll, setRememberRoll] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [attendanceData, setAttendanceData] = useState<AttendanceResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load remembered roll number (NEVER password!)
  useEffect(() => {
    try {
      const savedRoll = localStorage.getItem(STORAGE_KEY_ROLL_NUMBER);
      if (savedRoll) {
        setRollNumber(savedRoll);
        setRememberRoll(true);
      }
    } catch {
      // ignore
    }
  }, []);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rollNumber.trim() || !password.trim()) {
      setErrorMessage('Please enter both your MITS Roll Number and Student Password.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    // If remember roll number is checked, store ONLY the roll number
    try {
      if (rememberRoll) {
        localStorage.setItem(STORAGE_KEY_ROLL_NUMBER, rollNumber.trim().toUpperCase());
      } else {
        localStorage.removeItem(STORAGE_KEY_ROLL_NUMBER);
      }
    } catch {
      // ignore
    }

    try {
      const result = await checkAttendanceApi(rollNumber.trim().toUpperCase(), password);
      setAttendanceData(result);
      // SECURITY: Clear password immediately from memory state after successful fetch
      setPassword('');
    } catch (err: any) {
      setErrorMessage(err.message || 'Official attendance integration is currently unavailable.');
      // SECURITY: Clear password from memory on error as well
      setPassword('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!attendanceData) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      // Prompt student for password or refresh
      // Since password is never stored, if password is required we prompt
      const result = await checkAttendanceApi(attendanceData.roll_number, password || 'REFRESH');
      setAttendanceData(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Official attendance integration is currently unavailable.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearSession = () => {
    setAttendanceData(null);
    setPassword('');
    setErrorMessage(null);
  };

  return (
    <div className="attendance-modal-backdrop" onClick={onClose} data-testid="attendance-modal">
      <div
        className="attendance-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="attendance-modal-title"
      >
        {/* Modal Header */}
        <div className="attendance-modal-header">
          <div className="header-title-wrap">
            <div className="attendance-header-icon">
              <CalendarCheck size={22} />
            </div>
            <div>
              <h3 id="attendance-modal-title">Official MITS Attendance Tracker</h3>
              <p>Direct institutional attendance verification</p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="attendance-modal-body">
          {attendanceData ? (
            /* Results State */
            <div className="attendance-result-view" data-testid="attendance-result-view">
              <div className="student-profile-summary">
                <div className="student-info">
                  <span className="info-label">Student</span>
                  <h4>{attendanceData.student_name}</h4>
                  <span className="roll-badge">{attendanceData.roll_number}</span>
                </div>
                <div className="overall-pct-badge-wrap">
                  <div
                    className={`pct-circle ${
                      attendanceData.is_safe ? 'safe' : 'warning'
                    }`}
                  >
                    <span className="pct-number">{attendanceData.overall_percentage}%</span>
                    <span className="pct-label">Overall</span>
                  </div>
                </div>
              </div>

              {/* Progress Bar & Status */}
              <div className="attendance-progress-container">
                <div className="progress-bar-track">
                  <div
                    className={`progress-bar-fill ${
                      attendanceData.is_safe ? 'safe' : 'warning'
                    }`}
                    style={{ width: `${Math.min(100, attendanceData.overall_percentage)}%` }}
                  ></div>
                  {/* 75% Threshold Marker */}
                  <div
                    className="threshold-marker"
                    style={{ left: `${attendanceData.required_percentage}%` }}
                    title={`Required Minimum: ${attendanceData.required_percentage}%`}
                  >
                    <span className="marker-label">75% Req</span>
                  </div>
                </div>

                <div className="attendance-status-message">
                  {attendanceData.is_safe ? (
                    <div className="status-badge safe">
                      <CheckCircle2 size={16} />
                      <span>{attendanceData.status_text}</span>
                    </div>
                  ) : (
                    <div className="status-badge warning">
                      <AlertTriangle size={16} />
                      <span>{attendanceData.status_text}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="attendance-metrics-grid">
                <div className="metric-box">
                  <span className="metric-title">Attended Classes</span>
                  <span className="metric-val text-safe">{attendanceData.attended_classes}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-title">Total Classes</span>
                  <span className="metric-val">{attendanceData.total_classes}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-title">Absent</span>
                  <span className="metric-val text-danger">{attendanceData.absent_classes}</span>
                </div>
                <div className="metric-box">
                  <span className="metric-title">Required Rule</span>
                  <span className="metric-val">{attendanceData.required_percentage}%</span>
                </div>
              </div>

              {/* Subject Wise Table */}
              {attendanceData.subjects && attendanceData.subjects.length > 0 && (
                <div className="subject-attendance-section">
                  <h5>Subject-Wise Attendance</h5>
                  <div className="subject-table-wrapper">
                    <table className="subject-table">
                      <thead>
                        <tr>
                          <th>Subject</th>
                          <th>Attended</th>
                          <th>Total</th>
                          <th>Percentage</th>
                        </tr>
                      </thead>
                      <tbody>
                        {attendanceData.subjects.map((sub, idx) => (
                          <tr key={idx}>
                            <td>
                              <span className="sub-name">{sub.name}</span>
                              {sub.code && <span className="sub-code"> ({sub.code})</span>}
                            </td>
                            <td>{sub.attended}</td>
                            <td>{sub.total}</td>
                            <td>
                              <span
                                className={`sub-pct-tag ${
                                  sub.percentage >= 75 ? 'safe' : 'low'
                                }`}
                              >
                                {sub.percentage}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Timestamp & Refresh Controls */}
              <div className="attendance-footer-controls">
                <div className="timestamp-info">
                  <span>Last updated: {attendanceData.last_updated}</span>
                  <span className="official-source-tag">
                    Source: Official MITS Student System
                  </span>
                </div>
                <div className="action-btns">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={handleRefresh}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 size={15} className="spin" />
                    ) : (
                      <RotateCw size={15} />
                    )}
                    <span>Refresh Attendance</span>
                  </button>
                  <button
                    type="button"
                    className="text-btn clear-session-btn"
                    onClick={handleClearSession}
                  >
                    Clear Session
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Login & Credentials Input Form */
            <form onSubmit={handleSubmit} className="attendance-login-form" data-testid="attendance-form">
              <p className="form-intro-text">
                Enter your official MITS Student Information credentials to retrieve your verified attendance roster directly from the official portal.
              </p>

              {errorMessage && (
                <div className="attendance-error-banner" data-testid="attendance-error-banner">
                  <AlertTriangle size={18} className="error-icon" />
                  <div className="error-details">
                    <span className="error-title">Official attendance integration is currently unavailable.</span>
                    <p className="error-msg">{errorMessage}</p>
                    <a
                      href="https://studentportal.universitysolutions.in/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="portal-link"
                    >
                      Visit Official MITS Student Portal <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="roll-number-input">MITS Roll Number</label>
                <div className="input-with-icon">
                  <User size={18} className="input-icon" />
                  <input
                    id="roll-number-input"
                    type="text"
                    placeholder="e.g. 24691A31N1"
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value.toUpperCase())}
                    required
                    autoComplete="username"
                    maxLength={15}
                    className="attendance-text-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="password-input">MITS Student Password</label>
                <div className="input-with-icon">
                  <Lock size={18} className="input-icon" />
                  <input
                    id="password-input"
                    type="password"
                    placeholder="•••••••••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    className="attendance-text-input"
                  />
                </div>
              </div>

              <div className="remember-roll-row">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={rememberRoll}
                    onChange={(e) => setRememberRoll(e.target.checked)}
                  />
                  <span>Remember roll number</span>
                </label>
              </div>

              <div className="security-notice-card">
                <ShieldCheck size={18} className="shield-icon" />
                <span>
                  Your credentials are sent securely to the official MITS attendance system over HTTPS. Passwords are never stored in your browser or persisted in database records.
                </span>
              </div>

              <div className="form-submit-row">
                <button
                  type="submit"
                  className="primary-button view-attendance-btn"
                  disabled={isLoading}
                  data-testid="view-attendance-btn"
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={18} className="spin" />
                      <span>Checking Official Records...</span>
                    </>
                  ) : (
                    <span>View Attendance</span>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
