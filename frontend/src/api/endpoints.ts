import { apiClient } from './client';
import {
  AnomalyScanResponse,
  AuditEventRecord,
  DashboardChartsData,
  DashboardKPIs,
  DemandRecord,
  InventoryRecord,
  LoginResponse,
  MitigationComparisonView,
  PaginatedResponse,
  ProductionPlanRecord,
  PurchaseOrderRecord,
  ShortagePABResponse,
  ShortageRecord,
  SupplierRecord,
  UserProfile,
} from '../types';

export const api = {
  // Auth
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const res = await apiClient.post<LoginResponse>('/auth/login', { email, password });
    return res.data;
  },

  getCurrentUser: async (): Promise<UserProfile> => {
    const res = await apiClient.get<UserProfile>('/auth/me');
    return res.data;
  },

  // Dashboard
  getDashboardKPIs: async (): Promise<DashboardKPIs> => {
    const res = await apiClient.get<DashboardKPIs>('/dashboard/kpis');
    return res.data;
  },

  getDashboardCharts: async (): Promise<DashboardChartsData> => {
    const res = await apiClient.get<DashboardChartsData>('/dashboard/charts');
    return res.data;
  },

  // Demand Planning
  getDemand: async (params?: {
    week_bucket?: string;
    sku_id?: string;
    location_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<DemandRecord>> => {
    const res = await apiClient.get<PaginatedResponse<DemandRecord>>('/demand', { params });
    return res.data;
  },

  // Inventory Management
  getInventory: async (params?: {
    category?: string;
    location_code?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<InventoryRecord>> => {
    const res = await apiClient.get<PaginatedResponse<InventoryRecord>>('/inventory', { params });
    return res.data;
  },

  // Supplier Management
  getSuppliers: async (params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<SupplierRecord>> => {
    const res = await apiClient.get<PaginatedResponse<SupplierRecord>>('/suppliers/overview', { params });
    return res.data;
  },

  // Purchase Orders
  getPurchaseOrders: async (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<PurchaseOrderRecord>> => {
    const res = await apiClient.get<PaginatedResponse<PurchaseOrderRecord>>('/purchase-orders', { params });
    return res.data;
  },

  // Production Plans
  getProductionPlans: async (params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ProductionPlanRecord>> => {
    const res = await apiClient.get<PaginatedResponse<ProductionPlanRecord>>('/production-plans', { params });
    return res.data;
  },

  // Shortages Workbench
  getShortages: async (params?: {
    priority?: string;
    root_cause?: string;
    status?: string;
    sku_id?: string;
    location_id?: string;
    sort_by?: string;
    sort_desc?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ShortageRecord>> => {
    const res = await apiClient.get<PaginatedResponse<ShortageRecord>>('/shortages', { params });
    return res.data;
  },

  getShortageDetail: async (shortageId: string): Promise<ShortageRecord> => {
    const res = await apiClient.get<ShortageRecord>(`/shortages/${shortageId}`);
    return res.data;
  },

  getShortagePAB: async (shortageId: string): Promise<ShortagePABResponse> => {
    const res = await apiClient.get<ShortagePABResponse>(`/shortages/${shortageId}/pab`);
    return res.data;
  },

  // Mitigation Planner
  getMitigationTradeoffs: async (shortageId: string): Promise<MitigationComparisonView> => {
    const res = await apiClient.get<MitigationComparisonView>(`/mitigations/shortage/${shortageId}`);
    return res.data;
  },

  submitDecision: async (data: {
    mitigation_option_id: string;
    decision: 'APPROVED' | 'REJECTED' | 'OVERRIDDEN';
    override_qty?: number;
    reason?: string;
  }, idempotencyKey?: string) => {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }
    const res = await apiClient.post('/decisions', data, { headers });
    return res.data;
  },

  // Planning Runs
  triggerPlanningRun: async (scope: string = 'WEEKLY_MRP') => {
    const res = await apiClient.post('/planning-runs', { run_type: scope });
    return res.data;
  },

  getLatestPlanningRun: async () => {
    const res = await apiClient.get('/planning-runs/latest');
    return res.data;
  },

  // Data Quality & Anomalies
  getAnomalies: async (params?: {
    issue_type?: string;
    entity_type?: string;
    severity?: string;
    page?: number;
    page_size?: number;
  }) => {
    const res = await apiClient.get('/anomalies', { params });
    return res.data;
  },

  triggerAnomalyScan: async (): Promise<AnomalyScanResponse> => {
    const res = await apiClient.post<AnomalyScanResponse>('/anomalies/scan');
    return res.data;
  },

  // Audit Events
  getAuditEvents: async (params?: {
    entity_type?: string;
    action?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<AuditEventRecord>> => {
    const res = await apiClient.get<PaginatedResponse<AuditEventRecord>>('/audit-events', { params });
    return res.data;
  },
};
