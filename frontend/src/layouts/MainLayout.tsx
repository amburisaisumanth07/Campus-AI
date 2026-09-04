import React from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
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
} from 'lucide-react';

export const MainLayout: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="layout-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <BookOpen className="logo-icon" size={28} />
          <div>
            <h1>CampusAI</h1>
            <span className="app-subtitle">College Knowledge Platform</span>
          </div>
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
