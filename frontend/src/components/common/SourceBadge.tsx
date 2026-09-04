import React from 'react';
import { ExternalLink, ShieldCheck, FileText, AlertTriangle } from 'lucide-react';

interface SourceBadgeProps {
  sourceName?: string;
  sourceUrl?: string | null;
  documentUrl?: string | null;
  publishedDate?: string | null;
  lastVerifiedAt?: string | null;
  isValid?: boolean;
  className?: string;
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  sourceName = 'Madanapalle Institute of Technology & Science',
  sourceUrl = 'https://mits.ac.in/',
  documentUrl,
  publishedDate,
  lastVerifiedAt,
  isValid = true,
  className = '',
}) => {
  const formattedDate = publishedDate
    ? new Date(publishedDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : null;

  const formattedVerified = lastVerifiedAt
    ? new Date(lastVerifiedAt).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
    : formattedDate || 'Current Academic Year';

  return (
    <div className={`source-badge-container ${className}`} data-testid="source-badge">
      <div className="source-badge-header">
        {isValid ? (
          <span className="official-source-indicator">
            <span className="status-dot-green"></span>
            <ShieldCheck size={14} className="source-icon" />
            Verified Official MITS Source
          </span>
        ) : (
          <span className="official-source-indicator warning" style={{ color: '#d97706' }}>
            <AlertTriangle size={14} className="source-icon" />
            Source Currently Unavailable
          </span>
        )}
        {formattedDate && <span className="source-published-date">Published: {formattedDate}</span>}
      </div>

      <div className="source-meta-row">
        <span className="source-institution-name">Source: {sourceName}</span>
        <span className="source-verified-date">Last Verified: {formattedVerified}</span>
      </div>

      <div className="source-action-links">
        {sourceUrl && isValid ? (
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="source-external-link"
            title="Open official college source website"
          >
            <ExternalLink size={13} /> Open Official Source
          </a>
        ) : (
          sourceUrl && !isValid && (
            <span className="source-link-disabled" style={{ fontSize: '0.8rem', color: '#9ca3af' }}>
              Official source link temporarily unavailable
            </span>
          )
        )}
        {documentUrl && isValid && (
          <a
            href={documentUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="source-document-link"
            title="View original official PDF document"
          >
            <FileText size={13} /> View Original PDF
          </a>
        )}
      </div>
    </div>
  );
};
