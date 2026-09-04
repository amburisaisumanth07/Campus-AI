import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, ArrowRight, Search } from 'lucide-react';
import type { User } from '../../types/api';

interface StudentWelcomeHeroProps {
  user: User | null;
}

const SAMPLE_PROMPTS = [
  { label: 'Grading system & SGPA calculation', query: 'What is the grading system and how is SGPA calculated?' },
  { label: 'Minimum attendance requirement', query: 'What is the minimum attendance requirement for semester exams?' },
  { label: 'End-semester exam rules', query: 'What are the end-semester exam rules?' },
  { label: 'Placement eligibility criteria', query: 'What are the placement eligibility criteria and company requirements?' },
  { label: 'College overview & history', query: 'Give me an overview of the college, its establishment, and history.' },
];

export const StudentWelcomeHero: React.FC<StudentWelcomeHeroProps> = ({ user }) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const handleAsk = (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const query = customQuery !== undefined ? customQuery : searchQuery;
    navigate('/chat', { state: { initialQuery: query } });
  };

  const studentName = user?.name || 'Student';

  return (
    <div className="student-hero-section">
      {/* Welcome Header */}
      <div className="student-welcome-header">
        <div className="welcome-text-group">
          <h2>Welcome back, {studentName} 👋</h2>
          <p>Your intelligent college information hub.</p>
        </div>
        <div className="student-meta-badge">
          <span className="dot" />
          <span>{user?.role || 'STUDENT'}</span>
          <span style={{ color: 'var(--border-color)' }}>•</span>
          <span style={{ color: '#94a3b8' }}>{user?.email}</span>
        </div>
      </div>

      {/* Ask CampusAI Primary Feature Card */}
      <div className="ask-campusai-hero" style={{ marginTop: '1.5rem' }}>
        <div className="hero-header-badge">
          <Sparkles size={14} />
          <span>AI Knowledge Assistant</span>
        </div>

        <div className="hero-content">
          <h3>Ask CampusAI</h3>
          <p>
            Ask anything about your college, academics, examinations, departments, events, placements, and more.
          </p>
        </div>

        <form className="hero-search-form" onSubmit={(e) => handleAsk(e)}>
          <div className="hero-search-input-wrapper">
            <Search className="search-icon" size={18} />
            <input
              type="text"
              className="hero-search-input"
              placeholder="e.g. What are the rules for semester attendance and hall tickets?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button type="submit" className="hero-submit-btn" data-testid="hero-submit-btn">
            Ask CampusAI <ArrowRight size={18} />
          </button>
        </form>

        <div className="hero-prompt-suggestions">
          <span className="suggestions-label">Try asking:</span>
          {SAMPLE_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              className="prompt-chip"
              onClick={() => handleAsk(undefined, prompt.query)}
            >
              <span>{prompt.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
