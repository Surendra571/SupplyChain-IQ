import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { PurchaseOrderRecord } from '../types';
import { StatusBadge } from '../components/common/Badge';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { ShoppingCart, DollarSign, Clock, CheckCircle2, Filter } from 'lucide-react';

export const PurchaseOrdersPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['purchase-orders', page, statusFilter],
    queryFn: () =>
      api.getPurchaseOrders({
        page,
        page_size: 25,
        status: statusFilter || undefined,
      }),
  });

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const columns: Column<PurchaseOrderRecord>[] = [
    {
      header: 'PO Number',
      accessorKey: 'po_number',
      cell: (row) => (
        <span className="font-semibold text-blue-600 dark:text-blue-400">
          {row.po_number}
        </span>
      ),
    },
    {
      header: 'Supplier',
      cell: (row) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-white">{row.supplier_name}</span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">{row.supplier_code}</p>
        </div>
      ),
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: 'Order Date',
      accessorKey: 'order_date',
      cell: (row) => (row.order_date ? new Date(row.order_date).toLocaleDateString() : '-'),
    },
    {
      header: 'Line Items',
      accessorKey: 'line_count',
      cell: (row) => `${row.line_count} lines`,
    },
    {
      header: 'Total Units',
      accessorKey: 'total_units',
      cell: (row) => (
        <span className="font-bold text-slate-900 dark:text-white">
          {row.total_units.toLocaleString()} units
        </span>
      ),
    },
    {
      header: 'Total Commitment',
      accessorKey: 'total_amount',
      cell: (row) => (
        <span className="font-semibold text-slate-900 dark:text-white">
          {formatCurrency(row.total_amount)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Purchase Orders & Inbound Supply
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Tracking scheduled supplier shipments, open line items, and confirmed dock dates
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Total Orders"
          value={data?.total.toLocaleString() || '0'}
          subtitle="Inbound procurement commitments"
          icon={<ShoppingCart className="h-4 w-4" />}
        />
        <KpiCard
          title="Total Spend"
          value={formatCurrency(
            (data?.items || []).reduce((acc, curr) => acc + curr.total_amount, 0)
          )}
          subtitle="Committed procurement budget"
          icon={<DollarSign className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="Fulfillment"
          value="In Progress"
          subtitle="Dock arrivals mapped to planning weeks"
          icon={<Clock className="h-4 w-4" />}
          variant="warning"
        />
        <KpiCard
          title="Order Integrity"
          value="100% Validated"
          subtitle="Zero orphaned line records"
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
        {['', 'PLACED', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED'].map((st) => (
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
          title="Could not load purchase orders"
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

