import React from 'react';
import clsx from 'clsx';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    text: string;
    isGood?: boolean;
  };
  variant?: 'default' | 'critical' | 'warning' | 'success' | 'brand';
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  variant = 'default',
  className,
}) => {
  const borderStyles = {
    default: 'border-slate-200/80 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700',
    critical: 'border-rose-200 dark:border-rose-900/60 bg-gradient-to-br from-rose-50/40 to-transparent dark:from-rose-950/20',
    warning: 'border-amber-200 dark:border-amber-900/60 bg-gradient-to-br from-amber-50/40 to-transparent dark:from-amber-950/20',
    success: 'border-emerald-200 dark:border-emerald-900/60 bg-gradient-to-br from-emerald-50/40 to-transparent dark:from-emerald-950/20',
    brand: 'border-blue-200 dark:border-blue-900/60 bg-gradient-to-br from-blue-50/40 to-transparent dark:from-blue-950/20',
  };

  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl border bg-white dark:bg-slate-900 p-5 shadow-xs transition-all duration-200 hover:shadow-md',
        borderStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </p>
        {icon && (
          <div className="rounded-lg bg-slate-100 dark:bg-slate-800 p-2 text-slate-600 dark:text-slate-300">
            {icon}
          </div>
        )}
      </div>

      <div className="mt-3">
        <h3 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          {value}
        </h3>
        {subtitle && (
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 truncate">
            {subtitle}
          </p>
        )}
      </div>

      {trend && (
        <div className="mt-3 flex items-center gap-1.5 text-xs font-medium">
          {trend.direction === 'up' && (
            <TrendingUp
              className={clsx(
                'h-3.5 w-3.5',
                trend.isGood ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
              )}
            />
          )}
          {trend.direction === 'down' && (
            <TrendingDown
              className={clsx(
                'h-3.5 w-3.5',
                trend.isGood ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
              )}
            />
          )}
          {trend.direction === 'neutral' && (
            <Minus className="h-3.5 w-3.5 text-slate-400" />
          )}
          <span
            className={clsx(
              trend.isGood === undefined
                ? 'text-slate-600 dark:text-slate-400'
                : trend.isGood
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-rose-600 dark:text-rose-400'
            )}
          >
            {trend.text}
          </span>
        </div>
      )}
    </div>
  );
};

