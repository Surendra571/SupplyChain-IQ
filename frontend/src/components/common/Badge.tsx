import React from 'react';
import clsx from 'clsx';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'critical' | 'high' | 'medium' | 'low' | 'success' | 'warning' | 'info' | 'neutral';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className,
}) => {
  const variantStyles = {
    critical: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800',
    high: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
    medium: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800',
    low: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800',
    warning: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800',
    info: 'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800',
    neutral: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
  };

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full border tracking-wide uppercase',
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {children}
    </span>
  );
};

export const PriorityBadge: React.FC<{ priority: string; size?: 'sm' | 'md' }> = ({ priority, size = 'sm' }) => {
  const p = (priority || '').toUpperCase();
  if (p === 'CRITICAL') return <Badge variant="critical" size={size}>{priority}</Badge>;
  if (p === 'HIGH') return <Badge variant="high" size={size}>{priority}</Badge>;
  if (p === 'MEDIUM') return <Badge variant="medium" size={size}>{priority}</Badge>;
  return <Badge variant="low" size={size}>{priority || 'LOW'}</Badge>;
};

export const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({ status, size = 'sm' }) => {
  const s = (status || '').toUpperCase();
  if (s === 'APPROVED' || s === 'RESOLVED' || s === 'DELIVERED' || s === 'SUCCESS' || s === 'COMPLETED') {
    return <Badge variant="success" size={size}>{status}</Badge>;
  }
  if (s === 'MITIGATING' || s === 'IN_TRANSIT' || s === 'IN_PROGRESS' || s === 'PLACED') {
    return <Badge variant="info" size={size}>{status}</Badge>;
  }
  if (s === 'IDENTIFIED' || s === 'PLANNED' || s === 'DRAFT') {
    return <Badge variant="warning" size={size}>{status}</Badge>;
  }
  if (s === 'REJECTED' || s === 'CANCELLED' || s === 'FAILED') {
    return <Badge variant="critical" size={size}>{status}</Badge>;
  }
  return <Badge variant="neutral" size={size}>{status}</Badge>;
};

