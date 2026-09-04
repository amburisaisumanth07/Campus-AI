import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginApi } from '../services/api';
import {
  LogIn,
  AlertCircle,
  Loader2,
  Sparkles,
  Search,
  BookOpen,
  ShieldCheck,
  Building2,
  ArrowRight,
} from 'lucide-react';

export const Login: React.FC = () => {
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
      const { access_token } = await loginApi(email, password);
      const user = await login(access_token);

      if (user.role === 'ADMIN') {
        navigate('/admin');
      } else {
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      {/* Left Column: CampusAI Hero Branding & Feature Information */}
      <div className="auth-info-panel">
        <div className="auth-info-content">
          <div className="auth-info-badge">
            <Sparkles size={14} />
            <span>Next-Generation College Intelligence</span>
          </div>

          <h1 className="auth-info-title">
            Your Unified <span className="text-gradient">CampusAI</span> Portal
          </h1>

          <p className="auth-info-description">
            Instant semantic search across official college syllabus, academic calendars,
            examination guidelines, department notices, and career placements.
          </p>

          <div className="auth-features-list">
            <div className="auth-feature-item">
              <div className="feature-icon-circle blue">
                <Search size={18} />
              </div>
              <div className="feature-text">
                <strong>Smart Document-Grounded RAG</strong>
                <span>Direct answers cited from verified institutional PDFs and portals.</span>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="feature-icon-circle purple">
                <Building2 size={18} />
              </div>
              <div className="feature-text">
                <strong>Academic & Department Hub</strong>
                <span>All faculty, course curricula, and regulations in one place.</span>
              </div>
            </div>

            <div className="auth-feature-item">
              <div className="feature-icon-circle emerald">
                <ShieldCheck size={18} />
              </div>
              <div className="feature-text">
                <strong>Official & High-Trust Data</strong>
                <span>Governed by MITS institutional knowledge sources with source verification.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="auth-info-footer">
          <div className="auth-stat-pill">
            <BookOpen size={14} />
            <span>MITS Autonomous Portal</span>
          </div>
        </div>
      </div>

      {/* Right Column: Sign In Card */}
      <div className="auth-card-panel">
        <div className="auth-card-header">
          <div className="auth-card-icon-wrap">
            <LogIn size={26} className="auth-card-icon" />
          </div>
          <h2 className="auth-card-title">Sign In to CampusAI</h2>
          <p className="auth-card-subtitle">Access your college portal and AI assistant</p>
        </div>

        {error && (
          <div className="auth-error-banner" role="alert">
            <AlertCircle size={18} className="error-icon" />
            <div className="error-text-content">
              <strong>Authentication Error</strong>
              <span>{error}</span>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form-body">
          <div className="auth-form-group">
            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
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
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              required
              autoComplete="current-password"
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
            data-testid="sign-in-btn"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="spin" />
                <span>Signing In...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className="auth-card-footer">
          <p>
            Don't have an account?{' '}
            <Link to="/register" className="auth-link">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
