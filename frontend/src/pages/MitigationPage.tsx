import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { MitigationComparisonView, MitigationOptionItem } from '../types';
import { Modal } from '../components/common/Modal';
import { PriorityBadge, StatusBadge } from '../components/common/Badge';
import { LoadingSpinner, ErrorBanner } from '../components/common/LoadingSpinner';
import {
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  Truck,
  TrendingUp,
  Layers,
  Sparkles,
  Zap,
  HelpCircle,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import clsx from 'clsx';

export const MitigationPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  // Selected shortage ID from query param or fallback
  const shortageIdParam = searchParams.get('shortageId') || '';

  // Fetch list of active shortages for selection dropdown
  const { data: shortagesData } = useQuery({
    queryKey: ['active-shortages-for-mitigation'],
    queryFn: () => api.getShortages({ page: 1, page_size: 50, priority: 'CRITICAL' }),
  });

  const activeShortageId =
    shortageIdParam || (shortagesData?.items && shortagesData.items[0]?.id) || '';

  // Fetch trade-offs for the active shortage
  const {
    data: comparison,
    isLoading,
    error,
    refetch,
  } = useQuery<MitigationComparisonView>({
    queryKey: ['mitigation-tradeoffs', activeShortageId],
    queryFn: () => api.getMitigationTradeoffs(activeShortageId),
    enabled: Boolean(activeShortageId),
  });

  // Rejection Modal State
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedOptionForReject, setSelectedOptionForReject] = useState<MitigationOptionItem | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Override Modal State
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [selectedOptionForOverride, setSelectedOptionForOverride] = useState<MitigationOptionItem | null>(null);
  const [overrideQty, setOverrideQty] = useState<number>(0);
  const [overrideReason, setOverrideReason] = useState('');

  // Notification State
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  // Decision Mutation
  const decisionMutation = useMutation({
    mutationFn: (payload: {
      mitigation_option_id: string;
      decision: 'APPROVED' | 'REJECTED' | 'OVERRIDDEN';
      override_qty?: number;
      reason?: string;
    }) => api.submitDecision(payload, `DEC-${Date.now()}`),
    onSuccess: (data) => {
      setActionNotice(data.message || 'Decision registered successfully.');
      queryClient.invalidateQueries({ queryKey: ['mitigation-tradeoffs', activeShortageId] });
      queryClient.invalidateQueries({ queryKey: ['shortages-workbench'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard-kpis'] });
      setTimeout(() => setActionNotice(null), 5000);
    },
    onError: (err: any) => {
      alert(`Action failed: ${err.response?.data?.message || err.message}`);
    },
  });

  const handleApprove = (opt: MitigationOptionItem) => {
    decisionMutation.mutate({
      mitigation_option_id: opt.id,
      decision: 'APPROVED',
    });
  };

  const handleConfirmReject = () => {
    if (!selectedOptionForReject) return;
    decisionMutation.mutate({
      mitigation_option_id: selectedOptionForReject.id,
      decision: 'REJECTED',
      reason: rejectReason || 'Declined by supply planner',
    });
    setRejectModalOpen(false);
    setSelectedOptionForReject(null);
    setRejectReason('');
  };

  const handleConfirmOverride = () => {
    if (!selectedOptionForOverride) return;
    decisionMutation.mutate({
      mitigation_option_id: selectedOptionForOverride.id,
      decision: 'OVERRIDDEN',
      override_qty: overrideQty,
      reason: overrideReason || 'Planner quantity override',
    });
    setOverrideModalOpen(false);
    setSelectedOptionForOverride(null);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const renderOptionCard = (
    opt: MitigationOptionItem,
    badgeText: string,
    badgeColor: string,
    badgeIcon: React.ReactNode
  ) => {
    const isApproved = opt.status === 'APPROVED';
    const isRejected = opt.status === 'REJECTED';

    return (
      <div
        key={opt.id}
        className={clsx(
          'relative flex flex-col justify-between rounded-2xl border p-5 transition-all shadow-xs',
          isApproved
            ? 'border-emerald-500 bg-emerald-50/20 dark:bg-emerald-950/20 ring-1 ring-emerald-500'
            : isRejected
            ? 'border-slate-200 dark:border-slate-800 opacity-60 bg-slate-50 dark:bg-slate-900'
            : 'border-slate-200/80 bg-white dark:border-slate-800 dark:bg-slate-900 hover:shadow-md'
        )}
      >
        <div>
          {/* Header pill */}
          <div className="flex items-center justify-between mb-3">
            <span
              className={clsx(
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-bold tracking-wide uppercase',
                badgeColor
              )}
            >
              {badgeIcon}
              {badgeText}
            </span>
            <StatusBadge status={opt.status} />
          </div>

          <h4 className="text-sm font-bold text-slate-900 dark:text-white">
            {opt.action_type.replace(/_/g, ' ')}
          </h4>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            {opt.description}
          </p>

          {/* Key Metrics Grid */}
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Recovered</span>
              <p className="font-bold text-emerald-600 dark:text-emerald-400 text-sm">
                +{opt.recoverable_qty.toLocaleString()} units
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Cost</span>
              <p className="font-bold text-slate-900 dark:text-white text-sm">
                {formatCurrency(opt.total_cost)}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Arrival Date</span>
              <p className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1">
                <Clock className="h-3 w-3 text-slate-400" />
                {opt.estimated_availability_date
                  ? new Date(opt.estimated_availability_date).toLocaleDateString()
                  : 'Immediate'}
              </p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-2.5">
              <span className="text-[10px] text-slate-400 uppercase font-semibold">Service Impact</span>
              <p className="font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                {opt.service_level_impact_pct}%
              </p>
            </div>
          </div>

          {/* Feasibility Rationale */}
          <div className="mt-4 rounded-lg border border-slate-100 bg-slate-50/50 p-3 text-xs dark:border-slate-800 dark:bg-slate-800/40">
            <div className="flex items-center gap-1 font-semibold text-slate-700 dark:text-slate-300 mb-1">
              <HelpCircle className="h-3.5 w-3.5 text-blue-500" />
              Engine Feasibility Analysis
            </div>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              {opt.decision_rationale ||
                (opt.is_feasible
                  ? 'All supplier capacity, lead time, and MOQ requirements satisfied.'
                  : `Infeasible: ${(opt.infeasibility_reasons || []).join(', ')}`)}
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 flex items-center gap-2">
          {isApproved ? (
            <div className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 font-semibold text-xs">
              <CheckCircle2 className="h-4 w-4" />
              Recommendation Approved & Executed
            </div>
          ) : isRejected ? (
            <div className="w-full flex items-center justify-center gap-1.5 py-2 rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 font-medium text-xs">
              <XCircle className="h-4 w-4" />
              Recommendation Rejected
            </div>
          ) : (
            <>
              <button
                onClick={() => handleApprove(opt)}
                disabled={decisionMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-blue-600 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 active:bg-blue-800 disabled:opacity-50 transition-colors"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Approve
              </button>
              <button
                onClick={() => {
                  setSelectedOptionForReject(opt);
                  setRejectModalOpen(true);
                }}
                disabled={decisionMutation.isPending}
                className="rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 dark:border-rose-900/60 dark:bg-slate-800 dark:text-rose-400 dark:hover:bg-rose-950/40 transition-colors"
              >
                Reject
              </button>
              <button
                onClick={() => {
                  setSelectedOptionForOverride(opt);
                  setOverrideQty(opt.recoverable_qty);
                  setOverrideModalOpen(true);
                }}
                disabled={decisionMutation.isPending}
                title="Override allocation quantity"
                className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Shortage Mitigation & Decision Center
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Multi-objective trade-off comparison engine powered by Google OR-Tools optimization
          </p>
        </div>

        {/* Shortage Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">
            Active Shortage:
          </span>
          <select
            value={activeShortageId}
            onChange={(e) => setSearchParams({ shortageId: e.target.value })}
            className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 max-w-xs"
          >
            {(shortagesData?.items || []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.business_id} - {s.sku_code} (-{s.shortage_qty.toLocaleString()}u)
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionNotice && (
        <div className="flex items-center gap-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 p-4 text-xs font-semibold text-emerald-800 dark:text-emerald-300 animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
          {actionNotice}
        </div>
      )}

      {isLoading ? (
        <LoadingSpinner text="Computing OR-Tools mitigation candidate frontiers..." size="lg" />
      ) : error ? (
        <ErrorBanner
          title="Could not evaluate mitigations"
          message={(error as any)?.message || 'Database error'}
          onRetry={() => refetch()}
        />
      ) : !comparison ? (
        <div className="text-center py-12 text-slate-400 text-xs">
          Select an active shortage to inspect candidate solutions.
        </div>
      ) : (
        <div className="space-y-6">
          {/* Active Shortage Banner */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-blue-200/60 bg-blue-50/50 p-4 dark:border-blue-900/40 dark:bg-blue-950/20 text-xs">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-600 p-2 text-white">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 dark:text-white text-sm">
                    {comparison.shortage_business_id}
                  </span>
                  <PriorityBadge priority={comparison.priority} size="sm" />
                </div>
                <p className="text-slate-600 dark:text-slate-400 mt-0.5">
                  Required Date: {new Date(comparison.required_date).toLocaleDateString()} | Net Deficit:{' '}
                  <span className="font-bold text-rose-600 dark:text-rose-400">
                    -{comparison.deficit_qty.toLocaleString()} units
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-slate-700 dark:text-slate-300">
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400">Feasible Options</span>
                <p className="font-bold text-sm text-blue-600 dark:text-blue-400">
                  {comparison.all_candidates.filter((c) => c.is_feasible).length} of{' '}
                  {comparison.all_candidates.length}
                </p>
              </div>
            </div>
          </div>

          {/* 4-Way Trade-off Comparisons Grid */}
          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">
              Strategic Trade-Off Frontiers
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              {comparison.recommended_option &&
                renderOptionCard(
                  comparison.recommended_option,
                  'Recommended (Optimal)',
                  'bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200',
                  <Sparkles className="h-3 w-3 text-blue-600" />
                )}

              {comparison.cheapest_option &&
                renderOptionCard(
                  comparison.cheapest_option,
                  'Cheapest Option',
                  'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200',
                  <DollarSign className="h-3 w-3 text-emerald-600" />
                )}

              {comparison.fastest_option &&
                renderOptionCard(
                  comparison.fastest_option,
                  'Fastest Recovery',
                  'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200',
                  <Zap className="h-3 w-3 text-amber-600" />
                )}

              {comparison.best_service_option &&
                renderOptionCard(
                  comparison.best_service_option,
                  'Best Service Recovery',
                  'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200',
                  <TrendingUp className="h-3 w-3 text-purple-600" />
                )}
            </div>
          </div>

          {/* Full Candidates Table */}
          <div className="rounded-xl border border-slate-200/80 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 shadow-xs">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-3">
              All Evaluated Candidate Solutions ({comparison.all_candidates.length})
            </h3>
            <div className="overflow-x-auto text-xs">
              <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-slate-800/80 font-semibold text-slate-600 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                  <tr>
                    <th className="px-3 py-2.5">Action Lever</th>
                    <th className="px-3 py-2.5">Candidate Description</th>
                    <th className="px-3 py-2.5">Recoverable Qty</th>
                    <th className="px-3 py-2.5">Total Cost</th>
                    <th className="px-3 py-2.5">ETA</th>
                    <th className="px-3 py-2.5">Service %</th>
                    <th className="px-3 py-2.5">Status</th>
                    <th className="px-3 py-2.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {comparison.all_candidates.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="px-3 py-2.5 font-semibold text-slate-900 dark:text-white">
                        {c.action_type.replace(/_/g, ' ')}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                        {c.description}
                      </td>
                      <td className="px-3 py-2.5 font-bold text-emerald-600 dark:text-emerald-400">
                        +{c.recoverable_qty.toLocaleString()}
                      </td>
                      <td className="px-3 py-2.5 font-semibold text-slate-900 dark:text-white">
                        {formatCurrency(c.total_cost)}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600 dark:text-slate-400">
                        {c.estimated_availability_date
                          ? new Date(c.estimated_availability_date).toLocaleDateString()
                          : 'Immediate'}
                      </td>
                      <td className="px-3 py-2.5 font-medium text-blue-600 dark:text-blue-400">
                        {c.service_level_impact_pct}%
                      </td>
                      <td className="px-3 py-2.5">
                        <StatusBadge status={c.status} size="sm" />
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {c.status === 'PROPOSED' ? (
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleApprove(c)}
                              className="rounded-md bg-blue-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-blue-700"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() => {
                                setSelectedOptionForReject(c);
                                setRejectModalOpen(true);
                              }}
                              className="rounded-md border border-rose-200 px-2 py-1 text-[11px] font-medium text-rose-600 hover:bg-rose-50 dark:border-rose-900"
                            >
                              Reject
                            </button>
                          </div>
                        ) : (
                          <span className="text-slate-400 text-[11px] italic">Decided</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Reject Modal with Reason Capture */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Mitigation Recommendation"
        subtitle={
          selectedOptionForReject
            ? `Option ${selectedOptionForReject.action_type.replace(/_/g, ' ')}`
            : undefined
        }
        maxWidth="md"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Please capture the business rationale for rejecting this recommendation. An immutable audit record will be logged.
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Rejection Reason:
            </label>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Expedite freight costs exceed budget threshold; commercial team negotiated delayed delivery..."
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-rose-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setRejectModalOpen(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmReject}
              disabled={decisionMutation.isPending}
              className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
            >
              Confirm Rejection
            </button>
          </div>
        </div>
      </Modal>

      {/* Override Modal */}
      <Modal
        isOpen={overrideModalOpen}
        onClose={() => setOverrideModalOpen(false)}
        title="Override Mitigation Allocation Quantity"
        maxWidth="md"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Adjust the allocated quantity for this mitigation solution.
          </p>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Allocated Quantity (Units):
            </label>
            <input
              type="number"
              value={overrideQty}
              onChange={(e) => setOverrideQty(Number(e.target.value))}
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Override Justification:
            </label>
            <input
              type="text"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. Partial shipment accepted due to truckload volume..."
              className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setOverrideModalOpen(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirmOverride}
              className="rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
            >
              Apply Override
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

