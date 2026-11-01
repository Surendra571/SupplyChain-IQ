import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/endpoints';
import { UserProfile } from '../types';

export interface PersonaOption {
  email: string;
  role: string;
  name: string;
  password: string;
  avatarColor: string;
}

export const DEMO_PERSONAS: PersonaOption[] = [
  {
    email: 'planner@supplychainiq.com',
    role: 'Planner',
    name: 'Elena Rostova',
    password: 'Planner123!',
    avatarColor: 'bg-blue-600',
  },
  {
    email: 'procurement@supplychainiq.com',
    role: 'Procurement Manager',
    name: 'David Sterling',
    password: 'Procure123!',
    avatarColor: 'bg-emerald-600',
  },
  {
    email: 'opsmanager@supplychainiq.com',
    role: 'Operations Manager',
    name: 'Arthur Pendelton',
    password: 'OpsMgr123!',
    avatarColor: 'bg-purple-600',
  },
  {
    email: 'logistics@supplychainiq.com',
    role: 'Logistics Analyst',
    name: 'Marcus Vance',
    password: 'Logistics123!',
    avatarColor: 'bg-amber-600',
  },
  {
    email: 'warehouse@supplychainiq.com',
    role: 'Warehouse Operator',
    name: 'Clara Jensen',
    password: 'Warehouse123!',
    avatarColor: 'bg-orange-600',
  },
  {
    email: 'admin@supplychainiq.com',
    role: 'Administrator',
    name: 'System Administrator',
    password: 'Admin123!',
    avatarColor: 'bg-rose-600',
  },
];

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  switchPersona: (email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('supplychain_iq_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('supplychain_iq_token');
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const login = async (email: string, password: string) => {
    try {
      const data = await api.login(email, password);
      setToken(data.access_token);
      const profile: UserProfile = {
        id: data.user_id,
        username: data.email.split('@')[0],
        email: data.email,
        full_name: data.full_name,
        role: data.role,
        permissions: [],
      };
      setUser(profile);
      localStorage.setItem('supplychain_iq_token', data.access_token);
      localStorage.setItem('supplychain_iq_user', JSON.stringify(profile));
    } catch (err) {
      console.error('Failed to log in:', err);
      throw err;
    }
  };

  const switchPersona = async (email: string) => {
    const persona = DEMO_PERSONAS.find((p) => p.email === email);
    if (persona) {
      await login(persona.email, persona.password);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('supplychain_iq_token');
    localStorage.removeItem('supplychain_iq_user');
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('supplychain_iq_token');
      if (savedToken) {
        try {
          const profile = await api.getCurrentUser();
          setUser(profile);
          localStorage.setItem('supplychain_iq_user', JSON.stringify(profile));
        } catch {
          // Token expired or invalid, auto-login with default demo planner persona
          await login('planner@supplychainiq.com', 'Planner123!');
        }
      } else {
        // Auto-login default demo planner persona
        await login('planner@supplychainiq.com', 'Planner123!');
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, switchPersona, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

