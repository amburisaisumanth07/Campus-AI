import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { getAttendanceApi } from '../services/api';
import type { AttendanceTrackerData } from '../types/api';
import { AttendanceSummary } from '../components/attendance/AttendanceSummary';
import { SubjectAttendance } from '../components/attendance/SubjectAttendance';
import { AttendancePlanner } from '../components/attendance/AttendancePlanner';
import { CalendarCheck, RotateCw, AlertTriangle, Loader2 } from 'lucide-react';

export const AttendancePage: React.FC = () => {
  const { token } = useAuth();
  const [data, setData] = useState<AttendanceTrackerData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAttendance = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getAttendanceApi(token || undefined);
      setData(result);
    } catch (err: any) {
      setError(err?.message || 'Unable to load attendance');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAttendance();
  }, [fetchAttendance]);

  // Loading state independent of authentication loading
  if (isLoading) {
    return (
      <div className="attendance-page-container" data-testid="attendance-page-loading">
        <div className="attendance-status-card loading-card" role="status" aria-live="polite">
          <Loader2 className="attendance-spinner" size={36} />
          <h2 className="loading-text">AI/Attendance data loading...</h2>
          <p className="loading-subtext">Fetching verified academic attendance records</p>
        </div>
      </div>
    );
  }

  // Error state with Retry button
  if (error || !data) {
    return (
      <div className="attendance-page-container" data-testid="attendance-page-error">
        <div className="attendance-status-card error-card" role="alert">
          <div className="error-icon-bubble">
            <AlertTriangle size={32} />
          </div>
          <h2 className="error-title">Unable to load attendance</h2>
          <p className="error-message">
            {error || 'Unable to retrieve academic attendance records from the server.'}
          </p>
          <button
            type="button"
            className="attendance-retry-btn"
            onClick={fetchAttendance}
            data-testid="attendance-retry-btn"
          >
            <RotateCw size={16} />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

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
            Verified subject attendance, regulatory compliance, and mathematical projection planner
          </p>
        </div>

        <div className="header-action-area">
          <button
            type="button"
            className="attendance-refresh-btn"
            onClick={fetchAttendance}
            title="Refresh attendance records"
            data-testid="attendance-refresh-btn"
          >
            <RotateCw size={16} />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="attendance-content-layout">
        {/* Overall Attendance Summary Card */}
        <AttendanceSummary
          student={data.student}
          rollNumber={data.roll_number}
          overall={data.overall}
          required={data.required}
          status={data.status}
        />

        {/* Mathematical Planner */}
        <AttendancePlanner subjects={data.subjects} overall={data.overall} />

        {/* Subject-wise Cards Breakdown */}
        <SubjectAttendance subjects={data.subjects} />
      </div>
    </div>
  );
};
