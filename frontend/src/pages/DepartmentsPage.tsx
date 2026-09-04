import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Building2, ChevronRight, UserCheck, Loader2 } from 'lucide-react';
import { getDepartmentsApi, type DepartmentItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const DepartmentsPage: React.FC = () => {
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDepts = async () => {
      try {
        setLoading(true);
        const data = await getDepartmentsApi();
        setDepartments(data);
      } catch (err) {
        console.error('Failed to load departments:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchDepts();
  }, []);

  return (
    <div className="full-page-container" data-testid="departments-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      <div className="page-header-banner">
        <div className="banner-icon-box emerald">
          <Building2 size={28} />
        </div>
        <div>
          <h1 className="page-heading">Academic Departments & Schools</h1>
          <p className="page-subheading">
            Official degree programs, faculty profiles, curriculum, and research domains across MITS.
          </p>
        </div>
      </div>

      <SourceBadge
        sourceName="MITS Academic Council & Official Department Portals"
        sourceUrl="https://mits.ac.in/programmes"
      />

      {loading ? (
        <div className="page-loading-container">
          <Loader2 size={32} className="animate-spin text-emerald-400" />
          <div>Loading official departments...</div>
        </div>
      ) : departments.length === 0 ? (
        <div className="card-empty-state">
          <Building2 className="empty-icon" size={32} />
          <div className="empty-title">Currently no official department records are available.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="departments-grid">
          {departments.map((dept) => (
            <div
              key={dept.id}
              className="department-overview-card"
              onClick={() => navigate(`/departments/${dept.code.toLowerCase()}`)}
              role="button"
              tabIndex={0}
            >
              <div className="dept-card-top">
                <span className="item-dept-code-tag large">{dept.code}</span>
                <span className="dept-school-badge">{dept.school || 'Engineering'}</span>
              </div>

              <h3 className="dept-card-name">{dept.name}</h3>
              {dept.description && <p className="dept-card-desc">{dept.description}</p>}

              {dept.hod && (
                <div className="dept-hod-row">
                  <UserCheck size={14} color="#10b981" />
                  <span>Head of Department: <strong>{dept.hod}</strong></span>
                </div>
              )}

              <div className="dept-card-footer">
                <span className="dept-view-link">
                  View Programs & Faculty <ChevronRight size={15} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
