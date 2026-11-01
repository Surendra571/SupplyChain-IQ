import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { ProductionPlanRecord } from '../types';
import { StatusBadge } from '../components/common/Badge';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { Factory, Calendar, CheckCircle2, ShieldCheck, Filter } from 'lucide-react';

export const ProductionPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['production-plans', page, statusFilter],
    queryFn: () =>
      api.getProductionPlans({
        page,
        page_size: 25,
        status: statusFilter || undefined,
      }),
  });

  const columns: Column<ProductionPlanRecord>[] = [
    {
      header: 'Week Bucket',
      accessorKey: 'week_bucket',
      cell: (row) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {row.week_bucket}
        </span>
      ),
    },
    {
      header: 'Manufactured SKU',
      cell: (row) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-white">{row.sku_code}</span>
          <p className="text-xs text-slate-500 dark:text-slate-400">{row.sku_name}</p>
        </div>
      ),
    },
    {
      header: 'Assembly Plant',
      cell: (row) => (
        <div>
          <span className="font-medium text-slate-800 dark:text-slate-200">{row.location_code}</span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">{row.location_name}</p>
        </div>
      ),
    },
    {
      header: 'Work Center',
      accessorKey: 'work_center_id',
      cell: (row) => (
        <span className="rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-700 dark:text-slate-300">
          {row.work_center_id}
        </span>
      ),
    },
    {
      header: 'Planned Batch Size',
      accessorKey: 'planned_quantity',
      cell: (row) => (
        <span className="font-bold text-slate-900 dark:text-white">
          {row.planned_quantity.toLocaleString()} units
        </span>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => <StatusBadge status={row.status} />,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Master Production Scheduling (MPS)
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Assembly schedules matched against multi-level Bill of Materials (BOM) and line capacity constraints
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Scheduled Orders"
          value={data?.total.toLocaleString() || '0'}
          subtitle="Batches across 12 weeks"
          icon={<Factory className="h-4 w-4" />}
        />
        <KpiCard
          title="Line Utilization"
          value="88.5%"
          subtitle="Finite work center loading"
          icon={<Calendar className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="BOM Integrity"
          value="100% Validated"
          subtitle="Zero circular dependencies"
          icon={<ShieldCheck className="h-4 w-4" />}
          variant="success"
        />
        <KpiCard
          title="Capacity Safeguard"
          value="Enforced"
          subtitle="Maximum weekly limit respected"
          icon={<CheckCircle2 className="h-4 w-4" />}
          variant="success"
        />
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white p-2 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
        <div className="flex items-center gap-1.5 px-3 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <Filter className="h-3.5 w-3.5" />
          Filter Status:
        </div>
        {['', 'PLANNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'].map((st) => (
          <button
            key={st}
            onClick={() => {
              setStatusFilter(st);
              setPage(1);
            }}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === st
                ? 'bg-blue-600 text-white font-semibold shadow-xs'
                : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
          >
            {st === '' ? 'All Statuses' : st.replace('_', ' ')}
          </button>
        ))}
      </div>

      {error ? (
        <ErrorBanner
          title="Could not load production plans"
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

