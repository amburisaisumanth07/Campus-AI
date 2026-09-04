import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, GraduationCap, ExternalLink, Calendar, Search, Loader2, AlertTriangle } from 'lucide-react';
import { getExaminationsApi, type ExaminationItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const ExaminationsPage: React.FC = () => {
  const [exams, setExams] = useState<ExaminationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedType, setSelectedType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  const categories = [
    { id: 'all', label: 'All Notices' },
    { id: 'timetable', label: 'Timetables' },
    { id: 'hall_ticket', label: 'Hall Tickets' },
    { id: 'result', label: 'Results & Grades' },
    { id: 'revaluation', label: 'Revaluation' },
    { id: 'notification', label: 'Circulars & Regulations' },
  ];

  useEffect(() => {
    const fetchExams = async () => {
      try {
        setLoading(true);
        const params: any = {};
        if (selectedType !== 'all') params.exam_type = selectedType;
        const data = await getExaminationsApi(params);
        setExams(data);
      } catch (err) {
        console.error('Failed to load exams:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchExams();
  }, [selectedType]);

  const filteredExams = exams.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      item.title.toLowerCase().includes(term) ||
      (item.description && item.description.toLowerCase().includes(term)) ||
      (item.program && item.program.toLowerCase().includes(term))
    );
  });

  return (
    <div className="full-page-container" data-testid="examinations-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      <div className="page-header-banner">
        <div className="banner-icon-box amber">
          <GraduationCap size={28} />
        </div>
        <div>
          <h1 className="page-heading">University Examination Section</h1>
          <p className="page-subheading">
            Official semester schedules, timetables, hall-ticket notices, revaluation circulars, and academic regulations.
          </p>
        </div>
      </div>

      <SourceBadge
        sourceName="Controller of Examinations (CoE), MITS"
        sourceUrl="https://mits.ac.in/university-exam"
      />

      {/* Category Tabs */}
      <div className="exam-tabs-container">
        {categories.map((cat) => (
          <button
            key={cat.id}
            className={`exam-tab-btn ${selectedType === cat.id ? 'active' : ''}`}
            onClick={() => setSelectedType(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="exam-search-wrapper">
        <Search size={16} className="search-input-icon" />
        <input
          type="text"
          className="search-input-field"
          placeholder="Filter by subject, program, regulation (e.g. B.Tech, R25, Mid-term)..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="page-loading-container">
          <Loader2 size={32} className="animate-spin text-amber-400" />
          <div>Loading official examination records...</div>
        </div>
      ) : filteredExams.length === 0 ? (
        <div className="card-empty-state">
          <GraduationCap className="empty-icon" size={32} />
          <div className="empty-title">Currently no official examination notices match your filter.</div>
          <div className="empty-subtext">Verified source: https://mits.ac.in/university-exam</div>
        </div>
      ) : (
        <div className="exam-records-grid">
          {filteredExams.map((item) => {
            const published = item.published_date
              ? new Date(item.published_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
              : 'Recent';

            return (
              <div key={item.id} className="exam-card-item">
                <div className="exam-card-header">
                  <span className={`item-category-tag tag-exam-${(item.exam_type || 'notification').toLowerCase()}`}>
                    {item.exam_type.replace('_', ' ').toUpperCase()}
                  </span>
                  <span className="exam-date-label">
                    <Calendar size={12} /> {published}
                  </span>
                </div>

                <h3 className="exam-card-title">{item.title}</h3>
                {item.description && <p className="exam-card-desc">{item.description}</p>}

                <div className="exam-card-meta">
                  <span>Program: {item.program || 'All Programs'}</span>
                  {item.year && <span>• {item.year}</span>}
                  {item.semester && <span>• {item.semester}</span>}
                </div>

                <div className="exam-card-actions">
                  {item.document_url && item.is_valid !== false ? (
                    <a
                      href={item.document_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary"
                    >
                      <ExternalLink size={14} /> View Timetable / PDF
                    </a>
                  ) : (
                    item.document_url && (
                      <span className="source-link-disabled" style={{ fontSize: '0.8rem', color: '#9ca3af', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={13} color="#f59e0b" /> Document currently unavailable
                      </span>
                    )
                  )}
                  {item.source_url && (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary"
                    >
                      Official Portal
                    </a>
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
