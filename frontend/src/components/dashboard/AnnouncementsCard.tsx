import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, ChevronRight, Calendar } from 'lucide-react';
import { getAnnouncementsApi, type AnnouncementItem } from '../../services/api';

export const AnnouncementsCard: React.FC = () => {
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchAnnouncements = async () => {
      try {
        setLoading(true);
        const data = await getAnnouncementsApi(undefined, 4);
        if (isMounted) {
          setAnnouncements(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load announcements');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchAnnouncements();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="dashboard-card" data-testid="announcements-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box blue">
            <Bell size={20} />
          </div>
          <div>
            <h3>Latest Announcements</h3>
            <span className="card-subtitle">Official university circulars and notices</span>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="card-skeleton-list">
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
          <div className="skeleton-row animate-pulse"></div>
        </div>
      ) : error ? (
        <div className="card-empty-state">
          <div className="empty-subtext">Currently unable to load official announcements.</div>
        </div>
      ) : announcements.length === 0 ? (
        <div className="card-empty-state" data-testid="announcements-empty">
          <Bell className="empty-icon" size={28} />
          <div className="empty-title">Currently no official information is available.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="card-items-list">
          {announcements.map((item) => {
            const formattedDate = item.published_date
              ? new Date(item.published_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
              : 'Recent';

            return (
              <div
                key={item.id}
                className="card-item-row clickable-item"
                onClick={() => navigate(`/announcements/${item.id}`)}
                role="button"
                tabIndex={0}
              >
                <div className="item-left">
                  <span className={`item-category-tag tag-${(item.category || 'general').toLowerCase()}`}>
                    {item.category}
                  </span>
                  <div className="item-details">
                    <div className="item-title">{item.title}</div>
                    <div className="item-meta">
                      <Calendar size={12} /> Published: {formattedDate} • {item.source_name}
                    </div>
                  </div>
                </div>
                <ChevronRight size={16} className="item-action-icon" />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
