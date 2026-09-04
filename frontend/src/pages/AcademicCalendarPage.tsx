import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Filter, Clock, FileText, Loader2, AlertTriangle } from 'lucide-react';
import { getAcademicCalendarApi, type AcademicCalendarItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const AcademicCalendarPage: React.FC = () => {
  const [events, setEvents] = useState<AcademicCalendarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [programFilter, setProgramFilter] = useState('All');
  const [yearFilter, setYearFilter] = useState('All');
  const [academicYearFilter, setAcademicYearFilter] = useState('2026-2027');
  const navigate = useNavigate();

  useEffect(() => {
    const fetchCalendar = async () => {
      try {
        setLoading(true);
        const params: any = {
          academic_year: academicYearFilter !== 'All' ? academicYearFilter : undefined,
          program: programFilter !== 'All' ? programFilter : undefined,
          year: yearFilter !== 'All' ? yearFilter : undefined,
        };
        const data = await getAcademicCalendarApi(params);
        setEvents(data);
      } catch (err) {
        console.error('Failed to load academic calendar:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchCalendar();
  }, [programFilter, yearFilter, academicYearFilter]);

  return (
    <div className="full-page-container" data-testid="academic-calendar-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      <div className="page-header-banner">
        <div className="banner-icon-box purple">
          <Calendar size={28} />
        </div>
        <div>
          <h1 className="page-heading">Official Academic Calendar</h1>
          <p className="page-subheading">
            Key semester milestones, approved academic calendars, reopening dates, and preparation schedules for MITS.
          </p>
        </div>
      </div>

      <SourceBadge
        sourceName="MITS Academic Section & Dean of Academics"
        sourceUrl="https://mits.ac.in/academic-calenders"
      />

      {/* Filter Toolbar */}
      <div className="calendar-filter-bar">
        <div className="filter-group">
          <Filter size={16} className="filter-icon" />
          <span className="filter-label">Filter Events:</span>
        </div>

        <div className="filter-selects-row">
          <select
            value={academicYearFilter}
            onChange={(e) => setAcademicYearFilter(e.target.value)}
            className="filter-select"
          >
            <option value="2026-2027">Academic Year: 2026-2027</option>
            <option value="2025-2026">Academic Year: 2025-2026</option>
            <option value="All">All Academic Years</option>
          </select>

          <select
            value={programFilter}
            onChange={(e) => setProgramFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">All Programs (B.Tech, M.Tech, MCA, MBA, BBA, BCA)</option>
            <option value="B.Tech">B.Tech</option>
            <option value="M.Tech">M.Tech</option>
            <option value="MCA">MCA</option>
            <option value="MBA">MBA</option>
            <option value="BBA">BBA</option>
            <option value="BCA">BCA</option>
          </select>

          <select
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
            className="filter-select"
          >
            <option value="All">All Years</option>
            <option value="I Year">I Year</option>
            <option value="II Year">II Year</option>
            <option value="III Year">III Year</option>
            <option value="IV Year">IV Year</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="page-loading-container">
          <Loader2 size={32} className="animate-spin text-purple-400" />
          <div>Loading official calendar events...</div>
        </div>
      ) : events.length === 0 ? (
        <div className="card-empty-state">
          <Calendar className="empty-icon" size={32} />
          <div className="empty-title">Currently no official events match the selected filter.</div>
          <div className="empty-subtext">Verified source: https://mits.ac.in/academic-calenders</div>
        </div>
      ) : (
        <div className="calendar-timeline-list">
          {events.map((ev) => {
            const startDate = ev.start_date
              ? new Date(ev.start_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
              : 'Current Term';
            const endDate = ev.end_date
              ? new Date(ev.end_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
              : null;

            return (
              <div key={ev.id} className="timeline-event-card">
                <div className="timeline-date-pillar">
                  <Clock size={16} color="#c084fc" />
                  <span className="timeline-date-str">{startDate}</span>
                  {endDate && <span className="timeline-date-end">to {endDate}</span>}
                </div>

                <div className="timeline-content-body">
                  <div className="timeline-badges-row">
                    <span className="item-category-tag tag-purple">{ev.program}</span>
                    {ev.year && <span className="item-meta-tag">{ev.year}</span>}
                    {ev.semester && <span className="item-meta-tag">{ev.semester}</span>}
                    <span className="item-meta-tag">{ev.academic_year}</span>
                  </div>

                  <h3 className="timeline-event-title">{ev.event_name}</h3>
                  {ev.event_description && (
                    <p className="timeline-event-desc">{ev.event_description}</p>
                  )}

                  {ev.document_url && ev.is_valid !== false ? (
                    <a
                      href={ev.document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-document-link"
                    >
                      <FileText size={13} /> View Official Calendar Document (PDF)
                    </a>
                  ) : (
                    ev.document_url && (
                      <span className="source-link-disabled" style={{ fontSize: '0.8rem', color: '#9ca3af', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={13} color="#f59e0b" /> Official document temporarily unavailable on MITS portal
                      </span>
                    )
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
