import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Briefcase, TrendingUp, Calendar, CheckCircle2, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { getPlacementsApi, type PlacementItem } from '../services/api';
import { SourceBadge } from '../components/common/SourceBadge';

export const PlacementsPage: React.FC = () => {
  const [placements, setPlacements] = useState<PlacementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchPlacements = async () => {
      try {
        setLoading(true);
        const data = await getPlacementsApi();
        setPlacements(data);
      } catch (err) {
        console.error('Failed to load placements:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlacements();
  }, []);

  return (
    <div className="full-page-container" data-testid="placements-page">
      <div className="detail-page-header-nav">
        <button className="back-link-btn" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>

      <div className="page-header-banner">
        <div className="banner-icon-box rose">
          <Briefcase size={28} />
        </div>
        <div>
          <h1 className="page-heading">Training & Campus Placements</h1>
          <p className="page-subheading">
            Official recruitment drives, eligibility guidelines, top hiring partners, and salary packages at MITS.
          </p>
        </div>
      </div>

      <SourceBadge
        sourceName="MITS Training & Placement Cell"
        sourceUrl="https://mits.ac.in/placements"
        documentUrl="https://mits.ac.in/assets/pdf/placements/AWS_Campus_Drive_2026.pdf"
      />

      {loading ? (
        <div className="page-loading-container">
          <Loader2 size={32} className="animate-spin text-rose-400" />
          <div>Loading official placement drives...</div>
        </div>
      ) : placements.length === 0 ? (
        <div className="card-empty-state">
          <Briefcase className="empty-icon" size={32} />
          <div className="empty-title">Currently no active placement drives are posted.</div>
          <div className="empty-subtext">Last verified: 26 August 2026</div>
        </div>
      ) : (
        <div className="placements-records-grid">
          {placements.map((item) => {
            const driveDate = item.drive_date
              ? new Date(item.drive_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
              : 'Upcoming';

            return (
              <div key={item.id} className="placement-card-item">
                <div className="placement-card-header">
                  <div className="company-title-group">
                    <div className="placement-company-avatar large">
                      <TrendingUp size={20} color="#f43f5e" />
                    </div>
                    <div>
                      <h3 className="placement-company-name">{item.company}</h3>
                      <div className="placement-role-text">{item.job_role || 'Engineering Role'}</div>
                    </div>
                  </div>
                  {item.package_details && (
                    <span className="package-tag">{item.package_details}</span>
                  )}
                </div>

                {item.description && <p className="placement-desc-text">{item.description}</p>}

                {item.eligibility && (
                  <div className="eligibility-box">
                    <CheckCircle2 size={15} color="#10b981" />
                    <span><strong>Eligibility:</strong> {item.eligibility}</span>
                  </div>
                )}

                <div className="placement-footer-row">
                  <span className="drive-date-label">
                    <Calendar size={13} /> Drive Date: {driveDate}
                  </span>
                  <div className="placement-action-links">
                    {item.document_url && (
                      <a
                        href={item.document_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary small"
                      >
                        <FileText size={13} /> View Circular
                      </a>
                    )}
                    <a
                      href={item.source_url || 'https://mits.ac.in/placements'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-primary small"
                    >
                      <ExternalLink size={13} /> Official Portal
                    </a>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
