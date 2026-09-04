import type { Role, User } from '../types/api';

export type UserRole = Role;

/**
 * Checks if a given role or user has permission to upload PDF documents.
 * Allowed roles: ADMIN, FACULTY.
 * Students (STUDENT) and unauthenticated users return false.
 */
export const canUploadDocuments = (roleOrUser?: UserRole | User | null): boolean => {
  if (!roleOrUser) return false;
  const role = typeof roleOrUser === 'string' ? roleOrUser : roleOrUser.role;
  return role === 'ADMIN' || role === 'FACULTY';
};

/**
 * Checks if a given role or user has permission to delete documents.
 * Allowed roles: ADMIN.
 */
export const canDeleteDocuments = (roleOrUser?: UserRole | User | null): boolean => {
  if (!roleOrUser) return false;
  const role = typeof roleOrUser === 'string' ? roleOrUser : roleOrUser.role;
  return role === 'ADMIN';
};

/**
 * Checks if a given role or user has access to the Admin panel.
 * Allowed roles: ADMIN.
 */
export const canAccessAdminPanel = (roleOrUser?: UserRole | User | null): boolean => {
  if (!roleOrUser) return false;
  const role = typeof roleOrUser === 'string' ? roleOrUser : roleOrUser.role;
  return role === 'ADMIN';
};
