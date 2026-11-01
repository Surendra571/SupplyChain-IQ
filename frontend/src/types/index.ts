export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface DashboardKPIs {
  total_skus: number;
  total_locations: number;
  total_inventory_value: number;
  demand_at_risk: number;
  critical_shortages: number;
  total_shortages: number;
  supplier_on_time_rate: number;
  mitigation_recovery_rate: number;
}

export interface PriorityChartPoint {
  priority: string;
  count: number;
  deficit_qty: number;
}

export interface RootCauseChartPoint {
  root_cause: string;
  count: number;
  deficit_qty: number;
}

export interface CategoryChartPoint {
  category: string;
  total_value: number;
  sku_count: number;
}

export interface TopShortageSKU {
  sku_code: string;
  sku_name: string;
  priority: string;
  total_deficit: number;
}

export interface DashboardChartsData {
  shortage_by_priority: PriorityChartPoint[];
  shortage_by_root_cause: RootCauseChartPoint[];
  inventory_by_category: CategoryChartPoint[];
  top_shortage_skus: TopShortageSKU[];
}

export interface DemandRecord {
  id: string;
  week_bucket: string;
  forecast_qty: number;
  confidence_p50: number;
  confidence_p90: number;
  sku_code: string;
  sku_name: string;
  category: string;
  location_code: string;
  location_name: string;
}

export interface InventoryRecord {
  id: string;
  on_hand_qty: number;
  allocated_qty: number;
  safety_stock_qty: number;
  reorder_point: number;
  available_qty: number;
  total_value: number;
  sku_code: string;
  sku_name: string;
  category: string;
  unit_cost: number;
  location_code: string;
  location_name: string;
  location_type: string;
}

export interface SupplierRecord {
  id: string;
  business_id: string;
  supplier_code: string;
  name: string;
  tier: string;
  country: string;
  lead_time_days: number;
  on_time_delivery_rate: number;
  active_skus_count: number;
  total_capacity: number;
}

export interface PurchaseOrderRecord {
  id: string;
  business_id: string;
  po_number: string;
  status: string;
  order_date: string;
  total_amount: number;
  supplier_code: string;
  supplier_name: string;
  line_count: number;
  total_units: number;
}

export interface ProductionPlanRecord {
  id: string;
  business_id: string;
  week_bucket: string;
  planned_quantity: number;
  status: string;
  work_center_id: string;
  sku_code: string;
  sku_name: string;
  location_code: string;
  location_name: string;
}

export interface ShortageRecord {
  id: string;
  business_id: string;
  planning_run_id: string;
  sku_id: string;
  sku_code?: string;
  sku_name?: string;
  sku_category?: string;
  location_id: string;
  location_code?: string;
  location_name?: string;
  shortage_date: string;
  shortage_qty: number;
  days_until_stockout: number;
  priority_score: number;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  root_cause: string;
  status: 'IDENTIFIED' | 'MITIGATING' | 'RESOLVED' | 'ACCEPTED_RISK';
  recommended_option_id?: string;
  recommended_action?: string;
  recommended_cost?: number;
}

export interface TimePhasedPABPoint {
  week_bucket: string;
  period_start_date: string;
  opening_balance: number;
  forecast_demand: number;
  allocated_qty: number;
  scheduled_receipts: number;
  planned_production: number;
  projected_available_balance: number;
  safety_stock: number;
  net_shortage: number;
}

export interface ShortagePABResponse {
  shortage_id: string;
  sku_code: string;
  sku_name: string;
  location_code: string;
  location_name: string;
  shortage_date: string;
  shortage_qty: number;
  priority: string;
  pab_timeline: TimePhasedPABPoint[];
}

export interface MitigationOptionItem {
  id: string;
  business_id: string;
  shortage_id: string;
  action_type: string;
  description: string;
  supplier_id?: string;
  supplier_name?: string;
  source_location_id?: string;
  source_location_name?: string;
  substitute_sku_id?: string;
  substitute_sku_name?: string;
  recoverable_qty: number;
  unmet_qty: number;
  additional_procurement_cost: number;
  expedite_cost: number;
  transfer_cost: number;
  total_cost: number;
  estimated_availability_date: string;
  service_level_impact_pct: number;
  feasibility_score: number;
  is_feasible: boolean;
  infeasibility_reasons?: string[];
  recommendation_rank: number;
  status: string;
  decision_rationale?: string;
}

export interface MitigationComparisonView {
  shortage_id: string;
  shortage_business_id: string;
  deficit_qty: number;
  required_date: string;
  priority: string;
  recommended_option?: MitigationOptionItem;
  cheapest_option?: MitigationOptionItem;
  fastest_option?: MitigationOptionItem;
  best_service_option?: MitigationOptionItem;
  all_candidates: MitigationOptionItem[];
}

export interface AnomalyIssueItem {
  issue_id: string;
  issue_type: string;
  entity_type: string;
  record_id: string;
  severity: string;
  detection_rule: string;
  expected_result: string;
  actual_result: string;
  detected_at: string;
}

export interface AnomalyScanResponse {
  total_issues: number;
  total_rules_evaluated: number;
  issues_by_category: Record<string, number>;
  metrics?: {
    precision: number;
    recall: number;
    f1_score: number;
    true_positives: number;
    false_positives: number;
    false_negatives: number;
  };
  sample_issues: AnomalyIssueItem[];
}

export interface AuditEventRecord {
  id: string;
  business_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  user_id: string;
  user_role: string;
  old_state?: Record<string, any>;
  new_state?: Record<string, any>;
  created_at: string;
}
