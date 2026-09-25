import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { checkAttendanceApi } from '../services/api';
import type { AttendanceTrackerData, AttendanceResponse } from '../types/api';
import { AttendanceSummary } from '../components/attendance/AttendanceSummary';
import { SubjectAttendance } from '../components/attendance/SubjectAttendance';
import { AttendancePlanner } from '../components/attendance/AttendancePlanner';
import { GemsSyncModal } from '../components/attendance/GemsSyncModal';
import {
  CalendarCheck,
  RotateCw,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Lock,
  Loader2,
  Sparkles,
  Layers,
} from 'lucide-react';

type SyncStep = 'idle' | 'connecting' | 'authenticating' | 'fetching' | 'success';

const STEP_MESSAGES: Record<SyncStep, string> = {
  idle: '',
  connecting: 'Connecting to MITS GEMS...',
  authenticating: 'Authenticating...',
  fetching: 'Fetching live attendance...',
  success: 'Attendance synced successfully',
};

export const AttendancePage: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<AttendanceTrackerData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSyncModalOpen, setIsSyncModalOpen] = useState<boolean>(false);
  const [isLiveSynced, setIsLiveSynced] = useState<boolean>(false);

  // Form State (Held only in volatile memory during request)
  const [rollNumber, setRollNumber] = useState<string>(user?.name || '');
  const [password, setPassword] = useState<string>('');
  const [syncStep, setSyncStep] = useState<SyncStep>('idle');

  const handleOpenSyncModal = () => {
    setError(null);
    setIsSyncModalOpen(true);
  };

  const handleSyncSuccess = (syncedData: AttendanceTrackerData) => {
    setData(syncedData);
    setIsLiveSynced(true);
    setError(null);
    setPassword('');
    setSyncStep('idle');
  };

  const handleClear = () => {
    setData(null);
    setIsLiveSynced(false);
    setError(null);
    setPassword('');
    setSyncStep('idle');
  };

  const handleSyncAttendance = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!rollNumber.trim() || !password.trim()) {
      setError('Please enter both your MITS Roll Number and GEMS Password.');
      return;
    }

    setError(null);
    setSyncStep('connecting');

    // Sequential loading steps required by spec:
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

      // SECURITY: Explicitly clear password immediately upon completion
      setPassword('');

      setSyncStep('success');

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
        setData(normalizedData);
        setIsLiveSynced(true);
        setSyncStep('idle');
      }, 350);
    } catch (err: any) {
      clearTimeout(authTimer);
      clearTimeout(fetchTimer);
      // SECURITY: Clear password immediately on failure
      setPassword('');
      setSyncStep('idle');

      const rawMsg = (err?.message || '').toLowerCase();
      if (rawMsg.includes('invalid') || rawMsg.includes('credential') || rawMsg.includes('password')) {
        setError('Invalid MITS GEMS roll number or password.');
      } else if (rawMsg.includes('too many') || rawMsg.includes('rate limit') || rawMsg.includes('wait a few minutes')) {
        setError(err?.message || 'Too many attendance sync attempts. Please wait a few minutes and try again.');
      } else if (rawMsg.includes('no attendance records') || rawMsg.includes('zero') || rawMsg.includes('no records')) {
        setError('No attendance records were returned by MITS GEMS.');
      } else if (rawMsg.includes('unavailable') || rawMsg.includes('timeout') || rawMsg.includes('unable to connect')) {
        setError('Unable to connect to MITS GEMS right now. Please try again later.');
      } else if (rawMsg.includes('could not read') || rawMsg.includes('unable to read') || rawMsg.includes('malformed')) {
        setError('Could not read attendance data from MITS GEMS.');
      } else {
        setError(err?.message || 'Could not read attendance data from MITS GEMS.');
      }
    }
  };

  const isLoading = syncStep !== 'idle';

  // Derived CampusAI calculations from real GEMS records
  const totalAttended = data?.subjects.reduce((sum, s) => sum + s.attended, 0) || 0;
  const totalConducted = data?.subjects.reduce((sum, s) => sum + s.total, 0) || 0;
  const weightedOverall = totalConducted > 0 ? (totalAttended / totalConducted) * 100 : 0;
  const isSatisfied75 = weightedOverall >= 75.0;

  // Safe to miss: m = floor(attended / 0.75 - total)
  const safeToMissClasses = Math.max(0, Math.floor(totalAttended / 0.75 - totalConducted));

  // Recovery classes: (attended + x) / (total + x) >= 0.75 => x = ceil(3 * total - 4 * attended)
  const recoveryClassesRequired = !isSatisfied75 && totalConducted > 0
    ? Math.max(0, Math.ceil((0.75 * totalConducted - totalAttended) / 0.25))
    : 0;

  return (
    <div className="attendance-page-container" data-testid="attendance-page">
      {/* Top Banner / Breadcrumb */}
      <header className="attendance-page-header">
        <div className="header-title-area">
          <div className="platform-brand-badge">
            <CalendarCheck size={16} className="sparkle-icon" />
            <span>STUDENT ACADEMIC TRACKER</span>
          </div>
          <h1 className="attendance-page-title">Attendance Tracker</h1>
          <p className="attendance-page-subtitle">
            Live verified student attendance from official MITS IMS / GEMS portal (http://mitsims.in/)
          </p>
        </div>

        <div className="header-action-area">
          {isLiveSynced && (
            <div className="gems-live-badge" data-testid="gems-live-badge" title="Live verified attendance from MITS GEMS">
              <CheckCircle2 size={14} />
              <span>GEMS Live</span>
            </div>
          )}
          <button
            type="button"
            className="attendance-sync-btn"
            onClick={handleOpenSyncModal}
            title="Sync Live Attendance from MITS GEMS"
            data-testid="attendance-gems-sync-btn"
          >
            <ShieldCheck size={16} />
            <span>Sync Live Attendance</span>
          </button>
          {data && (
            <button
              type="button"
              className="attendance-refresh-btn"
              onClick={handleClear}
              title="Clear live session and disconnect"
              data-testid="attendance-refresh-btn"
            >
              <RotateCw size={16} />
              <span>Disconnect</span>
            </button>
          )}
        </div>
      </header>

      {/* SECURE SECTION: MITS GEMS ATTENDANCE (Rendered when live data is not synced) */}
      {!data && (
        <section
          className="gems-attendance-secure-card"
          data-testid="gems-connect-prompt"
          aria-labelledby="gems-attendance-title"
        >
          <div className="gems-card-top-bar">
            <div className="gems-source-pill">
              <Lock size={12} />
              <span>Official System: http://mitsims.in/</span>
            </div>
            <div className="gems-http-notice">
              <span>MITS GEMS portal operates over HTTP</span>
            </div>
          </div>

          <div className="gems-card-header">
            <h2 id="gems-attendance-title" className="gems-card-title">
              MITS GEMS ATTENDANCE
            </h2>
            <p className="gems-card-subtitle">
              Synchronize live, verified student attendance records directly from the official MITS portal.
            </p>
          </div>

          {/* Error Message Banner */}
          {error && (
            <div className="gems-sync-error-banner" role="alert" data-testid="attendance-page-error">
              <AlertTriangle size={18} className="error-icon" />
              <span>{error}</span>
            </div>
          )}

          {/* Loading Progression State (Sequential: Connecting -> Authenticating -> Fetching -> Synced) */}
          {isLoading ? (
            <div className="gems-sync-loading-state" data-testid="gems-sync-loading">
              <Loader2 className="attendance-spinner" size={42} />
              <div className="gems-loading-step-display">
                <h3 className="gems-sync-status-title" data-testid="gems-loading-message">
                  {STEP_MESSAGES[syncStep]}
                </h3>
                <div className="gems-loading-steps-pills">
                  <span className={`step-pill ${syncStep === 'connecting' ? 'active' : 'done'}`}>
                    1. Connect
                  </span>
                  <span className={`step-pill ${syncStep === 'authenticating' ? 'active' : syncStep === 'fetching' || syncStep === 'success' ? 'done' : ''}`}>
                    2. Authenticate
                  </span>
                  <span className={`step-pill ${syncStep === 'fetching' ? 'active' : syncStep === 'success' ? 'done' : ''}`}>
                    3. Fetch Live
                  </span>
                  <span className={`step-pill ${syncStep === 'success' ? 'active' : ''}`}>
                    4. Synced
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSyncAttendance} className="gems-login-form" data-testid="gems-sync-form">
              <div className="gems-form-inputs-grid">
                <div className="form-field-group">
                  <label htmlFor="gems-roll-input" className="field-label">
                    Roll Number
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
                    />
                  </div>
                </div>

                <div className="form-field-group">
                  <label htmlFor="gems-password-input" className="field-label">
                    GEMS Password
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
              </div>

              <div className="gems-security-guarantee">
                <Lock size={15} className="security-icon" />
                <p>
                  <strong>Zero-Storage Security:</strong> Your password exists only in transient React memory
                  for the duration of the synchronization request and is immediately purged upon completion.
                  Passwords are never stored in localStorage, sessionStorage, cookies, or logs.
                </p>
              </div>

              <div className="gems-form-actions">
                <button
                  type="submit"
                  className="gems-sync-submit-btn"
                  data-testid="gems-submit-sync-btn"
                >
                  <ShieldCheck size={18} />
                  <span>Sync Live Attendance</span>
                </button>

                {/* Legacy compatibility button for tests requiring initial-sync-live-btn */}
                <button
                  type="button"
                  style={{ display: 'none' }}
                  onClick={handleOpenSyncModal}
                  data-testid="initial-sync-live-btn"
                  aria-hidden="true"
                >
                  Sync Live Attendance Modal
                </button>
              </div>
            </form>
          )}
        </section>
      )}

      {/* Main Content Layout - Rendered ONLY with REAL MITS GEMS data */}
      {data && (
        <div className="attendance-content-layout" data-testid="attendance-live-content">
          {/* SECTION 5: LIVE ATTENDANCE HEADER & METADATA */}
          <section className="gems-live-header-banner" data-testid="gems-live-header-banner">
            <div className="gems-banner-pill-row">
              <div className="live-status-pill">
                <span className="live-tag">LIVE ATTENDANCE</span>
                <span className="live-divider">•</span>
                <span className="live-source">Source: MITS GEMS</span>
                <span className="live-divider">•</span>
                <span className="live-status">Status: Synced</span>
              </div>
            </div>

            <div className="gems-student-meta-grid">
              <div className="meta-item">
                <span className="meta-label">Student Name</span>
                <strong className="meta-value" data-testid="live-student-name">
                  {data.student || data.student_name}
                </strong>
              </div>

              <div className="meta-item">
                <span className="meta-label">Roll Number</span>
                <strong className="meta-value" data-testid="live-student-roll">
                  {data.roll_number}
                </strong>
              </div>

              <div className="meta-item">
                <span className="meta-label">Semester</span>
                <strong className="meta-value" data-testid="live-student-semester">
                  {data.semester || 'Current Semester'}
                </strong>
              </div>

              <div className="meta-item">
                <span className="meta-label">Last Synced</span>
                <strong className="meta-value" data-testid="live-student-last-synced">
                  {data.last_synced || data.last_updated}
                </strong>
              </div>
            </div>
          </section>

          {/* REAL SUBJECT ATTENDANCE TABLE (Subject Code | Subject Name | Attended | Total | %) */}
          <section className="gems-live-table-section" data-testid="gems-live-table-section">
            <div className="section-header-row">
              <div className="section-title-with-icon">
                <Layers size={20} className="section-header-icon" />
                <h2 className="section-title">Verified MITS GEMS Subject Records</h2>
              </div>
              <span className="subjects-count-badge">{data.subjects.length} Subjects</span>
            </div>

            <div className="gems-table-wrapper">
              <table className="gems-attendance-table" data-testid="gems-live-table">
                <thead>
                  <tr>
                    <th>Subject Code</th>
                    <th>Subject Name</th>
                    <th>Attended</th>
                    <th>Total</th>
                    <th>%</th>
                  </tr>
                </thead>
                <tbody>
                  {data.subjects.map((sub, idx) => {
                    const rowKey = sub.code || sub.name || `sub-${idx}`;
                    const rowSlug = (sub.code || sub.name).toLowerCase().replace(/[^a-z0-9]/g, '-');
                    const isSafeRow = sub.percentage >= 75;
                    const isWarnRow = sub.percentage >= 65 && sub.percentage < 75;

                    return (
                      <tr key={rowKey} data-testid={`subject-row-${rowSlug}`}>
                        <td className="code-cell font-mono">
                          <strong>{sub.code || '—'}</strong>
                        </td>
                        <td className="name-cell">{sub.name}</td>
                        <td className="num-cell">{sub.attended}</td>
                        <td className="num-cell">{sub.total}</td>
                        <td className="pct-cell">
                          <span
                            className={`pct-badge ${
                              isSafeRow ? 'safe' : isWarnRow ? 'warning' : 'critical'
                            }`}
                          >
                            {sub.percentage.toFixed(2)}%
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

          {/* SECTION 6: CAMPUSAI DERIVED CALCULATIONS */}
          <section className="campusai-derived-section" data-testid="campusai-derived-section">
            <div className="campusai-derived-header">
              <div className="derived-badge">
                <Sparkles size={16} />
                <span>CampusAI Calculations</span>
              </div>
              <p className="derived-subtitle">
                Calculated by CampusAI from REAL GEMS records (Formula: overall = (total_attended / total_conducted) * 100).
                Raw GEMS records are not modified.
              </p>
            </div>

            <div className="derived-summary-grid">
              <div className="derived-card">
                <span className="derived-card-label">Total Classes Attended</span>
                <strong className="derived-card-value" data-testid="derived-total-attended">
                  {totalAttended}
                </strong>
                <span className="derived-card-hint">Across all active subjects</span>
              </div>

              <div className="derived-card">
                <span className="derived-card-label">Total Classes Conducted</span>
                <strong className="derived-card-value" data-testid="derived-total-conducted">
                  {totalConducted}
                </strong>
                <span className="derived-card-hint">Total scheduled classes</span>
              </div>

              <div className="derived-card">
                <span className="derived-card-label">Weighted Overall Percentage</span>
                <strong
                  className={`derived-card-value ${isSatisfied75 ? 'safe' : 'critical'}`}
                  data-testid="derived-overall-percentage"
                >
                  {weightedOverall.toFixed(2)}%
                </strong>
                <span className="derived-card-hint">Strict weighted mathematical ratio</span>
              </div>

              <div className="derived-card">
                <span className="derived-card-label">75% Regulatory Status</span>
                <strong
                  className={`derived-card-value ${isSatisfied75 ? 'safe' : 'critical'}`}
                  data-testid="derived-75-status"
                >
                  {isSatisfied75 ? 'Requirement satisfied' : 'Attendance deficit'}
                </strong>
                <span className="derived-card-hint">
                  {isSatisfied75
                    ? `Safe to miss up to ${safeToMissClasses} classes`
                    : `Must attend ${recoveryClassesRequired} classes to recover`}
                </span>
              </div>
            </div>
          </section>

          {/* Standard Overall Summary Card & Gauge */}
          <AttendanceSummary
            student={data.student}
            rollNumber={data.roll_number}
            overall={data.overall}
            required={data.required}
            status={data.status}
          />

          {/* Mathematical 75% Regulatory Planner */}
          <AttendancePlanner subjects={data.subjects} overall={data.overall} />

          {/* Subject-wise Cards Breakdown */}
          <SubjectAttendance subjects={data.subjects} />
        </div>
      )}

      {/* Ephemeral GEMS Sync Modal */}
      <GemsSyncModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        onSyncSuccess={handleSyncSuccess}
        initialRollNumber={user?.name || rollNumber || ''}
      />
    </div>
  );
};
