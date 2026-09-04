import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, ChevronRight, ArrowUpRight } from 'lucide-react';
import { getExaminationsApi, type ExaminationItem } from '../../services/api';

export const ExaminationsCard: React.FC = () => {
  const [exams, setExams] = useState<ExaminationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchExams = async () => {
      try {
        setLoading(true);
        const data = await getExaminationsApi();
        if (isMounted) {
          setExams(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load examinations');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchExams();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="dashboard-card" data-testid="examinations-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box amber">
            <GraduationCap size={20} />
          </div>
          <div>
            <h3>Examinations</h3>
            <span className="card-subtitle">Official schedules, notices & regulations</span>
          </div>
        </div>
        <button
          className="card-header-action-btn"
          onClick={() => navigate('/examinations')}
          title="View All Examination Sections"
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
          <div className="empty-subtext">Currently unable to load official examination notices.</div>
        </div>
      ) : exams.length === 0 ? (
        <div className="card-empty-state" data-testid="examinations-empty">
          <GraduationCap className="empty-icon" size={28} />
          <div className="empty-title">Currently no official examination notices are available.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="card-items-list">
          {exams.slice(0, 4).map((item) => (
            <div
              key={item.id}
              className="card-item-row clickable-item"
              onClick={() => navigate('/examinations')}
              role="button"
              tabIndex={0}
            >
              <div className="item-left">
                <span className={`item-category-tag tag-exam-${(item.exam_type || 'notification').toLowerCase()}`}>
                  {item.exam_type.replace('_', ' ').toUpperCase()}
                </span>
                <div className="item-details">
                  <div className="item-title">{item.title}</div>
                  <div className="item-meta">
                    {item.program} {item.year ? `• ${item.year}` : ''} • {item.source_name}
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
