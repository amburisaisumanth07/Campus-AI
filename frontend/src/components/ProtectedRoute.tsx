import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';
import { canAccessAdminPanel } from '../utils/permissions';

export const ProtectedRoute: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading && !user) {
    return (
      <div className="loading-screen">
        <Loader2 className="spin" size={32} />
        <p>Verifying session...</p>
      </div>
    );
  }

  if (!isAuthenticated && !user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export const AdminRoute: React.FC = () => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading && !user) {
    return (
      <div className="loading-screen">
        <Loader2 className="spin" size={32} />
        <p>Verifying permissions...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!canAccessAdminPanel(user)) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
};
