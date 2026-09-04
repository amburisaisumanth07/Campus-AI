import React, { useState, useEffect, useCallback } from 'react';
import { DocumentUploadForm } from '../components/DocumentUploadForm';
import { DocumentList } from '../components/DocumentList';
import type { DocumentItem } from '../types/api';
import { listDocumentsApi, deleteDocumentApi } from '../services/documents';

export const Admin: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listDocumentsApi();
      setDocuments(data.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleDelete = async (id: number) => {
    try {
      await deleteDocumentApi(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err: any) {
      alert(err.message || 'Failed to delete document');
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '0 0 8px 0', color: '#0f172a' }}>
          Admin Document Management
        </h2>
        <p style={{ margin: 0, color: '#64748b' }}>
          Upload, manage, and process college PDF documents for the campus AI knowledge base.
        </p>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      <DocumentUploadForm onUploadSuccess={fetchDocuments} />

      <DocumentList
        documents={documents}
        loading={loading}
        onDelete={handleDelete}
        onRefresh={fetchDocuments}
      />
    </div>
  );
};
