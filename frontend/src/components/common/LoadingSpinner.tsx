import React from 'react';
import clsx from 'clsx';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface LoadingSpinnerProps {
  text?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  text = 'Loading...',
  size = 'md',
  className,
}) => {
  const sizeStyles = {
    sm: 'h-4 w-4 border-2',
    md: 'h-7 w-7 border-3',
    lg: 'h-10 w-10 border-4',
  };

  return (
    <div className={clsx('flex flex-col items-center justify-center p-8 text-center', className)}>
      <div
        className={clsx(
          'animate-spin rounded-full border-slate-200 border-t-blue-600 dark:border-slate-800 dark:border-t-blue-500',
          sizeStyles[size]
        )}
      />
      {text && (
        <p className="mt-3 text-xs font-medium text-slate-500 dark:text-slate-400 animate-pulse">
          {text}
        </p>
      )}
    </div>
  );
};

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Failed to load data',
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      className={clsx(
        'rounded-xl border border-rose-200 bg-rose-50/70 p-4 dark:border-rose-900/60 dark:bg-rose-950/30',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-rose-900 dark:text-rose-200">{title}</h4>
          <p className="mt-1 text-xs text-rose-700 dark:text-rose-300">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50 dark:border-rose-800 dark:bg-slate-900 dark:text-rose-300 dark:hover:bg-rose-950 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Retry
          </button>
        )}
      </div>
    </div>
  );
};

