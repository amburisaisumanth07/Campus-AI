import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationList } from './CitationList';

describe('CitationList Component', () => {
  it('renders nothing when citations list is empty or null', () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders citations toggle and displays official website citation badges and source links', () => {
    const mockCitations = [
      {
        title: 'Academic Regulations',
        page_number: 3,
        source_pages: [3],
        department: 'CSE',
        academic_year: '2025-2026',
        snippet: 'Attendance must be at least 75%.',
        source_type: 'OFFICIAL_WEBSITE',
        source_url: 'https://college.edu/regulations.html',
      },
      {
        title: 'Manual Student Guide',
        page_number: 1,
        source_pages: [1],
        department: 'General',
        snippet: 'Hostel timings are 9:00 PM.',
        source_type: 'MANUAL_UPLOAD',
      },
    ];

    render(<CitationList citations={mockCitations} />);

    // Toggle button should show count
    const toggleBtn = screen.getByRole('button', { name: /Toggle sources \(2 cited\)/i });
    expect(toggleBtn).toBeInTheDocument();
    expect(screen.getByText(/2 cited sources/i)).toBeInTheDocument();

    // Expand citations
    fireEvent.click(toggleBtn);

    expect(screen.getByText('Academic Regulations')).toBeInTheDocument();
    expect(screen.getByText('Official College Website')).toBeInTheDocument();
    expect(screen.getByText(/View Source/i)).toHaveAttribute('href', 'https://college.edu/regulations.html');

    expect(screen.getByText('Manual Student Guide')).toBeInTheDocument();
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });
});
