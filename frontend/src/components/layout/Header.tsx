import React, { useState } from 'react';
import { useAuth, DEMO_PERSONAS } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { api } from '../../api/endpoints';
import {
  Sun,
  Moon,
  Play,
  UserCheck,
  ChevronDown,
  CheckCircle2,
  Loader2,
  Shield,
} from 'lucide-react';
import clsx from 'clsx';

export const Header: React.FC = () => {
  const { user, switchPersona } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isPersonaMenuOpen, setIsPersonaMenuOpen] = useState(false);
  const [isTriggeringRun, setIsTriggeringRun] = useState(false);
  const [runSuccessNotice, setRunSuccessNotice] = useState<string | null>(null);

  const handleTriggerRun = async () => {
    setIsTriggeringRun(true);
    try {
      const res = await api.triggerPlanningRun('WEEKLY_MRP');
      setRunSuccessNotice(`Planning Run #${res.run_number || 1} triggered!`);
      setTimeout(() => setRunSuccessNotice(null), 4000);
    } catch (err: any) {
      alert(`Planning run trigger error: ${err.message || 'Unknown'}`);
    } finally {
      setIsTriggeringRun(false);
    }
  };

  return (
    <header className="h-16 shrink-0 border-b border-slate-200/80 bg-white/90 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/90 px-6 flex items-center justify-between z-10">
      {/* Left: Active Planning Run Badge */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 rounded-lg bg-blue-50/70 border border-blue-200/60 px-3 py-1 text-xs text-blue-700 dark:bg-blue-950/40 dark:border-blue-900/50 dark:text-blue-300">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600" />
          </span>
          <span className="font-semibold">Planning Horizon:</span>
          <span>12 Weeks (2026-W01 to 2026-W12)</span>
        </div>

        {runSuccessNotice && (
          <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 px-3 py-1 rounded-lg animate-in fade-in">
            <CheckCircle2 className="h-3.5 w-3.5" />
            {runSuccessNotice}
          </div>
        )}
      </div>

      {/* Right: Actions, Persona Switcher & Theme */}
      <div className="flex items-center gap-3">
        {/* Trigger MRP Simulation Button */}
        <button
          onClick={handleTriggerRun}
          disabled={isTriggeringRun}
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition-colors"
        >
          {isTriggeringRun ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5 fill-current" />
          )}
          <span>Run MRP Engine</span>
        </button>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle Theme"
          className="rounded-lg border border-slate-200 dark:border-slate-700 p-2 text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 transition-colors"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        {/* Persona Switcher Dropdown */}
        <div className="relative">
          <button
            onClick={() => setIsPersonaMenuOpen(!isPersonaMenuOpen)}
            className="flex items-center gap-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-white font-bold text-[10px]">
              {user?.full_name ? user.full_name.charAt(0) : 'U'}
            </div>
            <div className="text-left hidden sm:block">
              <p className="font-semibold text-slate-900 dark:text-white leading-tight">
                {user?.full_name || 'Planner'}
              </p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight flex items-center gap-1">
                <Shield className="h-2.5 w-2.5 text-blue-500" />
                {user?.role || 'Planner'}
              </p>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
          </button>

          {isPersonaMenuOpen && (
            <>
              <div
                className="fixed inset-0 z-30"
                onClick={() => setIsPersonaMenuOpen(false)}
              />
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-xl dark:border-slate-800 dark:bg-slate-900 z-40 text-xs">
                <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800">
                  <p className="font-semibold text-slate-900 dark:text-white">Enterprise Persona Switcher</p>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400">
                    Switch roles to test permissions & workflows
                  </p>
                </div>

                <div className="py-1">
                  {DEMO_PERSONAS.map((p) => {
                    const isSelected = user?.email === p.email;
                    return (
                      <button
                        key={p.email}
                        onClick={async () => {
                          await switchPersona(p.email);
                          setIsPersonaMenuOpen(false);
                        }}
                        className={clsx(
                          'w-full flex items-center justify-between rounded-lg px-3 py-2 text-left transition-colors',
                          isSelected
                            ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300 font-semibold'
                            : 'text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span className={clsx('h-2 w-2 rounded-full', p.avatarColor)} />
                          <div>
                            <p className="text-xs leading-none">{p.name}</p>
                            <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5 leading-none">
                              {p.role}
                            </p>
                          </div>
                        </div>
                        {isSelected && <UserCheck className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />}
                      </button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
