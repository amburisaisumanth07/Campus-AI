import React from 'react';
import type { SubjectAttendance } from '../../types/api';
import { getStatusCategory, getStatusLabel } from '../../utils/attendanceCalculator';
import { CheckCircle2, AlertTriangle, AlertCircle, BookOpen } from 'lucide-react';

interface SubjectAttendanceCardProps {
  subject: SubjectAttendance;
}

export const SubjectAttendanceCard: React.FC<SubjectAttendanceCardProps> = ({ subject }) => {
  const statusCategory = getStatusCategory(subject.percentage);
  const statusLabel = getStatusLabel(subject.percentage);

  const getStatusIcon = () => {
    switch (statusCategory) {
      case 'safe':
        return <CheckCircle2 size={14} className="subject-status-icon safe" />;
      case 'conditionally-eligible':
        return <AlertTriangle size={14} className="subject-status-icon warning" />;
      case 'critical':
      default:
        return <AlertCircle size={14} className="subject-status-icon critical" />;
    }
  };

  return (
    <div
      className={`subject-attendance-card ${statusCategory}`}
      data-testid={`subject-card-${subject.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}
    >
      <div className="subject-card-header">
        <div className="subject-title-box">
          <BookOpen size={18} className="subject-icon" />
          <h3 className="subject-name" data-testid="subject-name">{subject.name}</h3>
        </div>
        <div className={`subject-status-badge ${statusCategory}`} data-testid="subject-status-badge">
          {getStatusIcon()}
          <span>{statusLabel}</span>
        </div>
      </div>

      <div className="subject-card-stats">
        <div className="subject-classes-count">
          <span className="classes-ratio" data-testid="subject-classes-ratio">
            <strong>{subject.attended}</strong> / {subject.total}
          </span>
          <span className="classes-label">Classes Attended</span>
        </div>

        <div className="subject-percentage-display">
          <span className={`subject-percent-value ${statusCategory}`} data-testid="subject-percentage">
            {subject.percentage.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="subject-progress-track">
        <div
          className={`subject-progress-fill ${statusCategory}`}
          style={{ width: `${Math.min(100, Math.max(0, subject.percentage))}%` }}
        />
      </div>
    </div>
  );
};
