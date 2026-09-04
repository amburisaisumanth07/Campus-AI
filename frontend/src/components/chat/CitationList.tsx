import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, FileText, Bookmark, Globe, ExternalLink } from 'lucide-react';
import type { CitationItem, SourceCitation } from '../../types/api';

interface CitationListProps {
  citations?: (CitationItem | SourceCitation)[] | null;
}

export const CitationList: React.FC<CitationListProps> = ({ citations }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="citations-container">
      <button
        type="button"
        className="citations-toggle"
        onClick={() => setIsExpanded((prev) => !prev)}
        aria-expanded={isExpanded}
        aria-label={`Toggle sources (${citations.length} cited)`}
      >
        <div className="citations-toggle-label">
          <BookOpen size={15} className="citation-icon" />
          <span>
            <strong>Sources</strong> ({citations.length} cited source{citations.length > 1 ? 's' : ''})
          </span>
        </div>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isExpanded && (
        <div className="citations-list">
          {citations.map((item, idx) => {
            const isWebSource = item.source_type === 'official_website' || item.source_type === 'OFFICIAL_WEBSITE' || !!item.source_url;
            const docTitle = item.title || (isWebSource ? 'Official College Website' : 'Official College Document');
            const pageNum = item.page_number;
            const sourcePages = item.source_pages && item.source_pages.length > 0 ? item.source_pages : (pageNum ? [pageNum] : []);
            const pageStr = !isWebSource && sourcePages.length > 0
              ? (sourcePages.length === 1 ? `Page ${sourcePages[0]}` : `Pages ${sourcePages.join(', ')}`)
              : null;
            const deptStr = item.department || null;
            const yearStr = item.academic_year || null;
            const docTypeStr = item.document_type || null;

            return (
              <div key={idx} className={`citation-card ${isWebSource ? 'web-citation' : ''}`}>
                <div className="citation-card-header">
                  {isWebSource ? (
                    <Globe size={14} className="citation-doc-icon text-indigo" />
                  ) : (
                    <FileText size={14} className="citation-doc-icon" />
                  )}
                  <span className="citation-title">{docTitle}</span>
                  {isWebSource && <span className="citation-web-badge">Official College Website</span>}
                  {pageStr && <span className="citation-page-badge">{pageStr}</span>}
                </div>

                <div className="citation-meta-tags">
                  {docTypeStr && <span className="meta-tag">{docTypeStr}</span>}
                  {deptStr && <span className="meta-tag">{deptStr}</span>}
                  {yearStr && <span className="meta-tag">{yearStr}</span>}
                  {item.source_url && (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="citation-url-link"
                    >
                      View Source <ExternalLink size={10} />
                    </a>
                  )}
                </div>

                {item.snippet && (
                  <blockquote className="citation-snippet">
                    <Bookmark size={12} className="snippet-icon" />
                    <span>"{item.snippet}"</span>
                  </blockquote>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
