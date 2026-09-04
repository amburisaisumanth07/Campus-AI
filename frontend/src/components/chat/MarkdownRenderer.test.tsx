import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MarkdownRenderer } from './MarkdownRenderer';

describe('MarkdownRenderer Component', () => {
  it('renders headings correctly', () => {
    const markdown = `# Main Title\n## Section Subtitle\n### Sub-sub Heading`;
    render(<MarkdownRenderer content={markdown} />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Main Title');
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Section Subtitle');
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Sub-sub Heading');
  });

  it('renders bold, italic, and inline code formatting', () => {
    const markdown = `Here is **bold text**, *italic text*, and \`inline code\`.`;
    const { container } = render(<MarkdownRenderer content={markdown} />);

    expect(container.querySelector('strong')).toHaveTextContent('bold text');
    expect(container.querySelector('em')).toHaveTextContent('italic text');
    expect(container.querySelector('code')).toHaveTextContent('inline code');
  });

  it('renders unordered and ordered lists', () => {
    const markdown = `* Item 1\n* Item 2\n\n1. Step A\n2. Step B`;
    const { container } = render(<MarkdownRenderer content={markdown} />);

    const uls = container.querySelectorAll('ul');
    expect(uls.length).toBe(1);
    expect(uls[0].children.length).toBe(2);

    const ols = container.querySelectorAll('ol');
    expect(ols.length).toBe(1);
    expect(ols[0].children.length).toBe(2);
  });

  it('renders markdown tables properly', () => {
    const tableMd = `| Marks Range | Letter Grade | Grade Point |\n| --- | --- | --- |\n| 90 & above | S | 10 |\n| 80 - 89 | A | 9 |`;
    const { container } = render(<MarkdownRenderer content={tableMd} />);

    expect(container.querySelector('table')).toBeInTheDocument();
    expect(container.querySelectorAll('th').length).toBe(3);
    expect(container.querySelectorAll('tbody tr').length).toBe(2);
  });

  it('renders complex multi-paragraph grounded answer completely without truncation', () => {
    const longAnswer = `# Attendance and Exam Regulations\n\n## 1. Minimum Attendance\nA student must have at least 75% aggregate attendance across all courses to be eligible to write the end semester examinations.\n\n## 2. Condonation\nCondonation of shortage of attendance between 65% and 75% may be granted by the Academic Council on medical grounds.\n\n## 3. Grading Scale\n| Grade | Point |\n| --- | --- |\n| S | 10 |\n| A | 9 |\n| B | 8 |`;

    const { container } = render(<MarkdownRenderer content={longAnswer} />);

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Attendance and Exam Regulations');
    expect(screen.getByRole('heading', { level: 2, name: /1\. Minimum Attendance/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /2\. Condonation/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /3\. Grading Scale/i })).toBeInTheDocument();
    expect(container.querySelector('table')).toBeInTheDocument();
  });
});
