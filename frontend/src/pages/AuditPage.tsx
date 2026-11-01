import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { AuditEventRecord } from '../types';
import { Badge } from '../components/common/Badge';
import { KpiCard } from '../components/common/KpiCard';
import { ErrorBanner } from '../components/common/LoadingSpinner';
import { History, Shield, Lock, CheckCircle2, Search } from 'lucide-react';

export const AuditPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [entityFilter, setEntityFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-history', page, entityFilter, actionFilter],
    queryFn: () =>
      api.getAuditEvents({
        page,
        page_size: 25,
        entity_type: entityFilter || undefined,
        action: actionFilter || undefined,
      }),
  });

  const columns: Column<AuditEventRecord>[] = [
    {
      header: 'Event ID',
      accessorKey: 'business_id',
      cell: (row) => (
        <span className="font-mono text-xs font-semibold text-blue-600 dark:text-blue-400">
          {row.business_id || row.id.slice(0, 8)}
        </span>
      ),
    },
    {
      header: 'Action',
      accessorKey: 'action',
      cell: (row) => (
        <Badge
          variant={
            row.action.includes('APPROVED')
              ? 'success'
              : row.action.includes('REJECTED')
              ? 'critical'
              : 'info'
          }
          size="sm"
        >
          {row.action}
        </Badge>
      ),
    },
    {
      header: 'Entity Type',
      accessorKey: 'entity_type',
      cell: (row) => (
        <span className="font-mono text-xs text-slate-700 dark:text-slate-300">
          {row.entity_type}
        </span>
      ),
    },
    {
      header: 'Entity Record ID',
      accessorKey: 'entity_id',
      cell: (row) => (
        <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400 truncate max-w-xs">
          {row.entity_id}
        </span>
      ),
    },
    {
      header: 'Operator Role',
      accessorKey: 'user_role',
      cell: (row) => (
        <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-300 font-medium text-xs">
          <Shield className="h-3 w-3 text-blue-500" />
          {row.user_role || 'Planner'}
        </span>
      ),
    },
    {
      header: 'Timestamp (UTC)',
      accessorKey: 'created_at',
      cell: (row) => (
        <span className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
          {new Date(row.created_at).toLocaleString()}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Enterprise Audit Ledger & Governance
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Tamper-evident, append-only history of all supply-demand planning executions and human decisions
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Recorded Events"
          value={data?.total.toLocaleString() || '0'}
          subtitle="Immutable ledger records"
          icon={<History className="h-4 w-4" />}
        />
        <KpiCard
          title="Audit Ledger"
          value="Append-Only"
          subtitle="Non-repudiable state snapshots"
          icon={<Lock className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="Role Enforcement"
          value="RBAC Active"
          subtitle="Strict permissions per role"
          icon={<Shield className="h-4 w-4" />}
          variant="success"
        />
        <KpiCard
          title="Idempotency"
          value="Key Enforced"
          subtitle="Duplicate protection on approvals"
          icon={<CheckCircle2 className="h-4 w-4" />}
          variant="success"
        />
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <Search className="h-3.5 w-3.5" />
          Filter Audit:
        </div>

        <input
          type="text"
          placeholder="Filter Entity (e.g. MitigationDecision)..."
          value={entityFilter}
          onChange={(e) => {
            setEntityFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        <input
          type="text"
          placeholder="Filter Action (e.g. APPROVED)..."
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />

        {(entityFilter || actionFilter) && (
          <button
            onClick={() => {
              setEntityFilter('');
              setActionFilter('');
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
          title="Could not load audit ledger"
          message={(error as any)?.message || 'Database error'}
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

