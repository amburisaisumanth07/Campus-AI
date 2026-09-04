import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, ChevronRight, ArrowUpRight } from 'lucide-react';
import { getDepartmentsApi, type DepartmentItem } from '../../services/api';

export const DepartmentsCard: React.FC = () => {
  const [departments, setDepartments] = useState<DepartmentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchDepartments = async () => {
      try {
        setLoading(true);
        const data = await getDepartmentsApi();
        if (isMounted) {
          setDepartments(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load departments');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchDepartments();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="dashboard-card" data-testid="departments-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box emerald">
            <Building2 size={20} />
          </div>
          <div>
            <h3>Academic Departments</h3>
            <span className="card-subtitle">Schools, programs & faculty profiles</span>
          </div>
        </div>
        <button
          className="card-header-action-btn"
          onClick={() => navigate('/departments')}
          title="View All Academic Departments"
        >
          View All <ArrowUpRight size={14} />
        </button>
      </div>

      {loading ? (
        <div className="card-skeleton-list">
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
        </div>
      ) : error ? (
        <div className="card-empty-state">
          <div className="empty-subtext">Currently unable to load official departments.</div>
        </div>
      ) : departments.length === 0 ? (
        <div className="card-empty-state" data-testid="departments-empty">
          <Building2 className="empty-icon" size={28} />
          <div className="empty-title">Currently no official department records are available.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="card-items-list">
          {departments.slice(0, 4).map((dept) => (
            <div
              key={dept.id}
              className="card-item-row clickable-item"
              onClick={() => navigate(`/departments/${dept.code.toLowerCase()}`)}
              role="button"
              tabIndex={0}
            >
              <div className="item-left">
                <span className="item-dept-code-tag">{dept.code}</span>
                <div className="item-details">
                  <div className="item-title">{dept.name}</div>
                  <div className="item-meta">
                    {dept.school || 'Engineering'} {dept.hod ? `• HoD: ${dept.hod}` : ''}
                  </div>
                </div>
              </div>
              <ChevronRight size={16} className="item-action-icon" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
