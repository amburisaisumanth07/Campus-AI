import { render, screen, waitFor } from '@testing-library/react';
import { HealthStatus } from './HealthStatus';
import { vi, describe, it, expect } from 'vitest';
import * as api from '../services/api';

vi.mock('../services/api', () => ({
  checkHealth: vi.fn(),
}));

describe('HealthStatus', () => {
  it('displays Checking initially', () => {
    (api.checkHealth as any).mockReturnValue(new Promise(() => {}));
    render(<HealthStatus />);
    expect(screen.getByText(/Checking.../i)).toBeInTheDocument();
  });

  it('displays Connected on success', async () => {
    (api.checkHealth as any).mockResolvedValue({ status: 'ok', database: 'ok' });
    render(<HealthStatus />);
    await waitFor(() => {
      expect(screen.getByText(/Connected/i)).toBeInTheDocument();
    });
  });

  it('displays Unavailable on failure', async () => {
    (api.checkHealth as any).mockRejectedValue(new Error('Failed'));
    render(<HealthStatus />);
    await waitFor(() => {
      expect(screen.getByText(/Unavailable/i)).toBeInTheDocument();
    });
  });
});
