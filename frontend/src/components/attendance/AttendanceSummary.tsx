import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, User } from 'lucide-react';
import { getStatusCategory } from '../../utils/attendanceCalculator';

interface AttendanceSummaryProps {
  student: string;
  rollNumber: string;
  overall: number;
  required: number;
  status: string;
}

export const AttendanceSummary: React.FC<AttendanceSummaryProps> = ({
  student,
  rollNumber,
  overall,
  required,
  status,
}) => {
  const statusCategory = getStatusCategory(overall);
  const isSatisfied = overall >= required;

  // Circular gauge math: radius 52, circumference ~326.73
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, overall)) / 100) * circumference;

  const getStatusIcon = () => {
    switch (statusCategory) {
      case 'safe':
        return <CheckCircle2 size={18} className="status-icon safe" />;
      case 'conditionally-eligible':
        return <AlertTriangle size={18} className="status-icon warning" />;
      case 'critical':
      default:
        return <AlertCircle size={18} className="status-icon critical" />;
    }
  };

  return (
    <section className="attendance-summary-card" data-testid="attendance-summary-card">
      <div className="attendance-summary-header">
        <div className="summary-student-badge">
          <div className="student-avatar-box">
            <User size={20} />
          </div>
          <div className="student-identity">
            <span className="summary-section-label">ATTENDANCE</span>
            <h2 className="student-name" data-testid="student-name">{student}</h2>
            <span className="student-roll" data-testid="student-roll">{rollNumber}</span>
          </div>
        </div>

        <div className="summary-status-pill-wrapper">
          <div className={`attendance-status-pill ${statusCategory}`} data-testid="overall-status-badge">
            {getStatusIcon()}
            <span>{isSatisfied ? `✓ ${status}` : status}</span>
          </div>
        </div>
      </div>

      <div className="attendance-summary-body">
        {/* Circular Progress Gauge */}
        <div className="attendance-gauge-container">
          <svg className="attendance-gauge-svg" width="130" height="130" viewBox="0 0 130 130">
            {/* Background Track */}
            <circle
              className="gauge-track"
              cx="65"
              cy="65"
              r={radius}
              strokeWidth="10"
            />
            {/* Value Progress */}
            <circle
              className={`gauge-progress ${statusCategory}`}
              cx="65"
              cy="65"
              r={radius}
              strokeWidth="10"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform="rotate(-90 65 65)"
            />
          </svg>
          <div className="gauge-center-text">
            <span className="gauge-percent" data-testid="overall-attendance-value">{overall.toFixed(2)}%</span>
            <span className="gauge-label">Overall</span>
          </div>
        </div>

        {/* Key Metrics Columns */}
        <div className="attendance-metrics-grid">
          <div className="metric-box">
            <span className="metric-label">Required Threshold</span>
            <span className="metric-value required" data-testid="required-attendance-value">{required}%</span>
            <span className="metric-hint">Official MITS Regulation</span>
          </div>

          <div className="metric-box">
            <span className="metric-label">Compliance Status</span>
            <span className={`metric-value ${statusCategory}`} data-testid="compliance-status-value">
              {isSatisfied ? 'Requirement satisfied' : 'Below requirement'}
            </span>
            <span className="metric-hint">
              {overall >= required ? 'Eligible for semester exams' : 'Action required'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
