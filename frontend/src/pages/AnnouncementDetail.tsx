import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Calendar, Download, ExternalLink, FileText, Loader2 } from 'lucide-react';
import { getAnnouncementByIdApi, type AnnouncementItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const AnnouncementDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [announcement, setAnnouncement] = useState<AnnouncementItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDetail = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const data = await getAnnouncementByIdApi(parseInt(id, 10));
        setAnnouncement(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load announcement details');
      } finally {
        setLoading(false);
      }
    };
    fetchDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="page-loading-container">
        <Loader2 size={32} className="animate-spin text-purple-400" />
        <div>Loading official announcement...</div>
      </div>
    );
  }

  if (error || !announcement) {
    return (
      <div className="page-error-container">
        <div className="error-title">Announcement Not Found</div>
        <div className="error-desc">{error || 'The requested official announcement does not exist or has been archived.'}</div>
        <button className="btn-secondary" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>
    );
  }

  const formattedDate = announcement.published_date
    ? new Date(announcement.published_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })
    : 'Recent';

  return (
    <div className="detail-page-container" data-testid="announcement-detail-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      <div className="detail-content-card">
        <div className="detail-top-badges">
          <span className={`item-category-tag tag-${(announcement.category || 'general').toLowerCase()}`}>
            {announcement.category}
          </span>
          <span className="detail-date-badge">
            <Calendar size={13} /> Published: {formattedDate}
          </span>
        </div>

        <h1 className="detail-page-title">{announcement.title}</h1>

        <SourceBadge
          sourceName={announcement.source_name}
          sourceUrl={announcement.source_url}
          documentUrl={announcement.document_url}
          publishedDate={announcement.published_date}
          lastVerifiedAt={announcement.last_verified_at}
        />

        <div className="detail-body-section">
          <h3>Official Notification Content</h3>
          <div className="detail-body-text">
            {announcement.content ? (
              announcement.content.split('\n\n').map((para, i) => <p key={i}>{para}</p>)
            ) : (
              <p>{announcement.description}</p>
            )}
          </div>
        </div>

        {announcement.document_url && (
          <div className="detail-document-action-box">
            <div className="doc-action-info">
              <FileText size={24} className="doc-action-icon" />
              <div>
                <div className="doc-action-title">Official Attachment Available</div>
                <div className="doc-action-sub">View or download the official signed PDF circular.</div>
              </div>
            </div>
            <div className="doc-action-buttons">
              <a
                href={announcement.document_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary"
              >
                <ExternalLink size={15} /> View PDF
              </a>
              <a
                href={announcement.document_url}
                download
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                <Download size={15} /> Download
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
