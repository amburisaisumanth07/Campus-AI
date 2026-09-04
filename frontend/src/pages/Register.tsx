import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registerApi, loginApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  UserPlus,
  AlertCircle,
  Loader2,
  Sparkles,
  Search,
  BookOpen,
  GraduationCap,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';

export const Register: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // 1. Register student account
      await registerApi(name, email, password);
      // 2. Automatically log in upon successful registration
      const { access_token } = await loginApi(email, password);
      await login(access_token);

      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      {/* Left Column: CampusAI Hero Branding */}
      <div className="auth-info-panel">
        <div className="auth-info-content">
          <div className="auth-info-badge">
            <Sparkles size={14} />
            <span>Join CampusAI Platform</span>
          </div>

          <h1 className="auth-info-title">
            Unlock Instant <span className="text-gradient">College Knowledge</span>
          </h1>

          <p className="auth-info-description">
            Create your student account to access AI-powered query resolution, exam notifications,
            academic calendars, and personalized student support.
          </p>

          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="feature-icon-circle blue">
                <Search size={18} />
              </div>
              <div className="feature-text">
                <strong>24/7 AI Academic Assistant</strong>
                <span>Instant help with grading schemes, syllabus, hall tickets, and regulations.</span>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="feature-icon-circle purple">
                <GraduationCap size={18} />
              </div>
              <div className="feature-text">
                <strong>Personalized Student Experience</strong>
                <span>Bookmark conversations, track announcements, and explore degree tracks.</span>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="feature-icon-circle emerald">
                <CheckCircle2 size={18} />
              </div>
              <div className="feature-text">
                <strong>Instant Activation</strong>
                <span>Immediate portal access upon registration with verified college email.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-info-footer">
          <div className="auth-stat-pill">
            <BookOpen size={14} />
            <span>MITS Student Network</span>
          </div>
        </div>
      </div>

      {/* Right Column: Register Card */}
      <div className="auth-card-panel">
        <div className="auth-card-header">
          <div className="auth-card-icon-wrap">
            <UserPlus size={26} className="auth-card-icon" />
          </div>
          <h2 className="auth-card-title">Create Student Account</h2>
          <p className="auth-card-subtitle">Register to get instant access to CampusAI</p>
        </div>

        {error && (
          <div className="auth-error-banner" role="alert">
            <AlertCircle size={18} className="error-icon" />
            <div className="error-text-content">
              <strong>Registration Error</strong>
              <span>{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form-body">
          <div className="auth-form-group">
            <label htmlFor="register-name">Full Name</label>
            <input
              id="register-name"
              type="text"
              required
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Doe"
              className="auth-input"
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="register-email">College Email Address</label>
            <input
              id="register-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="student@college.edu"
              className="auth-input"
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="register-password">Password (8+ characters)</label>
            <input
              id="register-password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="auth-input"
            />
          </div>

          <button
            type="submit"
            className="auth-submit-button"
            disabled={isSubmitting}
            data-testid="create-account-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="auth-link">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
