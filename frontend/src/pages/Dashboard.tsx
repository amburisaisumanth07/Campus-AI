import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  Search,
  Sparkles,
  ArrowRight,
  BookOpen,
  GraduationCap,
  FileText,
  Briefcase,
} from 'lucide-react';
import { canUploadDocuments } from '../utils/permissions';

export const Dashboard: React.FC = () => {
  const { user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const isStaff = !isAuthLoading && canUploadDocuments(user);
  const firstName = user?.name?.split(' ')[0] || user?.name || 'Student';

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate('/chat', { state: { initialMessage: searchQuery } });
    }
  };

  const handleSuggestionClick = (question: string) => {
    navigate('/chat', { state: { initialMessage: question } });
  };

  return (
    <div className="dashboard-container" data-testid="student-dashboard">
      {/* Admin Knowledge Banner */}
      {isStaff && (
        <div className="admin-knowledge-banner" data-testid="staff-banner">
          <div className="banner-content">
            <Shield size={24} className="banner-icon" />
            <div>
              <h3>Staff Knowledge Management</h3>
              <p>You have authorized staff privileges (ADMIN) to upload and process institutional documents.</p>
            </div>
          </div>
          <button 
            className="banner-btn" 
            onClick={() => navigate('/admin/sources')}
            data-testid="admin-manage-btn"
          >
            Manage Knowledge Sources <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* Welcome Header */}
      <div className="dashboard-welcome-area" data-testid="dashboard-welcome">
        <div className="welcome-text">
          <h2>Welcome back, {firstName} 👋</h2>
          <p>Your intelligent college information hub.</p>
        </div>
        {user && (
          <div className="welcome-user-info">
            <span className={`user-role-badge ${user.role.toLowerCase()}`}>
              {user.role}
            </span>
            <span className="user-email">• {user.email}</span>
          </div>
        )}
      </div>

      {/* Main AI Assistant Card */}
      <div className="ai-assistant-card" data-testid="hero-card">
        <div className="ai-card-header">
          <div className="ai-badge">
            <Sparkles size={14} />
            <span>AI KNOWLEDGE ASSISTANT</span>
          </div>
          <h3>Ask CampusAI</h3>
          <p>
            Ask anything about your college, academics, examinations,
            departments, events, placements, and more.
          </p>
        </div>

        <form className="search-action-row" onSubmit={handleSearch}>
          <div className="search-input-wrapper">
            <Search size={20} className="search-icon" />
            <input
              type="text"
              placeholder="e.g. What are the rules for semester attendance and hall tickets?"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="main-search-input"
            />
          </div>
          <button
            type="submit"
            className="primary-button ask-btn"
            data-testid="ask-campusai-btn"
          >
            Ask CampusAI <ArrowRight size={18} />
          </button>
        </form>

        <div className="suggestion-pills-container">
          <button 
            className="suggestion-pill"
            onClick={() => handleSuggestionClick('Grading system & SGPA calculation')}
          >
            Grading system & SGPA calculation
          </button>
          <button 
            className="suggestion-pill"
            onClick={() => handleSuggestionClick('Minimum attendance requirement')}
          >
            Minimum attendance requirement
          </button>
          <button 
            className="suggestion-pill"
            onClick={() => handleSuggestionClick('End-semester exam rules')}
          >
            End-semester exam rules
          </button>
          <button 
            className="suggestion-pill"
            onClick={() => handleSuggestionClick('Placement eligibility criteria')}
          >
            Placement eligibility criteria
          </button>
        </div>
      </div>

      {/* Institutional Knowledge Summary Grid */}
      <div className="dashboard-summary-grid">
        <div
          className="summary-card"
          onClick={() => handleSuggestionClick('What are the academic regulations, grading system and SGPA calculation rules?')}
          role="button"
          tabIndex={0}
        >
          <div className="summary-card-icon-wrap blue">
            <BookOpen size={22} />
          </div>
          <div className="summary-card-content">
            <h4>Academic & Grading Rules</h4>
            <p>R20/R25 regulations, SGPA & CGPA evaluation scales, attendance (75%), and promotion rules.</p>
            <span className="card-action-link">
              Ask Regulations <ArrowRight size={14} />
            </span>
          </div>
        </div>

        <div
          className="summary-card"
          onClick={() => navigate('/departments')}
          role="button"
          tabIndex={0}
        >
          <div className="summary-card-icon-wrap purple">
            <GraduationCap size={22} />
          </div>
          <div className="summary-card-content">
            <h4>Departments & Faculty</h4>
            <p>Explore all 13 canonical academic departments, official HODs, and 301 verified active faculty rosters.</p>
            <span className="card-action-link">
              View Directory <ArrowRight size={14} />
            </span>
          </div>
        </div>

        <div
          className="summary-card"
          onClick={() => navigate('/examinations')}
          role="button"
          tabIndex={0}
        >
          <div className="summary-card-icon-wrap emerald">
            <FileText size={22} />
          </div>
          <div className="summary-card-content">
            <h4>Examination Policies</h4>
            <p>SEE & CIE weightage, hall ticket criteria, recounting & revaluation procedures, and exam guidelines.</p>
            <span className="card-action-link">
              View Policies <ArrowRight size={14} />
            </span>
          </div>
        </div>

        <div
          className="summary-card"
          onClick={() => navigate('/placements')}
          role="button"
          tabIndex={0}
        >
          <div className="summary-card-icon-wrap amber">
            <Briefcase size={22} />
          </div>
          <div className="summary-card-content">
            <h4>Placement & Career Cell</h4>
            <p>Placement statistics, verified recruiting partners, training drives, and campus recruitment records.</p>
            <span className="card-action-link">
              Explore Placements <ArrowRight size={14} />
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
