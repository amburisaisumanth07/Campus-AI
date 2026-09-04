import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useNavigate } from 'react-router-dom';
import {
  Palette,
  Bell,
  Shield,
  Info,
  LogOut,
  ChevronRight,
  Sun,
  Moon,
  Monitor,
  Check,
} from 'lucide-react';

const NOTIFICATIONS_KEY = 'campusai-notifications';

export const Settings: React.FC = () => {
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState<boolean>(() => {
    const stored = localStorage.getItem(NOTIFICATIONS_KEY);
    return stored !== null ? stored === 'true' : true;
  });

  const [showSignOutConfirm, setShowSignOutConfirm] = useState(false);

  useEffect(() => {
    localStorage.setItem(NOTIFICATIONS_KEY, String(notifications));
  }, [notifications]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="settings-page" data-testid="settings-page">
      <div className="settings-header" data-testid="settings-header">
        <h2>Settings</h2>
      </div>

      <div className="settings-content">
        {/* Appearance Section */}
        <section className="settings-section" data-testid="settings-appearance">
          <div className="settings-section-header">
            <Palette size={18} className="settings-section-icon" />
            <h3 className="settings-section-title">Appearance</h3>
          </div>
          <div className="settings-card">
            <div className="settings-row">
              <div className="settings-row-label">
                <span className="settings-row-title">Theme</span>
                <span className="settings-row-desc">Choose how CampusAI appears across the entire application.</span>
              </div>
              <div className="theme-selector" data-testid="theme-selector">
                <button
                  className={`theme-option ${theme === 'light' ? 'active' : ''}`}
                  onClick={() => setTheme('light')}
                  data-testid="theme-option-light"
                >
                  <Sun size={16} />
                  <span>Light</span>
                  {theme === 'light' && <Check size={14} className="theme-check" />}
                </button>
                <button
                  className={`theme-option ${theme === 'dark' ? 'active' : ''}`}
                  onClick={() => setTheme('dark')}
                  data-testid="theme-option-dark"
                >
                  <Moon size={16} />
                  <span>Dark</span>
                  {theme === 'dark' && <Check size={14} className="theme-check" />}
                </button>
                <button
                  className={`theme-option ${theme === 'system' ? 'active' : ''}`}
                  onClick={() => setTheme('system')}
                  data-testid="theme-option-system"
                >
                  <Monitor size={16} />
                  <span>System</span>
                  {theme === 'system' && <Check size={14} className="theme-check" />}
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Notifications Section */}
        <section className="settings-section" data-testid="settings-notifications">
          <div className="settings-section-header">
            <Bell size={18} className="settings-section-icon" />
            <h3 className="settings-section-title">Notifications</h3>
          </div>
          <div className="settings-card">
            <div className="settings-row settings-row-toggle">
              <div className="settings-row-label">
                <span className="settings-row-title">In-app notifications</span>
              </div>
              <button
                className={`toggle-switch ${notifications ? 'on' : 'off'}`}
                onClick={() => setNotifications((prev) => !prev)}
                data-testid="notifications-toggle"
              >
                <span className="toggle-thumb" />
              </button>
            </div>
          </div>
        </section>

        {/* Security Section */}
        <section className="settings-section" data-testid="settings-security">
          <div className="settings-section-header">
            <Shield size={18} className="settings-section-icon" />
            <h3 className="settings-section-title">Security</h3>
          </div>
          <div className="settings-card">
            <div className="settings-row settings-row-action disabled-action">
              <div className="settings-row-label">
                <span className="settings-row-title">Change Password</span>
                <span className="settings-row-desc coming-soon-badge">Coming soon</span>
              </div>
              <ChevronRight size={16} className="settings-row-chevron" />
            </div>

            <div className="settings-divider" />

            {!showSignOutConfirm ? (
              <div className="settings-row settings-row-action danger-action" onClick={() => setShowSignOutConfirm(true)}>
                <div className="settings-row-label">
                  <span className="settings-row-title text-error">Sign Out</span>
                  <span className="settings-row-desc">Log out of your CampusAI session</span>
                </div>
                <LogOut size={16} className="text-error" />
              </div>
            ) : (
              <div className="settings-row settings-row-confirm">
                <span className="settings-row-title">Are you sure you want to sign out?</span>
                <div className="confirm-actions">
                  <button
                    className="danger-button"
                    onClick={handleLogout}
                    data-testid="settings-signout-confirm-btn"
                  >
                    Yes, Sign Out
                  </button>
                  <button
                    className="secondary-button"
                    onClick={() => setShowSignOutConfirm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* About Section */}
        <section className="settings-section" data-testid="settings-about">
          <div className="settings-section-header">
            <Info size={18} className="settings-section-icon" />
            <h3 className="settings-section-title">About</h3>
          </div>
          <div className="settings-card">
            <div className="settings-about-row">
              <span className="settings-about-label">Application</span>
              <span className="settings-about-value font-semibold">CampusAI</span>
            </div>
            <div className="settings-about-row">
              <span className="settings-about-label">Version</span>
              <span className="settings-about-value">0.1.0</span>
            </div>
            <div className="settings-about-row">
              <span className="settings-about-label">Description</span>
              <span className="settings-about-value">Official college knowledge assistant</span>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};
