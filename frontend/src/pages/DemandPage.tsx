import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { DemandRecord } from '../types';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { TrendingUp, Filter, Calendar, Search } from 'lucide-react';

export const DemandPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [weekBucket, setWeekBucket] = useState('');
  const [skuFilter, setSkuFilter] = useState('');
  const [locationFilter, setLocationFilter] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['demand-planning', page, weekBucket, skuFilter, locationFilter],
    queryFn: () =>
      api.getDemand({
        page,
        page_size: 25,
        week_bucket: weekBucket || undefined,
        sku_id: skuFilter || undefined,
        location_id: locationFilter || undefined,
      }),
  });

  const columns: Column<DemandRecord>[] = [
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
      header: 'SKU Code',
      accessorKey: 'sku_code',
      cell: (row) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-white">{row.sku_code}</span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">{row.category}</p>
        </div>
      ),
    },
    {
      header: 'SKU Name',
      accessorKey: 'sku_name',
    },
    {
      header: 'Location',
      cell: (row) => (
        <div>
          <span className="font-medium text-slate-800 dark:text-slate-200">{row.location_code}</span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">{row.location_name}</p>
        </div>
      ),
    },
    {
      header: 'Forecast Qty',
      accessorKey: 'forecast_qty',
      cell: (row) => (
        <span className="font-bold text-slate-900 dark:text-white">
          {row.forecast_qty.toLocaleString()} units
        </span>
      ),
    },
    {
      header: 'Confidence (P50)',
      accessorKey: 'confidence_p50',
      cell: (row) => `${row.confidence_p50.toLocaleString()}`,
    },
    {
      header: 'Confidence (P90)',
      accessorKey: 'confidence_p90',
      cell: (row) => (
        <span className="text-slate-500 dark:text-slate-400">
          {row.confidence_p90.toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Demand Planning & Forecasting
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Weekly SKU-location projected gross requirements with stochastic confidence intervals
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          title="Total Demand Points"
          value={data?.total.toLocaleString() || '0'}
          subtitle="SKU-Location-Week Combinations"
          icon={<TrendingUp className="h-4 w-4" />}
        />
        <KpiCard
          title="Planning Horizons"
          value="12 Weeks"
          subtitle="2026-W01 through 2026-W12"
          icon={<Calendar className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="Demand Distribution"
          value="Seasonal Gaussian"
          subtitle="Standard deviation ±15% with spikes"
          icon={<Filter className="h-4 w-4" />}
        />
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <Search className="h-3.5 w-3.5" />
          Filters:
        </div>

        <input
          type="text"
          placeholder="Filter by Week (e.g. 2026-W01)..."
          value={weekBucket}
          onChange={(e) => {
            setWeekBucket(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <input
          type="text"
          placeholder="Filter by SKU Code..."
          value={skuFilter}
          onChange={(e) => {
            setSkuFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <input
          type="text"
          placeholder="Filter by Location..."
          value={locationFilter}
          onChange={(e) => {
            setLocationFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        {(weekBucket || skuFilter || locationFilter) && (
          <button
            onClick={() => {
              setWeekBucket('');
              setSkuFilter('');
              setLocationFilter('');
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
          title="Could not load forecast demands"
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

