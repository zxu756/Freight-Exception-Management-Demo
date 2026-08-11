// Type definitions for the Freight Exception Management System

export interface Shipment {
  id: number;
  shipment_id: string;
  customer_name: string;
  customer_tier: string;
  cargo_description: string;
  cargo_value: number;
  origin: string;
  destination: string;
  transport_mode: string;
  scheduled_pickup: string;
  scheduled_delivery: string;
  sla_deadline: string;
  sla_buffer_hours: number;
  current_status: string;
  current_eta?: string;
  container_id?: string;
  vehicle_id?: string;
  special_requirements?: string;
  created_at: string;
  updated_at: string;
}

export interface Exception {
  id: number;
  exception_id: string;
  shipment_id: string;
  exception_type: string;
  severity: string;
  risk_level: string;
  detected_at: string;
  root_cause?: string;
  ai_diagnosis?: string;
  ai_confidence?: number;
  status: string;
  requires_human_approval: boolean;
  assigned_to?: string;
  resolved_at?: string;
  resolution_time_minutes?: number;
  created_at: string;
}

export interface DecisionOption {
  option_id: string;
  description: string;
  cost: number;
  new_eta: string;
  sla_impact: string;
  risk: string;
  utility_score?: number;
}

export interface Decision {
  decision_id: string;
  exception_id: string;
  decision_type: string;
  options: DecisionOption[];
  recommended_option?: string;
  recommendation_reasoning?: string;
  human_decision?: string;
  human_decision_by?: string;
  human_decision_at?: string;
  decision_outcome?: string;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  status: 'completed' | 'current' | 'pending' | 'alert';
  confidence?: number;
  severity?: string;
}

export interface DemoCase {
  case_number: number;
  risk_level: string;
  shipment_id: string;
  customer: string;
  cargo_value: number;
  exception_id: string;
  exception_type: string;
  status: string;
  severity: string;
  requires_approval: boolean;
  assigned_to?: string;
  resolution_time_minutes?: number;
}

export interface ExceptionStats {
  total_exceptions: number;
  by_status: {
    resolved: number;
    pending_approval: number;
    escalated: number;
  };
  by_risk_level: {
    low: number;
    medium: number;
    high: number;
  };
  metrics: {
    avg_resolution_time_minutes: number;
    auto_resolved_count: number;
    auto_resolved_percentage: number;
  };
}

export type DemoMode = 'auto' | 'step' | 'interactive';

export interface DemoStatus {
  mode: DemoMode | null;
  is_running: boolean;
  current_step: number;
  timestamp: string;
}
