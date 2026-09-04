import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DocumentUploadForm } from './DocumentUploadForm';
import * as documentsApi from '../services/documents';

vi.mock('../services/documents');

describe('DocumentUploadForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders upload form fields', () => {
    render(<DocumentUploadForm onUploadSuccess={() => {}} />);
    expect(screen.getByTestId('file-input')).toBeInTheDocument();
    expect(screen.getByTestId('title-input')).toBeInTheDocument();
    expect(screen.getByTestId('type-select')).toBeInTheDocument();
    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
  });

  it('shows error when submitting without file', async () => {
    render(<DocumentUploadForm onUploadSuccess={() => {}} />);
    fireEvent.click(screen.getByTestId('submit-button'));
    await waitFor(() => {
      expect(screen.getByTestId('upload-error')).toHaveTextContent('Please select a PDF file');
    });
  });

  it('shows error when non-PDF file is selected', async () => {
    render(<DocumentUploadForm onUploadSuccess={() => {}} />);
    const file = new File(['text'], 'test.txt', { type: 'text/plain' });
    const fileInput = screen.getByTestId('file-input');
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByTestId('upload-error')).toHaveTextContent('Only PDF files are allowed');
    });
  });

  it('submits form successfully with valid PDF', async () => {
    const mockUpload = vi.spyOn(documentsApi, 'uploadDocumentApi').mockResolvedValue({
      id: 1,
      title: 'Test Regulation',
      filename: 'regulation.pdf',
      document_type: 'regulation',
      department: 'CSE',
      academic_year: '2025-2026',
      status: 'READY',
      uploaded_by_id: 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      active_version: null,
      versions: [],
      page_count: 5,
    });

    const onSuccess = vi.fn();
    render(<DocumentUploadForm onUploadSuccess={onSuccess} />);

    const pdfFile = new File(['%PDF-1.4 mock content'], 'regulation.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByTestId('file-input'), { target: { files: [pdfFile] } });
    fireEvent.change(screen.getByTestId('title-input'), { target: { value: 'Test Regulation' } });

    fireEvent.click(screen.getByTestId('submit-button'));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalled();
      expect(screen.getByTestId('upload-success')).toBeInTheDocument();
      expect(onSuccess).toHaveBeenCalled();
    });
  });
});
