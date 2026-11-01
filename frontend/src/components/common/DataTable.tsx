import React from 'react';
import { ChevronLeft, ChevronRight, Inbox, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import clsx from 'clsx';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  emptyMessage?: string;
  page?: number;
  totalPages?: number;
  total?: number;
  pageSize?: number;
  onPageChange?: (newPage: number) => void;
  sortBy?: string;
  sortDesc?: boolean;
  onSortChange?: (field: string) => void;
  className?: string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  isLoading = false,
  emptyMessage = 'No records found matching criteria',
  page = 1,
  totalPages = 1,
  total = 0,
  pageSize = 50,
  onPageChange,
  sortBy,
  sortDesc,
  onSortChange,
  className,
}: DataTableProps<T>) {
  return (
    <div className={clsx('flex flex-col rounded-xl border border-slate-200/80 bg-white dark:border-slate-800 dark:bg-slate-900 shadow-xs overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/75 dark:bg-slate-900/90 text-slate-600 dark:text-slate-400 font-semibold uppercase tracking-wider">
            <tr>
              {columns.map((col, idx) => {
                const isSorted = sortBy && col.accessorKey === sortBy;
                return (
                  <th
                    key={idx}
                    scope="col"
                    className={clsx(
                      'px-4 py-3.5 whitespace-nowrap',
                      col.sortable && 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors select-none',
                      col.className
                    )}
                    onClick={() => {
                      if (col.sortable && col.accessorKey && onSortChange) {
                        onSortChange(String(col.accessorKey));
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="text-slate-400">
                          {isSorted ? (
                            sortDesc ? <ArrowDown className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" /> : <ArrowUp className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                          ) : (
                            <ArrowUpDown className="h-3 w-3 opacity-40 hover:opacity-100" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-normal text-slate-800 dark:text-slate-200">
            {isLoading ? (
              // Loading Skeleton
              Array.from({ length: 8 }).map((_, rIdx) => (
                <tr key={rIdx} className="animate-pulse">
                  {columns.map((_, cIdx) => (
                    <td key={cIdx} className="px-4 py-3.5">
                      <div className="h-4 rounded bg-slate-150 dark:bg-slate-800 w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              // Empty State
              <tr>
                <td colSpan={columns.length} className="py-14 text-center">
                  <div className="flex flex-col items-center justify-center">
                    <div className="rounded-full bg-slate-100 dark:bg-slate-800 p-3 mb-2 text-slate-400">
                      <Inbox className="h-6 w-6" />
                    </div>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                      {emptyMessage}
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
                      Try adjusting filters or running a planning simulation
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              // Data Rows
              data.map((row, rIdx) => (
                <tr
                  key={row.id || rIdx}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                >
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className={clsx('px-4 py-3 whitespace-nowrap', col.className)}>
                      {col.cell
                        ? col.cell(row)
                        : col.accessorKey
                        ? String(row[col.accessorKey] ?? '-')
                        : null}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalPages > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-200/80 dark:border-slate-800 px-4 py-3 gap-2 bg-slate-50/50 dark:bg-slate-900/60 text-xs text-slate-500 dark:text-slate-400">
          <div>
            Showing <span className="font-semibold text-slate-900 dark:text-slate-200">{Math.min(total, (page - 1) * pageSize + 1)}</span> to{' '}
            <span className="font-semibold text-slate-900 dark:text-slate-200">{Math.min(total, page * pageSize)}</span> of{' '}
            <span className="font-semibold text-slate-900 dark:text-slate-200">{total.toLocaleString()}</span> entries
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onPageChange && onPageChange(page - 1)}
              disabled={page <= 1 || isLoading}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1 font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Prev
            </button>

            <span className="px-2 font-medium text-slate-700 dark:text-slate-300">
              Page {page} of {Math.max(1, totalPages)}
            </span>

            <button
              onClick={() => onPageChange && onPageChange(page + 1)}
              disabled={page >= totalPages || isLoading}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1 font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

