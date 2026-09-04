import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Briefcase, ChevronRight, ArrowUpRight, TrendingUp } from 'lucide-react';
import { getPlacementsApi, type PlacementItem } from '../../services/api';

export const PlacementsCard: React.FC = () => {
  const [placements, setPlacements] = useState<PlacementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchPlacements = async () => {
      try {
        setLoading(true);
        const data = await getPlacementsApi();
        if (isMounted) {
          setPlacements(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load placements');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchPlacements();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="dashboard-card" data-testid="placements-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box rose">
            <Briefcase size={20} />
          </div>
          <div>
            <h3>Training & Placements</h3>
            <span className="card-subtitle">Recruitment drives, packages & circulars</span>
          </div>
        </div>
        <button
          className="card-header-action-btn"
          onClick={() => navigate('/placements')}
          title="View All Campus Placement Drives"
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
          <div className="empty-subtext">Currently unable to load placement drives.</div>
        </div>
      ) : placements.length === 0 ? (
        <div className="card-empty-state" data-testid="placements-empty">
          <Briefcase className="empty-icon" size={28} />
          <div className="empty-title">Currently no active placement drives are scheduled.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="card-items-list">
          {placements.slice(0, 4).map((item) => (
            <div
              key={item.id}
              className="card-item-row clickable-item"
              onClick={() => navigate('/placements')}
              role="button"
              tabIndex={0}
            >
              <div className="item-left">
                <div className="placement-company-avatar">
                  <TrendingUp size={16} color="#f43f5e" />
                </div>
                <div className="item-details">
                  <div className="item-title">{item.company}</div>
                  <div className="item-meta">
                    {item.job_role || 'Engineering Role'} {item.package_details ? `• ${item.package_details}` : ''}
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
