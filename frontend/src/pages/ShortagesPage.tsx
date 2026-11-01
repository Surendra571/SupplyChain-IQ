import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/endpoints';
import { DataTable, Column } from '../components/common/DataTable';
import { ShortageRecord, ShortagePABResponse } from '../types';
import { PriorityBadge, StatusBadge } from '../components/common/Badge';
import { KpiCard } from '../components/common/KpiCard';
import { Modal } from '../components/common/Modal';
import { ErrorBanner, LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  AlertTriangle,
  Calendar,
  Clock,
  ArrowRight,
  Filter,
  BarChart3,
  Layers,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';

export const ShortagesPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [priorityFilter, setPriorityFilter] = useState(() => localStorage.getItem('sciq_filter_priority') || '');
  const [rootCauseFilter, setRootCauseFilter] = useState(() => localStorage.getItem('sciq_filter_root_cause') || '');
  const [statusFilter, setStatusFilter] = useState(() => localStorage.getItem('sciq_filter_status') || '');
  const [sortBy, setSortBy] = useState('priority_score');
  const [sortDesc, setSortDesc] = useState(true);

  const handlePriorityFilterChange = (val: string) => {
    setPriorityFilter(val);
    localStorage.setItem('sciq_filter_priority', val);
    setPage(1);
  };

  const handleRootCauseFilterChange = (val: string) => {
    setRootCauseFilter(val);
    localStorage.setItem('sciq_filter_root_cause', val);
    setPage(1);
  };

  const handleStatusFilterChange = (val: string) => {
    setStatusFilter(val);
    localStorage.setItem('sciq_filter_status', val);
    setPage(1);
  };

  // Modal State for PAB Curve
  const [selectedShortageId, setSelectedShortageId] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['shortages-workbench', page, priorityFilter, rootCauseFilter, statusFilter, sortBy, sortDesc],
    queryFn: () =>
      api.getShortages({
        page,
        page_size: 25,
        priority: priorityFilter || undefined,
        root_cause: rootCauseFilter || undefined,
        status: statusFilter || undefined,
        sort_by: sortBy,
        sort_desc: sortDesc,
      }),
  });

  const {
    data: pabData,
    isLoading: isPabLoading,
    error: pabError,
  } = useQuery<ShortagePABResponse>({
    queryKey: ['shortage-pab', selectedShortageId],
    queryFn: () => api.getShortagePAB(selectedShortageId!),
    enabled: Boolean(selectedShortageId),
  });

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortBy(field);
      setSortDesc(true);
    }
  };

  const columns: Column<ShortageRecord>[] = [
    {
      header: 'Shortage ID',
      accessorKey: 'business_id',
      sortable: true,
      cell: (row) => (
        <span className="font-mono font-semibold text-blue-600 dark:text-blue-400">
          {row.business_id}
        </span>
      ),
    },
    {
      header: 'SKU Item',
      cell: (row) => (
        <div>
          <span className="font-semibold text-slate-900 dark:text-white">{row.sku_code || 'SKU'}</span>
          <p className="text-xs text-slate-500 dark:text-slate-400">{row.sku_name || '-'}</p>
        </div>
      ),
    },
    {
      header: 'Location',
      cell: (row) => (
        <div>
          <span className="font-medium text-slate-800 dark:text-slate-200">
            {row.location_code || 'LOC'}
          </span>
          <p className="text-[10px] text-slate-400 dark:text-slate-500">
            {row.location_name || '-'}
          </p>
        </div>
      ),
    },
    {
      header: 'Deficit Qty',
      accessorKey: 'shortage_qty',
      sortable: true,
      cell: (row) => (
        <span className="font-bold text-rose-600 dark:text-rose-400">
          -{row.shortage_qty.toLocaleString()} units
        </span>
      ),
    },
    {
      header: 'Stockout Date',
      accessorKey: 'shortage_date',
      sortable: true,
      cell: (row) => (
        <div className="flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
          <Calendar className="h-3.5 w-3.5 text-slate-400" />
          {new Date(row.shortage_date).toLocaleDateString()}
        </div>
      ),
    },
    {
      header: 'Days to Stockout',
      accessorKey: 'days_until_stockout',
      sortable: true,
      cell: (row) => {
        const d = row.days_until_stockout;
        return (
          <span
            className={`font-semibold ${
              d <= 7
                ? 'text-rose-600 dark:text-rose-400 font-bold'
                : d <= 21
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-slate-700 dark:text-slate-300'
            }`}
          >
            {d} days
          </span>
        );
      },
    },
    {
      header: 'Root Cause',
      accessorKey: 'root_cause',
      cell: (row) => (
        <span className="rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300">
          {row.root_cause.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      header: 'Priority',
      accessorKey: 'priority',
      sortable: true,
      cell: (row) => <PriorityBadge priority={row.priority} />,
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: 'Actions',
      cell: (row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedShortageId(row.id)}
            title="Inspect 12-week time-phased PAB simulation"
            className="flex items-center gap-1 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <BarChart3 className="h-3 w-3 text-blue-500" />
            PAB
          </button>
          <button
            onClick={() => navigate(`/mitigations?shortageId=${row.id}`)}
            title="Evaluate and approve mitigation candidates"
            className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors"
          >
            Mitigate
            <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Shortage Workbench & Prioritization
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Time-phased projected deficits ranked by financial impact, urgency, and customer criticality
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Active Shortages"
          value={data?.total.toLocaleString() || '0'}
          subtitle="Identified across all locations"
          icon={<AlertTriangle className="h-4 w-4" />}
          variant="critical"
        />
        <KpiCard
          title="Critical Tier"
          value={
            (data?.items || []).filter((s) => s.priority === 'CRITICAL').length.toLocaleString()
          }
          subtitle="Immediate stockout threat"
          icon={<Clock className="h-4 w-4" />}
          variant="warning"
        />
        <KpiCard
          title="Scoring Model"
          value="4-Factor Multi-Weight"
          subtitle="Days-to-stockout + Revenue + BOM"
          icon={<Layers className="h-4 w-4" />}
          variant="brand"
        />
        <KpiCard
          title="Mitigation Status"
          value="Engine Feasible"
          subtitle="Candidates generated via OR-Tools"
          icon={<BarChart3 className="h-4 w-4" />}
          variant="success"
        />
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200/80 bg-white p-3 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400">
          <Filter className="h-3.5 w-3.5" />
          Filters:
        </div>

        {/* Priority Filter */}
        <select
          value={priorityFilter}
          onChange={(e) => handlePriorityFilterChange(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Priorities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
        </select>

        {/* Root Cause Filter */}
        <select
          value={rootCauseFilter}
          onChange={(e) => handleRootCauseFilterChange(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Root Causes</option>
          <option value="DEMAND_SPIKE">Demand Spike</option>
          <option value="SUPPLIER_DELAY">Supplier Delay</option>
          <option value="CAPACITY_CONSTRAINT">Capacity Constraint</option>
          <option value="INSUFFICIENT_OPENING_STOCK">Insufficient Opening Stock</option>
          <option value="BOM_COMPONENT_SHORTAGE">BOM Component Shortage</option>
        </select>

        {/* Status Filter */}
        <select
          value={statusFilter}
          onChange={(e) => handleStatusFilterChange(e.target.value)}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="IDENTIFIED">Identified</option>
          <option value="MITIGATING">Mitigating</option>
          <option value="RESOLVED">Resolved</option>
          <option value="ACCEPTED_RISK">Accepted Risk</option>
        </select>

        {(priorityFilter || rootCauseFilter || statusFilter) && (
          <button
            onClick={() => {
              setPriorityFilter('');
              setRootCauseFilter('');
              setStatusFilter('');
              setPage(1);
            }}
            className="text-xs font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Main Shortages Data Table */}
      {error ? (
        <ErrorBanner
          title="Could not load shortages"
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
          sortBy={sortBy}
          sortDesc={sortDesc}
          onSortChange={handleSort}
        />
      )}

      {/* 12-Week Time-Phased PAB Interactive Modal Drilldown */}
      <Modal
        isOpen={Boolean(selectedShortageId)}
        onClose={() => setSelectedShortageId(null)}
        title="Projected Available Balance (PAB) 12-Week Simulation"
        subtitle={
          pabData
            ? `${pabData.sku_code} (${pabData.sku_name}) @ ${pabData.location_code} - Net Deficit: ${pabData.shortage_qty.toLocaleString()} units`
            : 'Loading time-phased balance...'
        }
        maxWidth="4xl"
      >
        {isPabLoading ? (
          <LoadingSpinner text="Computing time-phased inventory curve..." size="md" />
        ) : pabError ? (
          <ErrorBanner message="Failed to load time-phased simulation." />
        ) : (
          <div className="space-y-5">
            {/* Chart Area */}
            <div className="rounded-xl border border-slate-200/80 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={pabData?.pab_timeline || []}
                    margin={{ top: 20, right: 20, bottom: 20, left: 10 }}
                  >
                    <XAxis dataKey="week_bucket" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#1e293b',
                        color: '#fff',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <ReferenceLine y={0} stroke="#e11d48" strokeDasharray="3 3" />
                    <Bar
                      dataKey="forecast_demand"
                      name="Forecast Demand"
                      fill="#94a3b8"
                      opacity={0.4}
                    />
                    <Bar
                      dataKey="scheduled_receipts"
                      name="Inbound Receipts"
                      fill="#10b981"
                      opacity={0.7}
                    />
                    <Line
                      type="monotone"
                      dataKey="projected_available_balance"
                      name="Projected Balance (PAB)"
                      stroke="#2563eb"
                      strokeWidth={3}
                      dot={{ r: 4 }}
                    />
                    <Line
                      type="stepAfter"
                      dataKey="safety_stock"
                      name="Safety Stock Buffer"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      strokeDasharray="4 4"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Weekly Ledger Breakdown Table */}
            <div className="overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800 text-xs">
              <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/80 font-semibold text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-3 py-2">Week</th>
                    <th className="px-3 py-2">Opening</th>
                    <th className="px-3 py-2">Receipts</th>
                    <th className="px-3 py-2">Production</th>
                    <th className="px-3 py-2">Demand</th>
                    <th className="px-3 py-2">Allocations</th>
                    <th className="px-3 py-2 font-bold text-blue-600 dark:text-blue-400">PAB</th>
                    <th className="px-3 py-2">Safety Stock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {(pabData?.pab_timeline || []).map((row, idx) => (
                    <tr
                      key={idx}
                      className={
                        row.projected_available_balance < 0
                          ? 'bg-rose-50/40 dark:bg-rose-950/20'
                          : undefined
                      }
                    >
                      <td className="px-3 py-2 font-semibold">{row.week_bucket}</td>
                      <td className="px-3 py-2">{row.opening_balance.toLocaleString()}</td>
                      <td className="px-3 py-2 text-emerald-600 dark:text-emerald-400 font-medium">
                        +{row.scheduled_receipts.toLocaleString()}
                      </td>
                      <td className="px-3 py-2">+{row.planned_production.toLocaleString()}</td>
                      <td className="px-3 py-2 text-rose-600 dark:text-rose-400">
                        -{row.forecast_demand.toLocaleString()}
                      </td>
                      <td className="px-3 py-2">-{row.allocated_qty.toLocaleString()}</td>
                      <td
                        className={`px-3 py-2 font-bold ${
                          row.projected_available_balance < 0
                            ? 'text-rose-600 dark:text-rose-400'
                            : 'text-slate-900 dark:text-white'
                        }`}
                      >
                        {row.projected_available_balance.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-slate-500 dark:text-slate-400">
                        {row.safety_stock.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setSelectedShortageId(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  const sId = selectedShortageId;
                  setSelectedShortageId(null);
                  navigate(`/mitigations?shortageId=${sId}`);
                }}
                className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 transition-colors"
              >
                Proceed to Mitigation Planner
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

