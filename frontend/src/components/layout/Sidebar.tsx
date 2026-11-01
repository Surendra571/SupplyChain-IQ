import React from 'react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import {
  LayoutDashboard,
  TrendingUp,
  Boxes,
  Truck,
  ShoppingCart,
  Factory,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  History,
  Cpu,
  Layers,
} from 'lucide-react';

interface NavItem {
  name: string;
  path: string;
  icon: React.ReactNode;
  badge?: string;
  badgeColor?: string;
}

const NAV_ITEMS: NavItem[] = [
  { name: 'Executive Dashboard', path: '/', icon: <LayoutDashboard className="h-4 w-4" /> },
  { name: 'Demand Planning', path: '/demand', icon: <TrendingUp className="h-4 w-4" /> },
  { name: 'Inventory Management', path: '/inventory', icon: <Boxes className="h-4 w-4" /> },
  { name: 'Supplier Management', path: '/suppliers', icon: <Truck className="h-4 w-4" /> },
  { name: 'Purchase Orders', path: '/purchase-orders', icon: <ShoppingCart className="h-4 w-4" /> },
  { name: 'Production Planning', path: '/production', icon: <Factory className="h-4 w-4" /> },
  { name: 'Shortage Workbench', path: '/shortages', icon: <AlertTriangle className="h-4 w-4" />, badge: 'Active', badgeColor: 'bg-rose-500/10 text-rose-600 dark:text-rose-400' },
  { name: 'Mitigation Planner', path: '/mitigations', icon: <Lightbulb className="h-4 w-4" /> },
  { name: 'Data Quality', path: '/data-quality', icon: <ShieldCheck className="h-4 w-4" /> },
  { name: 'Audit History', path: '/audit', icon: <History className="h-4 w-4" /> },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 shrink-0 flex flex-col border-r border-slate-200/80 bg-white dark:border-slate-800 dark:bg-slate-900 transition-colors select-none z-20">
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-200/80 dark:border-slate-800">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20">
          <Layers className="h-5 w-5" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-white">
              SupplyChain <span className="text-blue-600 dark:text-blue-400">IQ</span>
            </h1>
            <span className="rounded-sm bg-blue-50 px-1.5 py-0.2 text-[9px] font-semibold text-blue-700 dark:bg-blue-950/70 dark:text-blue-300">
              v1.0
            </span>
          </div>
          <p className="text-[11px] font-medium text-slate-400 dark:text-slate-500">
            Control Tower & MRP
          </p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Planning & Operations
        </div>

        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium transition-all group',
                isActive
                  ? 'bg-blue-50/80 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300 font-semibold'
                  : 'text-slate-600 hover:bg-slate-100/70 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-200'
              )
            }
          >
            <div className="flex items-center gap-2.5">
              <span className="shrink-0 transition-transform group-hover:scale-105">
                {item.icon}
              </span>
              <span>{item.name}</span>
            </div>
            {item.badge && (
              <span
                className={clsx(
                  'rounded-full px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase',
                  item.badgeColor || 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                )}
              >
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Engine Status Footer */}
      <div className="p-3 border-t border-slate-200/80 dark:border-slate-800">
        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 p-3 text-[11px] border border-slate-200/50 dark:border-slate-800">
          <div className="flex items-center justify-between mb-1">
            <span className="flex items-center gap-1.5 font-semibold text-slate-700 dark:text-slate-300">
              <Cpu className="h-3.5 w-3.5 text-blue-500" />
              OR-Tools Solver
            </span>
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400">
            Engine: Deterministic MRP
          </div>
          <div className="text-[10px] text-slate-400 dark:text-slate-500">
            DB: PostgreSQL 17 (Port 5433)
          </div>
        </div>
      </div>
    </aside>
  );
};

