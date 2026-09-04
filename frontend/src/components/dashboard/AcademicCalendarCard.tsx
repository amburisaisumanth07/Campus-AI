import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, ChevronRight, Clock, ArrowUpRight } from 'lucide-react';
import { getAcademicCalendarApi, type AcademicCalendarItem } from '../../services/api';

export const AcademicCalendarCard: React.FC = () => {
  const [events, setEvents] = useState<AcademicCalendarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchCalendar = async () => {
      try {
        setLoading(true);
        const data = await getAcademicCalendarApi({ limit: 4 });
        if (isMounted) {
          setEvents(data);
          setError(null);
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || 'Failed to load calendar');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchCalendar();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="dashboard-card" data-testid="academic-calendar-card">
      <div className="card-top-bar">
        <div className="card-title-group">
          <div className="card-icon-box purple">
            <Calendar size={20} />
          </div>
          <div>
            <h3>Academic Calendar</h3>
            <span className="card-subtitle">Official semester timelines & key dates</span>
          </div>
        </div>
        <button
          className="card-header-action-btn"
          onClick={() => navigate('/academic-calendar')}
          title="View Full Academic Calendar"
        >
          View Full <ArrowUpRight size={14} />
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
          <div className="empty-subtext">Currently unable to load official academic calendar.</div>
        </div>
      ) : events.length === 0 ? (
        <div className="card-empty-state" data-testid="calendar-empty">
          <Calendar className="empty-icon" size={28} />
          <div className="empty-title">Currently no official calendar dates are available.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="card-items-list">
          {events.slice(0, 4).map((ev) => {
            const startDate = ev.start_date
              ? new Date(ev.start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
              : 'TBA';

            return (
              <div
                key={ev.id}
                className="card-item-row clickable-item"
                onClick={() => navigate('/academic-calendar')}
                role="button"
                tabIndex={0}
              >
                <div className="item-left">
                  <div className="calendar-date-badge">
                    <Clock size={12} />
                    <span>{startDate}</span>
                  </div>
                  <div className="item-details">
                    <div className="item-title">{ev.event_name}</div>
                    <div className="item-meta">
                      {ev.program} {ev.year ? `• ${ev.year}` : ''} {ev.semester ? `• ${ev.semester}` : ''}
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
