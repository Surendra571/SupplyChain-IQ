import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, DEMO_PERSONAS } from '../context/AuthContext';
import { Layers, ShieldCheck, ArrowRight, UserCheck } from 'lucide-react';
import clsx from 'clsx';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('planner@supplychainiq.com');
  const [password, setPassword] = useState('Planner123!');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Login failed. Please check credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSelectPersona = async (p: typeof DEMO_PERSONAS[0]) => {
    setEmail(p.email);
    setPassword(p.password);
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await login(p.email, p.password);
      navigate('/');
    } catch (err: any) {
      setErrorMsg(err.response?.data?.message || 'Login failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-slate-50 dark:bg-slate-950 p-4 font-sans">
      <div className="w-full max-w-md rounded-2xl border border-slate-200/80 bg-white p-8 shadow-xl dark:border-slate-800 dark:bg-slate-900">
        {/* Brand */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/20">
            <Layers className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">
              SupplyChain <span className="text-blue-600 dark:text-blue-400">IQ</span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Intelligent Planning & Shortage Mitigation Platform
            </p>
          </div>
        </div>

        {errorMsg && (
          <div className="mb-4 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700 dark:bg-rose-950/40 dark:border-rose-900 dark:text-rose-300">
            {errorMsg}
          </div>
        )}

        {/* Quick Demo Persona Select */}
        <div className="mb-6">
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
            <UserCheck className="h-3.5 w-3.5 text-blue-500" />
            Quick Sign-In by Role:
          </p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_PERSONAS.map((p) => (
              <button
                key={p.email}
                type="button"
                onClick={() => handleSelectPersona(p)}
                disabled={isSubmitting}
                className={clsx(
                  'flex items-center gap-2 rounded-lg border p-2 text-left text-xs transition-colors',
                  email === p.email
                    ? 'border-blue-500 bg-blue-50/60 text-blue-800 dark:border-blue-600 dark:bg-blue-950/60 dark:text-blue-200 font-semibold'
                    : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                )}
              >
                <span className={clsx('h-2 w-2 rounded-full shrink-0', p.avatarColor)} />
                <div className="truncate">
                  <p className="truncate font-medium">{p.name.split(' ')[0]}</p>
                  <p className="text-[10px] text-slate-400 truncate">{p.role}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Enterprise Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 py-2.5 text-xs font-semibold text-white shadow-md hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition-colors"
          >
            <span>Sign In to Control Tower</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </form>

        <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800 text-center text-[11px] text-slate-400 dark:text-slate-500 flex items-center justify-center gap-1">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
          Role-Based Access Control (RBAC) Active
        </div>
      </div>
    </div>
  );
};
