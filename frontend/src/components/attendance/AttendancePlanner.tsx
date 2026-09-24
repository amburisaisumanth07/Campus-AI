import React from 'react';
import type { SubjectAttendance } from '../../types/api';
import {
  calculateCanMiss,
  calculateClassesRequired,
  MIN_REQUIRED_ATTENDANCE,
} from '../../utils/attendanceCalculator';
import { Calculator, CheckCircle2, ShieldCheck, Flame, Compass } from 'lucide-react';

interface AttendancePlannerProps {
  subjects: SubjectAttendance[];
  overall: number;
}

export const AttendancePlanner: React.FC<AttendancePlannerProps> = ({ subjects, overall }) => {
  const totalAttended = subjects.reduce((sum, s) => sum + s.attended, 0);
  const totalClasses = subjects.reduce((sum, s) => sum + s.total, 0);

  const canMissOverall = calculateCanMiss(totalAttended, totalClasses, MIN_REQUIRED_ATTENDANCE);
  const requiredClassesOverall = calculateClassesRequired(totalAttended, totalClasses, MIN_REQUIRED_ATTENDANCE);

  const isExactlyRequired = Math.abs(overall - MIN_REQUIRED_ATTENDANCE) < 0.001;
  const isAboveRequired = overall > MIN_REQUIRED_ATTENDANCE;
  const isBelowRequired = overall < MIN_REQUIRED_ATTENDANCE;

  return (
    <section className="attendance-planner-card" data-testid="attendance-planner-section">
      <div className="planner-header">
        <div className="planner-title-box">
          <Calculator size={22} className="planner-icon" />
          <div>
            <h2 className="planner-title">Attendance Planner & Projection</h2>
            <p className="planner-subtitle">
              Mathematical projection based on official 75% minimum academic threshold
            </p>
          </div>
        </div>
      </div>

      <div className="planner-body">
        {/* Scenario 1: Above 75% Requirement */}
        {isAboveRequired && (
          <div className="planner-projection-card safe" data-testid="planner-safe-card">
            <div className="projection-icon-wrapper safe">
              <ShieldCheck size={26} />
            </div>
            <div className="projection-content">
              <div className="projection-headline">
                <span className="projection-badge safe">BUFFER AVAILABLE</span>
                <h3>Safe to Miss</h3>
              </div>
              <p className="projection-main-text">
                You can safely miss up to{' '}
                <strong className="planner-highlight-number" data-testid="bunkable-classes-count">
                  {canMissOverall}
                </strong>{' '}
                class{canMissOverall === 1 ? '' : 'es'} without dropping below the required{' '}
                {MIN_REQUIRED_ATTENDANCE}% threshold.
              </p>
              <div className="projection-formula-explanation">
                <span>
                  Mathematical guarantee: After missing {canMissOverall} class{canMissOverall === 1 ? '' : 'es'}, your overall attendance will remain at or above {MIN_REQUIRED_ATTENDANCE}%.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Scenario 2: Exactly 75% Requirement */}
        {isExactlyRequired && (
          <div className="planner-projection-card exact" data-testid="planner-exact-card">
            <div className="projection-icon-wrapper exact">
              <CheckCircle2 size={26} />
            </div>
            <div className="projection-content">
              <div className="projection-headline">
                <span className="projection-badge exact">EXACTLY AT THRESHOLD</span>
                <h3>Zero Margin</h3>
              </div>
              <p className="projection-main-text" data-testid="planner-exact-message">
                You are currently at <strong>exactly 75%</strong> attendance. You cannot miss any upcoming classes without dropping below the regulatory threshold.
              </p>
              <div className="projection-formula-explanation">
                <span>
                  Every missed class from now on will immediately push attendance below 75%.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Scenario 3: Below 75% Requirement */}
        {isBelowRequired && (
          <div className="planner-projection-card critical" data-testid="planner-critical-card">
            <div className="projection-icon-wrapper critical">
              <Flame size={26} />
            </div>
            <div className="projection-content">
              <div className="projection-headline">
                <span className="projection-badge critical">ATTENDANCE DEFICIT</span>
                <h3>Action Plan to Recover</h3>
              </div>
              <p className="projection-main-text">
                You must attend the next{' '}
                <strong className="planner-highlight-number critical" data-testid="required-classes-count">
                  {requiredClassesOverall}
                </strong>{' '}
                consecutive class{requiredClassesOverall === 1 ? '' : 'es'} without missing any to reach the required{' '}
                {MIN_REQUIRED_ATTENDANCE}% threshold.
              </p>
              <div className="projection-formula-explanation">
                <span>
                  Mathematical guarantee: After attending {requiredClassesOverall} consecutive class{requiredClassesOverall === 1 ? '' : 'es'}, your attendance reaches at least {MIN_REQUIRED_ATTENDANCE}%.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Subject Planner Quick Summary Table */}
        <div className="planner-subjects-breakdown">
          <div className="breakdown-header">
            <Compass size={16} />
            <h4>Subject Attendance Projections</h4>
          </div>
          <div className="planner-table-wrapper">
            <table className="planner-summary-table" data-testid="planner-subjects-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Current</th>
                  <th>Status</th>
                  <th>Planner Guidance</th>
                </tr>
              </thead>
              <tbody>
                {subjects.map((sub) => {
                  const subMiss = calculateCanMiss(sub.attended, sub.total, MIN_REQUIRED_ATTENDANCE);
                  const subReq = calculateClassesRequired(sub.attended, sub.total, MIN_REQUIRED_ATTENDANCE);
                  const isSubExact = Math.abs(sub.percentage - MIN_REQUIRED_ATTENDANCE) < 0.001;

                  let guidance = '';
                  if (sub.percentage > MIN_REQUIRED_ATTENDANCE) {
                    guidance = `Can miss up to ${subMiss} class${subMiss === 1 ? '' : 'es'}`;
                  } else if (isSubExact) {
                    guidance = 'At requirement (0 classes can be missed)';
                  } else {
                    guidance = `Must attend ${subReq} consecutive class${subReq === 1 ? '' : 'es'}`;
                  }

                  return (
                    <tr key={sub.name} data-testid={`planner-row-${sub.name.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}>
                      <td className="planner-sub-name">{sub.name}</td>
                      <td className="planner-sub-pct">{sub.percentage.toFixed(2)}%</td>
                      <td>
                        <span className={`planner-sub-tag ${sub.percentage >= 75 ? 'safe' : sub.percentage >= 65 ? 'warning' : 'critical'}`}>
                          {sub.percentage >= 75 ? 'Safe' : sub.percentage >= 65 ? 'Conditional' : 'Critical'}
                        </span>
                      </td>
                      <td className="planner-sub-guidance">{guidance}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
};
