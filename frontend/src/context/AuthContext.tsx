import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { User } from '../types/api';
import { getMeApi } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<User>;
  logout: () => void;
}

const TOKEN_KEY = 'campusai_token';
const USER_KEY = 'campusai_user';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  });

  const [user, setUser] = useState<User | null>(() => {
    try {
      const storedUser = localStorage.getItem(USER_KEY);
      return storedUser ? JSON.parse(storedUser) : null;
    } catch {
      return null;
    }
  });

  // Only show initial loading screen if we have a token stored but no user profile cached yet
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    try {
      const savedToken = localStorage.getItem(TOKEN_KEY);
      const savedUser = localStorage.getItem(USER_KEY);
      return Boolean(savedToken && !savedUser);
    } catch {
      return false;
    }
  });

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (e) {
      console.error("Failed to clear auth storage:", e);
    }
    setToken(null);
    setUser(null);
    setIsLoading(false);
  }, []);

  // Listen for global unauthorized events (HTTP 401 from any API call)
  useEffect(() => {
    const handleUnauthorized = () => {
      logout();
    };

    window.addEventListener('campusai:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('campusai:unauthorized', handleUnauthorized);
    };
  }, [logout]);

  // Initial startup verification: run ONCE when the app loads
  useEffect(() => {
    let isMounted = true;

    const verifyInitialSession = async () => {
      const currentToken = localStorage.getItem(TOKEN_KEY);
      if (!currentToken) {
        if (isMounted) {
          setUser(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await getMeApi(currentToken);
        if (isMounted) {
          setUser(userData);
          try {
            localStorage.setItem(USER_KEY, JSON.stringify(userData));
          } catch (e) {
            console.error("Failed to persist user profile:", e);
          }
        }
      } catch (error: any) {
        console.error("Initial session verification failed:", error);
        // Only log out if it was an explicit auth error (401, 403, or invalid token)
        const isAuthError =
          error?.message?.includes('401') ||
          error?.message?.includes('403') ||
          error?.message?.toLowerCase().includes('unauthorized') ||
          error?.message?.toLowerCase().includes('invalid token');

        if (isAuthError && isMounted) {
          logout();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    verifyInitialSession();

    return () => {
      isMounted = false;
    };
  }, [logout]);

  const login = async (newToken: string): Promise<User> => {
    try {
      localStorage.setItem(TOKEN_KEY, newToken);
    } catch (e) {
      console.error("Failed to save token:", e);
    }
    setToken(newToken);

    const userData = await getMeApi(newToken);
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(userData));
    } catch (e) {
      console.error("Failed to save user profile:", e);
    }
    setUser(userData);
    setIsLoading(false);
    return userData;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(user && token),
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
