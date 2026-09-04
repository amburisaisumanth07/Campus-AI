import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  getMeApi: vi.fn(),
  loginApi: vi.fn(),
  registerApi: vi.fn(),
}));

const TestConsumer = () => {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  if (isLoading) return <div>Loading Auth...</div>;
  return (
    <div>
      <div data-testid="auth-state">{isAuthenticated ? 'Authenticated' : 'Unauthenticated'}</div>
      <div data-testid="user-name">{user?.name || 'No User'}</div>
      <button onClick={logout}>Log Out</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('provides unauthenticated state by default when no token in localStorage', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(await screen.findByTestId('auth-state')).toHaveTextContent('Unauthenticated');
    expect(screen.getByTestId('user-name')).toHaveTextContent('No User');
  });

  it('restores user session if token exists in localStorage', async () => {
    localStorage.setItem('campusai_token', 'valid-test-token');
    (api.getMeApi as any).mockResolvedValue({
      id: 1,
      name: 'John Doe',
      email: 'john@campusai.edu',
      role: 'STUDENT',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(await screen.findByTestId('auth-state')).toHaveTextContent('Authenticated');
    expect(screen.getByTestId('user-name')).toHaveTextContent('John Doe');
  });

  it('clears token on logout', async () => {
    localStorage.setItem('campusai_token', 'valid-test-token');
    (api.getMeApi as any).mockResolvedValue({
      id: 1,
      name: 'John Doe',
      email: 'john@campusai.edu',
      role: 'STUDENT',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(await screen.findByTestId('auth-state')).toHaveTextContent('Authenticated');

    act(() => {
      screen.getByText('Log Out').click();
    });

    expect(screen.getByTestId('auth-state')).toHaveTextContent('Unauthenticated');
    expect(localStorage.getItem('campusai_token')).toBeNull();
  });
});
