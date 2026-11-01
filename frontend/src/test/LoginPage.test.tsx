import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../api/endpoints';

// Mock api
vi.mock('../api/endpoints', () => ({
  api: {
    login: vi.fn().mockResolvedValue({
      access_token: 'fake-jwt-token',
      token_type: 'bearer',
      user_id: 'user-001',
      email: 'planner@supplychainiq.com',
      full_name: 'Elena Rostova',
      role: 'Planner',
    }),
    getMe: vi.fn().mockResolvedValue({
      id: 'user-001',
      email: 'planner@supplychainiq.com',
      role: 'Planner',
      name: 'Elena Rostova',
      permissions: ['mitigation:approve'],
    }),
  },
}));

describe('LoginPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders login screen with SupplyChain IQ branding and inputs', () => {
    const { container } = render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByText(/SupplyChain/i)).toBeInTheDocument();
    expect(screen.getByText(/Enterprise Email/i)).toBeInTheDocument();
    expect(screen.getByText(/Password/i)).toBeInTheDocument();
    expect(container.querySelector('input[type="email"]')).toBeInTheDocument();
    expect(container.querySelector('input[type="password"]')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In to Control Tower/i })).toBeInTheDocument();
  });

  it('displays quick-switch persona options', () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByText('Elena')).toBeInTheDocument();
    expect(screen.getByText('David')).toBeInTheDocument();
    expect(screen.getByText('Arthur')).toBeInTheDocument();
  });

  it('submits login form successfully with planner credentials', async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /Sign In to Control Tower/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith('planner@supplychainiq.com', 'Planner123!');
    });
  });
});

