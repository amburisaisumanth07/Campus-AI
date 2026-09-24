import React from 'react';
import type { SubjectAttendance as SubjectAttendanceType } from '../../types/api';
import { SubjectAttendanceCard } from './SubjectAttendanceCard';
import { Layers } from 'lucide-react';

interface SubjectAttendanceProps {
  subjects: SubjectAttendanceType[];
}

export const SubjectAttendance: React.FC<SubjectAttendanceProps> = ({ subjects }) => {
  return (
    <section className="subjects-attendance-section" data-testid="subjects-attendance-section">
      <div className="section-header-row">
        <div className="section-title-with-icon">
          <Layers size={20} className="section-header-icon" />
          <h2 className="section-title">Subject-wise Breakdown</h2>
        </div>
        <span className="subjects-count-badge">{subjects.length} Subjects</span>
      </div>

      <div className="subjects-grid" data-testid="subjects-grid">
        {subjects.map((subject) => (
          <SubjectAttendanceCard key={subject.name} subject={subject} />
        ))}
      </div>
    </section>
  );
};
