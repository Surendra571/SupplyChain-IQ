import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { InventoryRecord } from '../types';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { Boxes, DollarSign, ShieldAlert, CheckCircle2, Search } from 'lucide-react';
import clsx from 'clsx';

export const InventoryPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState('');
  const [locationCode, setLocationCode] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['inventory-management', page, category, locationCode],
    queryFn: () =>
      api.getInventory({
        page,
        page_size: 25,
        category: category || undefined,
        location_code: locationCode || undefined,
      }),
  });

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 2,
    }).format(val);
  };

  const columns: Column<InventoryRecord>[] = [
    {
      header: 'SKU Item',
      cell: (row) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-white">{row.sku_code}</span>
          <p className="text-xs text-slate-500 dark:text-slate-400">{row.sku_name}</p>
        </div>
      ),
    },
    {
      header: 'Category',
      accessorKey: 'category',
      cell: (row) => (
        <span className="rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300">
          {row.category}
        </span>
      ),
    },
    {
      header: 'Location',
      cell: (row) => (
        <div>
          <span className="font-medium text-slate-800 dark:text-slate-200">{row.location_code}</span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">{row.location_type}</p>
        </div>
      ),
    },
    {
      header: 'On Hand',
      accessorKey: 'on_hand_qty',
      cell: (row) => (
        <span className="font-bold text-slate-900 dark:text-white">
          {row.on_hand_qty.toLocaleString()}
        </span>
      ),
    },
    {
      header: 'Allocated',
      accessorKey: 'allocated_qty',
      cell: (row) => (
        <span className="text-slate-500 dark:text-slate-400">
          {row.allocated_qty.toLocaleString()}
        </span>
      ),
    },
    {
      header: 'Available',
      accessorKey: 'available_qty',
      cell: (row) => {
        const isLow = row.available_qty < row.safety_stock_qty;
        return (
          <span
            className={clsx(
              'font-semibold',
              isLow ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'
            )}
          >
            {row.available_qty.toLocaleString()}
          </span>
        );
      },
    },
    {
      header: 'Safety Stock',
      accessorKey: 'safety_stock_qty',
      cell: (row) => `${row.safety_stock_qty.toLocaleString()}`,
    },
    {
      header: 'Unit Cost',
      accessorKey: 'unit_cost',
      cell: (row) => formatCurrency(row.unit_cost),
    },
    {
      header: 'Total Valuation',
      accessorKey: 'total_value',
      cell: (row) => (
        <span className="font-semibold text-slate-900 dark:text-white">
          {formatCurrency(row.total_value)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Inventory Management & Valuation
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Real-time physical stock balances, safety buffers, committed allocations, and working capital
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Stock Keeping Units"
          value={data?.total.toLocaleString() || '0'}
          subtitle="Stocked across all locations"
          icon={<Boxes className="h-4 w-4" />}
        />
        <KpiCard
          title="Inventory Health"
          value="Healthy"
          subtitle="Safety-stock protected"
          icon={<CheckCircle2 className="h-4 w-4" />}
          variant="success"
        />
        <KpiCard
          title="Valuation Method"
          value="Standard FIFO"
          subtitle="Deterministic cost accounting"
          icon={<DollarSign className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="Stockout Safeguard"
          value="Dynamic ROP"
          subtitle="Reorder points adjusted to lead time"
          icon={<ShieldAlert className="h-4 w-4" />}
        />
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <Search className="h-3.5 w-3.5" />
          Filter Stock:
        </div>

        <input
          type="text"
          placeholder="Filter by Category (e.g. Raw Material)..."
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <input
          type="text"
          placeholder="Filter by Location Code..."
          value={locationCode}
          onChange={(e) => {
            setLocationCode(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        {(category || locationCode) && (
          <button
            onClick={() => {
              setCategory('');
              setLocationCode('');
              setPage(1);
            }}
            className="text-xs font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400"
          >
            Clear Filters
          </button>
        )}
      </div>

      {error ? (
        <ErrorBanner
          title="Could not load inventory balances"
          message={(error as any)?.message || 'Database connection error'}
          onRetry={() => refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.items || []}
          isLoading={isLoading}
          page={page}
          totalPages={data?.total_pages || 1}
          total={data?.total || 0}
          pageSize={25}
          onPageChange={(p) => setPage(p)}
        />
      )}
    </div>
  );
};

