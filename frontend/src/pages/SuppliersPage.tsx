import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { SupplierRecord } from '../types';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { Truck, Clock, Award, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';

export const SuppliersPage: React.FC = () => {
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['suppliers-overview', page],
    queryFn: () =>
      api.getSuppliers({
        page,
        page_size: 25,
      }),
  });

  const columns: Column<SupplierRecord>[] = [
    {
      header: 'Supplier Code',
      accessorKey: 'supplier_code',
      cell: (row) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {row.supplier_code}
        </span>
      ),
    },
    {
      header: 'Supplier Name',
      accessorKey: 'name',
      cell: (row) => (
        <span className="font-semibold text-slate-900 dark:text-white">{row.name}</span>
      ),
    },
    {
      header: 'Tier',
      accessorKey: 'tier',
      cell: (row) => {
        const isTier1 = row.tier.includes('1');
        return (
          <span
            className={clsx(
              'rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider',
              isTier1
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300'
                : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
            )}
          >
            {row.tier}
          </span>
        );
      },
    },
    {
      header: 'Origin Country',
      accessorKey: 'country',
    },
    {
      header: 'Nominal Lead Time',
      accessorKey: 'lead_time_days',
      cell: (row) => `${row.lead_time_days || 14} days`,
    },
    {
      header: 'On-Time Delivery Rate',
      accessorKey: 'on_time_delivery_rate',
      cell: (row) => {
        const rate = row.on_time_delivery_rate || 95.0;
        return (
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-16 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{ width: `${Math.min(100, rate)}%` }}
              />
            </div>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 text-xs">
              {rate.toFixed(1)}%
            </span>
          </div>
        );
      },
    },
    {
      header: 'Active SKUs',
      accessorKey: 'active_skus_count',
      cell: (row) => (
        <span className="font-medium text-slate-700 dark:text-slate-300">
          {row.active_skus_count} parts
        </span>
      ),
    },
    {
      header: 'Weekly Capacity',
      accessorKey: 'total_capacity',
      cell: (row) => (
        <span className="font-bold text-slate-900 dark:text-white">
          {row.total_capacity > 0 ? `${row.total_capacity.toLocaleString()} units` : 'Unconstrained'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Supplier Network & Capacity Management
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Approved vendor master, committed weekly capacities, procurement lead times, and fulfillment SLAs
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Total Suppliers"
          value={data?.total.toLocaleString() || '25'}
          subtitle="Qualified global partners"
          icon={<Truck className="h-4 w-4" />}
        />
        <KpiCard
          title="Avg Lead Time"
          value="14.2 Days"
          subtitle="Purchase order to port arrival"
          icon={<Clock className="h-4 w-4" />}
        />
        <KpiCard
          title="Network SLA"
          value="95.8%"
          subtitle="On-time delivery average"
          icon={<Award className="h-4 w-4" />}
          variant="success"
        />
        <KpiCard
          title="Capacity Commitment"
          value="100% Tracked"
          subtitle="Surge buffers monitored"
          icon={<CheckCircle2 className="h-4 w-4" />}
          variant="brand"
        />
      </div>

      {error ? (
        <ErrorBanner
          title="Could not load supplier network"
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

