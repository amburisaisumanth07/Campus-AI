import React, { useState } from 'react';
import type { DocumentType } from '../types/api';
import { uploadDocumentApi } from '../services/documents';

interface DocumentUploadFormProps {
  onUploadSuccess: () => void;
}

const DOCUMENT_TYPES: { value: DocumentType; label: string }[] = [
  { value: 'regulation', label: 'Regulation' },
  { value: 'academic_calendar', label: 'Academic Calendar' },
  { value: 'examination', label: 'Examination' },
  { value: 'attendance', label: 'Attendance' },
  { value: 'placement', label: 'Placement' },
  { value: 'scholarship', label: 'Scholarship' },
  { value: 'course', label: 'Course' },
  { value: 'notice', label: 'Notice' },
  { value: 'department_document', label: 'Department Document' },
  { value: 'other', label: 'Other' },
];

export const DocumentUploadForm: React.FC<DocumentUploadFormProps> = ({ onUploadSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [documentType, setDocumentType] = useState<DocumentType>('regulation');
  const [department, setDepartment] = useState('');
  const [academicYear, setAcademicYear] = useState('');
  const [version, setVersion] = useState('1.0');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type !== 'application/pdf') {
        setError('Only PDF files are allowed.');
        setFile(null);
        return;
      }
      setError(null);
      setFile(selectedFile);
      if (!title) {
        // Auto-fill title from filename without extension
        const cleanName = selectedFile.name.replace(/\.[^/.]+$/, '');
        setTitle(cleanName);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file to upload.');
      return;
    }
    if (!title.trim()) {
      setError('Please enter a document title.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title.trim());
    formData.append('document_type', documentType);
    if (department.trim()) formData.append('department', department.trim());
    if (academicYear.trim()) formData.append('academic_year', academicYear.trim());
    if (version.trim()) formData.append('version', version.trim());

    try {
      await uploadDocumentApi(formData);
      setSuccess('Document uploaded successfully and queued for processing!');
      setFile(null);
      setTitle('');
      setDepartment('');
      setAcademicYear('');
      setVersion('1.0');
      onUploadSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to upload document');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: '#ffffff', borderRadius: '8px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '24px' }}>
      <h3 style={{ marginTop: 0, marginBottom: '16px', color: '#1e293b' }}>Upload New Document</h3>

      {error && (
        <div data-testid="upload-error" style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
          {error}
        </div>
      )}

      {success && (
        <div data-testid="upload-success" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div style={{ gridColumn: 'span 2' }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            PDF File *
          </label>
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            data-testid="file-input"
            style={{ width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            Document Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. B.Tech Academic Regulations 2025"
            data-testid="title-input"
            style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            Document Type *
          </label>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value as DocumentType)}
            data-testid="type-select"
            style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', background: '#fff' }}
          >
            {DOCUMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            Department (Optional)
          </label>
          <input
            type="text"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            placeholder="e.g. Computer Science"
            data-testid="department-input"
            style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            Academic Year (Optional)
          </label>
          <input
            type="text"
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            placeholder="e.g. 2025-2026"
            data-testid="year-input"
            style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '6px', color: '#334155' }}>
            Version
          </label>
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="1.0"
            data-testid="version-input"
            style={{ width: '100%', padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
          />
        </div>

        <div style={{ gridColumn: 'span 2', display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
          <button
            type="submit"
            disabled={loading}
            data-testid="submit-button"
            style={{
              background: loading ? '#94a3b8' : '#2563eb',
              color: '#fff',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </div>
      </form>
    </div>
  );
};
