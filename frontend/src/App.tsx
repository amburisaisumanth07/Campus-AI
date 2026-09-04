import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { MainLayout } from './layouts/MainLayout';
import { AuthLayout } from './layouts/AuthLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Home } from './pages/Home';
import { Dashboard } from './pages/Dashboard';
import { ChatPage } from './pages/Chat';
import { Admin } from './pages/Admin';
import { AdminSources } from './pages/AdminSources';
import { AnnouncementDetail } from './pages/AnnouncementDetail';
import { AcademicCalendarPage } from './pages/AcademicCalendarPage';
import { ExaminationsPage } from './pages/ExaminationsPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { DepartmentDetail } from './pages/DepartmentDetail';
import { PlacementsPage } from './pages/PlacementsPage';
import { Settings } from './pages/Settings';
import { ProtectedRoute, AdminRoute } from './components/ProtectedRoute';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Authentication Routes - Wrapped only in clean AuthLayout */}
            <Route element={<AuthLayout />}>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
            </Route>

            {/* Protected Student / General User Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/" element={<Home />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/announcements/:id" element={<AnnouncementDetail />} />
                <Route path="/academic-calendar" element={<AcademicCalendarPage />} />
                <Route path="/examinations" element={<ExaminationsPage />} />
                <Route path="/departments" element={<DepartmentsPage />} />
                <Route path="/departments/:code" element={<DepartmentDetail />} />
                <Route path="/placements" element={<PlacementsPage />} />
              </Route>
            </Route>

            {/* Protected Admin Routes */}
            <Route element={<AdminRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/admin" element={<Admin />} />
                <Route path="/admin/sources" element={<AdminSources />} />
              </Route>
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
};

export default App;
