import React, { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { HealthStatus } from '../components/HealthStatus';
import { useAuth } from '../context/AuthContext';
import {
  Home,
  LayoutDashboard,
  BookOpen,
  Shield,
  LogOut,
  MessageSquare,
  Globe,
  Settings,
  Menu,
  X,
} from 'lucide-react';

export const MainLayout: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  // Automatically close mobile menu when navigating to a new route
  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="layout-container">
      {/* Mobile Topbar Navigation (< 1024px) */}
      <header className="mobile-header-bar">
        <div className="mobile-brand">
          <BookOpen className="logo-icon" size={24} />
          <span className="mobile-brand-title">CampusAI</span>
        </div>
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={() => setIsMobileNavOpen((prev) => !prev)}
          aria-label={isMobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={isMobileNavOpen}
        >
          {isMobileNavOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </header>

      {/* Backdrop overlay for mobile drawer */}
      {isMobileNavOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setIsMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Sidebar (Drawer on mobile/tablet, Sticky on desktop) */}
      <aside className={`sidebar ${isMobileNavOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <BookOpen className="logo-icon" size={28} />
          <div className="sidebar-title-box">
            <h1>CampusAI</h1>
            <span className="app-subtitle">College Knowledge Platform</span>
          </div>
          {/* Mobile close button inside drawer */}
          <button
            type="button"
            className="sidebar-drawer-close"
            onClick={() => setIsMobileNavOpen(false)}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        {isAuthenticated && user && (
          <div className="user-profile-widget">
            <div className="user-avatar">{user.name.charAt(0).toUpperCase()}</div>
            <div className="user-info">
              <span className="user-name">{user.name}</span>
              <span className={`user-role-badge ${user.role.toLowerCase()}`}>
                {user.role}
              </span>
            </div>
          </div>
        )}

        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <Home size={19} />
            <span>Home</span>
          </NavLink>

          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <LayoutDashboard size={19} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink to="/chat" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <MessageSquare size={19} />
            <span>Chat Assistant</span>
          </NavLink>

          {user?.role === 'ADMIN' && (
            <>
              <div className="sidebar-section-divider">
                <span>ADMINISTRATION</span>
              </div>
              <NavLink to="/admin" end className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                <Shield size={19} />
                <span>Document Admin</span>
              </NavLink>
              <NavLink to="/admin/sources" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                <Globe size={19} />
                <span>Knowledge Sources</span>
              </NavLink>
              <NavLink to="/admin/coverage" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
                <Shield size={19} />
                <span>Coverage Audit</span>
              </NavLink>
            </>
          )}

          <div className="sidebar-section-divider">
            <span>PREFERENCES</span>
          </div>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            <Settings size={19} />
            <span>Settings</span>
          </NavLink>
        </nav>

        <div className="sidebar-footer">
          {isAuthenticated && (
            <button className="logout-button" onClick={handleLogout} title="Log out of session">
              <LogOut size={18} />
              <span>Log Out</span>
            </button>
          )}
          <HealthStatus />
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};
