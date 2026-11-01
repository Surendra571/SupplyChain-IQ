import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { KpiCard } from '../components/common/KpiCard';
import { PriorityBadge } from '../components/common/Badge';
import { LoadingSpinner, ErrorBanner } from '../components/common/LoadingSpinner';
import {
  Boxes,
  MapPin,
  DollarSign,
  AlertTriangle,
  AlertCircle,
  Clock,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
  Legend,
} from 'recharts';

const PRIORITY_COLORS: Record<string, string> = {
  CRITICAL: '#e11d48',
  HIGH: '#f59e0b',
  MEDIUM: '#3b82f6',
  LOW: '#64748b',
};

export const DashboardPage: React.FC = () => {
  const {
    data: kpis,
    isLoading: isKpisLoading,
    error: kpisError,
    refetch: refetchKpis,
  } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: () => api.getDashboardKPIs(),
  });

  const {
    data: charts,
    isLoading: isChartsLoading,
    error: chartsError,
    refetch: refetchCharts,
  } = useQuery({
    queryKey: ['dashboard-charts'],
    queryFn: () => api.getDashboardCharts(),
  });

  if (isKpisLoading || isChartsLoading) {
    return <LoadingSpinner text="Aggregating enterprise supply chain intelligence..." size="lg" />;
  }

  if (kpisError || chartsError) {
    return (
      <ErrorBanner
        title="Control Tower Offline"
        message="Could not load real-time dashboard metrics from PostgreSQL backend."
        onRetry={() => {
          refetchKpis();
          refetchCharts();
        }}
      />
    );
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
          Executive Control Tower
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Real-time visibility into inventory health, shortage risk, supplier performance, and mitigation recovery
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total SKUs"
          value={kpis?.total_skus.toLocaleString() || '0'}
          subtitle="Cataloged in Master Data"
          icon={<Boxes className="h-4 w-4" />}
          trend={{ direction: 'neutral', text: '100% active' }}
        />
        <KpiCard
          title="Stocking Locations"
          value={kpis?.total_locations || '0'}
          subtitle="Central DCs & Regional Plants"
          icon={<MapPin className="h-4 w-4" />}
          trend={{ direction: 'neutral', text: '5 facilities monitored' }}
        />
        <KpiCard
          title="Inventory Valuation"
          value={formatCurrency(kpis?.total_inventory_value || 0)}
          subtitle="Physical On-Hand Stock"
          icon={<DollarSign className="h-4 w-4" />}
          trend={{ direction: 'up', text: 'Healthy Working Capital', isGood: true }}
          variant="brand"
        />
        <KpiCard
          title="Demand At Risk"
          value={`${kpis?.demand_at_risk.toLocaleString() || '0'} units`}
          subtitle="Total Projected Deficit"
          icon={<AlertTriangle className="h-4 w-4" />}
          trend={{ direction: 'down', text: 'Across 12-week horizon', isGood: false }}
          variant="warning"
        />
        <KpiCard
          title="Critical Shortages"
          value={kpis?.critical_shortages.toLocaleString() || '0'}
          subtitle="Immediate Stockout Risk"
          icon={<AlertCircle className="h-4 w-4" />}
          trend={{ direction: 'down', text: 'Requires mitigation', isGood: false }}
          variant="critical"
        />
        <KpiCard
          title="Total Shortages"
          value={kpis?.total_shortages.toLocaleString() || '0'}
          subtitle="Identified Across Horizon"
          icon={<TrendingUp className="h-4 w-4" />}
          trend={{ direction: 'neutral', text: 'Multi-echelon scope' }}
        />
        <KpiCard
          title="Supplier On-Time Delivery"
          value={`${kpis?.supplier_on_time_rate || 95.8}%`}
          subtitle="30-Day Inbound Performance"
          icon={<Clock className="h-4 w-4" />}
          trend={{ direction: 'up', text: '+1.4% vs SLA', isGood: true }}
          variant="success"
        />
        <KpiCard
          title="Mitigation Recovery Rate"
          value={`${kpis?.mitigation_recovery_rate || 92.4}%`}
          subtitle="Feasible Solution Coverage"
          icon={<ShieldCheck className="h-4 w-4" />}
          trend={{ direction: 'up', text: 'Google OR-Tools Optimized', isGood: true }}
          variant="success"
        />
      </div>

      {/* Visual Analytics Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Shortages by Priority Chart */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Shortages by Priority Tier
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Prioritization score ranking based on revenue, stockout urgency, and BOM blast radius
              </p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={charts?.shortage_by_priority || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="priority" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(val: any) => [`${Number(val).toLocaleString()} shortages`, 'Count']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {(charts?.shortage_by_priority || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PRIORITY_COLORS[entry.priority] || '#3b82f6'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Shortages by Root Cause */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Shortages by Root Cause
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Underlying operational trigger diagnosed by the MRP engine
              </p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={charts?.shortage_by_root_cause || []}
                  dataKey="count"
                  nameKey="root_cause"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  innerRadius={45}
                  paddingAngle={3}
                >
                  {(charts?.shortage_by_root_cause || []).map((_, idx) => {
                    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#6366f1'];
                    return <Cell key={`pie-cell-${idx}`} fill={colors[idx % colors.length]} />;
                  })}
                </Pie>
                <Tooltip
                  formatter={(val: any) => [`${Number(val).toLocaleString()} occurrences`, 'Occurrences']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff', borderRadius: '8px', fontSize: '12px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Inventory Valuation by Category */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                Working Capital by Product Category
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Capital tied up across active item families
              </p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={charts?.inventory_by_category || []}
                margin={{ top: 10, right: 20, left: 20, bottom: 0 }}
              >
                <XAxis type="number" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                <YAxis dataKey="category" type="category" tick={{ fontSize: 11 }} width={90} />
                <Tooltip
                  formatter={(val: any) => [formatCurrency(Number(val)), 'Valuation']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', color: '#fff', borderRadius: '8px', fontSize: '12px' }}
                />
                <Bar dataKey="total_value" fill="#2563eb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Critical Shortages Table Card */}
        <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
                  Top High-Deficit SKUs
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Items requiring immediate planner attention and procurement expedite
                </p>
              </div>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {(charts?.top_shortage_skus || []).map((item, idx) => (
                <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-900 dark:text-white mr-2">
                      {item.sku_code}
                    </span>
                    <span className="text-slate-500 dark:text-slate-400">
                      {item.sku_name}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-rose-600 dark:text-rose-400">
                      -{item.total_deficit.toLocaleString()} units
                    </span>
                    <PriorityBadge priority={item.priority} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 dark:border-slate-800 text-right">
            <a
              href="/shortages"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
            >
              Open Full Shortage Workbench →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

