import React from 'react';
import type { DocumentItem, DocumentStatus } from '../types/api';

interface DocumentListProps {
  documents: DocumentItem[];
  loading: boolean;
  onDelete: (id: number) => void;
  onRefresh: () => void;
  canDelete?: boolean;
}

const statusBadges: Record<DocumentStatus, { bg: string; color: string; label: string }> = {
  UPLOADED: { bg: '#e0f2fe', color: '#0369a1', label: 'Uploaded' },
  PROCESSING: { bg: '#fef3c7', color: '#b45309', label: 'Processing...' },
  READY: { bg: '#dcfce7', color: '#15803d', label: 'Ready' },
  FAILED: { bg: '#fee2e2', color: '#b91c1c', label: 'Failed' },
};

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  loading,
  onDelete,
  onRefresh,
  canDelete = true,
}) => {
  return (
    <div style={{ background: '#ffffff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: '#1e293b' }}>Document Library ({documents.length})</h3>
        <button
          onClick={onRefresh}
          style={{
            background: 'transparent',
            border: '1px solid #cbd5e1',
            borderRadius: '6px',
            padding: '6px 12px',
            color: '#475569',
            cursor: 'pointer',
          }}
        >
          Refresh List
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '24px', textAlign: 'center', color: '#64748b' }}>Loading documents...</div>
      ) : documents.length === 0 ? (
        <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', background: '#f8fafc', borderRadius: '6px' }}>
          No documents uploaded yet.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 8px' }}>Title & Type</th>
                <th style={{ padding: '12px 8px' }}>Department</th>
                <th style={{ padding: '12px 8px' }}>Academic Year</th>
                <th style={{ padding: '12px 8px' }}>Pages</th>
                <th style={{ padding: '12px 8px' }}>Status</th>
                {canDelete && <th style={{ padding: '12px 8px', textAlign: 'right' }}>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const badge = statusBadges[doc.status] || { bg: '#f1f5f9', color: '#475569', label: doc.status };
                const pages = doc.active_version?.page_count;

                return (
                  <tr key={doc.id} style={{ borderBottom: '1px solid #f1f5f9' }} data-testid={`doc-row-${doc.id}`}>
                    <td style={{ padding: '12px 8px' }}>
                      <div style={{ fontWeight: 600, color: '#1e293b' }}>{doc.title}</div>
                      <div style={{ fontSize: '12px', color: '#64748b' }}>
                        {doc.filename} • <span style={{ textTransform: 'capitalize' }}>{doc.document_type.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 8px', color: '#334155' }}>{doc.department || '—'}</td>
                    <td style={{ padding: '12px 8px', color: '#334155' }}>{doc.academic_year || '—'}</td>
                    <td style={{ padding: '12px 8px', color: '#334155' }}>{pages !== null && pages !== undefined ? `${pages} pgs` : '—'}</td>
                    <td style={{ padding: '12px 8px' }}>
                      <span
                        data-testid={`status-badge-${doc.id}`}
                        style={{
                          background: badge.bg,
                          color: badge.color,
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '12px',
                          fontWeight: 600,
                        }}
                      >
                        {badge.label}
                      </span>
                    </td>
                    {canDelete && (
                      <td style={{ padding: '12px 8px', textAlign: 'right' }}>
                        <button
                          onClick={() => {
                            if (window.confirm(`Are you sure you want to delete "${doc.title}"?`)) {
                              onDelete(doc.id);
                            }
                          }}
                          data-testid={`delete-btn-${doc.id}`}
                          style={{
                            background: '#fef2f2',
                            color: '#dc2626',
                            border: '1px solid #fecaca',
                            borderRadius: '4px',
                            padding: '4px 8px',
                            fontSize: '12px',
                            cursor: 'pointer',
                          }}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
