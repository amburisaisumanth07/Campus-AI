import React from 'react';
import { Outlet, Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { BookOpen, Sun, Moon, Monitor, ShieldCheck } from 'lucide-react';

export const AuthLayout: React.FC = () => {
  const { isAuthenticated, user, isLoading } = useAuth();
  const { theme, setTheme } = useTheme();

  // If already authenticated, redirect to appropriate destination
  if (!isLoading && isAuthenticated && user) {
    return <Navigate to={user.role === 'ADMIN' ? '/admin' : '/dashboard'} replace />;
  }

  return (
    <div className="auth-layout">
      {/* Top Header Bar */}
      <header className="auth-top-bar">
        <Link to="/login" className="auth-brand-logo">
          <div className="auth-brand-icon-box">
            <BookOpen size={22} className="auth-brand-icon" />
          </div>
          <div className="auth-brand-text">
            <span className="auth-brand-name">CampusAI</span>
            <span className="auth-brand-tagline">College Knowledge Platform</span>
          </div>
        </Link>

        {/* Global Theme Switcher accessible before login */}
        <div className="auth-theme-switcher" role="radiogroup" aria-label="Theme selection">
          <button
            type="button"
            className={`auth-theme-btn ${theme === 'light' ? 'active' : ''}`}
            onClick={() => setTheme('light')}
            title="Light Theme"
            aria-label="Light Theme"
          >
            <Sun size={15} />
            <span className="theme-btn-text">Light</span>
          </button>
          <button
            type="button"
            className={`auth-theme-btn ${theme === 'dark' ? 'active' : ''}`}
            onClick={() => setTheme('dark')}
            title="Dark Theme"
            aria-label="Dark Theme"
          >
            <Moon size={15} />
            <span className="theme-btn-text">Dark</span>
          </button>
          <button
            type="button"
            className={`auth-theme-btn ${theme === 'system' ? 'active' : ''}`}
            onClick={() => setTheme('system')}
            title="System Preference"
            aria-label="System Preference"
          >
            <Monitor size={15} />
            <span className="theme-btn-text">System</span>
          </button>
        </div>
      </header>

      {/* Main Auth Content Area */}
      <main className="auth-main">
        <Outlet />
      </main>

      {/* Subtle Platform Footer */}
      <footer className="auth-footer-bar">
        <div className="auth-footer-content">
          <span className="auth-footer-item">
            <ShieldCheck size={14} className="text-emerald" /> Official MITS Knowledge Grounding
          </span>
          <span className="auth-footer-dot">•</span>
          <span className="auth-footer-item">Autonomous College Intelligence System</span>
        </div>
      </footer>
    </div>
  );
};
