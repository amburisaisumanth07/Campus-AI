import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  Search,
  Sparkles,
  ArrowRight,
  Mic,
  CalendarCheck,
} from 'lucide-react';
import { canUploadDocuments } from '../utils/permissions';
import { VoiceInputButton } from '../components/voice/VoiceInputButton';
import { AttendanceTrackerModal } from '../components/attendance/AttendanceTrackerModal';

export const Dashboard: React.FC = () => {
  const { user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false);
  const [isVoiceRecordingActive, setIsVoiceRecordingActive] = useState(false);

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

  const handleVoiceTranscript = (transcriptText: string) => {
    setSearchQuery(transcriptText);
    // Automatically submit to chat when speech recognized or populate input
    if (transcriptText.trim()) {
      navigate('/chat', { state: { initialMessage: transcriptText.trim() } });
    }
  };

  return (
    <div className="dashboard-container modern-clean-dashboard" data-testid="student-dashboard">
      {/* Admin Knowledge Management Banner */}
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

      {/* Main Spacious & Focused Hero Header */}
      <div className="dashboard-header-hero" data-testid="dashboard-welcome">
        <div className="platform-brand-badge">
          <Sparkles size={16} className="sparkle-icon" />
          <span>OFFICIAL MITS KNOWLEDGE HUB</span>
        </div>
        <h1 className="hero-platform-title">CampusAI</h1>
        <p className="hero-platform-subtitle">College Knowledge Assistant</p>
        {user && (
          <p className="hero-user-greeting">
            Welcome back, <strong>{firstName}</strong> ({user.role})
          </p>
        )}
      </div>

      {/* Main Clean Ask CampusAI Search Box */}
      <div className="dashboard-search-card" data-testid="hero-card">
        <form className="dashboard-ask-form" onSubmit={handleSearch}>
          <div className="search-input-field-wrapper">
            <Search size={22} className="search-field-icon" />
            <input
              type="text"
              placeholder="Ask CampusAI anything..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="dashboard-search-input"
              data-testid="ask-campusai-input"
              autoFocus
            />
            {/* Inline Microphone Button */}
            <VoiceInputButton
              onTranscript={handleVoiceTranscript}
              variant="inline"
              className="search-mic-button"
            />
          </div>
          <button
            type="submit"
            className="primary-button ask-submit-button"
            data-testid="ask-campusai-btn"
          >
            <span>Ask</span>
            <ArrowRight size={18} />
          </button>
        </form>

        {/* Focused Curated Examples */}
        <div className="dashboard-examples-section">
          <span className="examples-label">Examples:</span>
          <div className="examples-pills-row">
            <button
              type="button"
              className="example-pill-btn"
              onClick={() => handleSuggestionClick('Who is the current HOD of CSE?')}
            >
              "Who is the current HOD of CSE?"
            </button>
            <button
              type="button"
              className="example-pill-btn"
              onClick={() => handleSuggestionClick('What is the minimum attendance requirement?')}
            >
              "What is the minimum attendance requirement?"
            </button>
            <button
              type="button"
              className="example-pill-btn"
              onClick={() => handleSuggestionClick('When are the semester examinations?')}
            >
              "When are the semester examinations?"
            </button>
            <button
              type="button"
              className="example-pill-btn"
              onClick={() => handleSuggestionClick('Show me the CSE faculty.')}
            >
              "Show me the CSE faculty."
            </button>
          </div>
        </div>
      </div>

      {/* Two Attractive Feature Cards: Voice + Official Attendance Tracker */}
      <div className="dashboard-featured-actions-grid" data-testid="dashboard-featured-actions">
        {/* Feature 1: Ask with Voice */}
        <div
          className="featured-action-card voice-action-card"
          onClick={() => setIsVoiceRecordingActive(true)}
          role="button"
          tabIndex={0}
          data-testid="ask-with-voice-card"
        >
          <div className="featured-card-icon-bubble voice-bubble">
            <Mic size={26} />
          </div>
          <div className="featured-card-content">
            <h3>Ask with Voice</h3>
            <p>Speak your question hands-free and get instant verified answers from CampusAI.</p>
            <span className="featured-card-cta">
              🎙 Start Voice Search <ArrowRight size={14} />
            </span>
          </div>
        </div>

        {/* Feature 2: Official Attendance Tracker */}
        <div
          className="featured-action-card attendance-action-card"
          onClick={() => setIsAttendanceModalOpen(true)}
          role="button"
          tabIndex={0}
          data-testid="attendance-tracker-card"
        >
          <div className="featured-card-icon-bubble attendance-bubble">
            <CalendarCheck size={26} />
          </div>
          <div className="featured-card-content">
            <h3>Attendance Tracker</h3>
            <p>Check your verified attendance directly from the official MITS student portal.</p>
            <span className="featured-card-cta">
              📊 View Attendance <ArrowRight size={14} />
            </span>
          </div>
        </div>
      </div>

      {/* Voice Trigger from Featured Card */}
      {isVoiceRecordingActive && (
        <VoiceInputButton
          onTranscript={(text) => {
            setIsVoiceRecordingActive(false);
            handleVoiceTranscript(text);
          }}
          variant="inline"
          isRecordingExternal={true}
          onRecordingStateChange={(rec) => {
            if (!rec) setIsVoiceRecordingActive(false);
          }}
        />
      )}

      {/* Official Attendance Tracker Modal */}
      <AttendanceTrackerModal
        isOpen={isAttendanceModalOpen}
        onClose={() => setIsAttendanceModalOpen(false)}
      />
    </div>
  );
};
