/**
 * Typed API Client for SyncOps Assistant REST API
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface KPIData {
  name: string;
  value: number;
  unit: string;
  sample_size: number;
  description: string;
}

export interface KPIsResponse {
  sync_success_rate: KPIData;
  recovery_rate: KPIData;
  time_to_recover: KPIData;
  repeat_failure_rate: KPIData;
  sync_related_support_tickets: KPIData & { ticket_to_failure_ratio: number };
  self_service_resolution_rate: KPIData;
  adoption_rate: KPIData;
  calculated_at: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: 'SEV1' | 'SEV2' | 'SEV3' | 'SEV4';
  status: 'DETECTED' | 'INVESTIGATING' | 'MITIGATED' | 'RESOLVED';
  start_time: string;
  affected_cohort: string;
  failure_category: string;
}

export interface DataQualitySummary {
  status: string;
  last_run_id: string | null;
  created_at: string | null;
  total_records: number;
  accepted_records: number;
  rejected_records: number;
  warning_count: number;
  rejection_breakdown: Record<string, number>;
  warning_breakdown: Record<string, number>;
}

export interface ForecastPoint {
  date: string;
  point_forecast: number;
  lower_bound: number;
  upper_bound: number;
}

export interface ForecastResponse {
  target: string;
  target_label: string;
  unit: string;
  status: string;
  model_name: string;
  horizon_days: number;
  historical: { date: string; value: number }[];
  forecast: ForecastPoint[];
  metrics: { mae?: number; rmse?: number; smape?: number };
}

export interface RagCitation {
  source_file: string;
  section_heading: string;
  relevance_score: number;
  chunk_id: string;
}

export interface RagTriageResponse {
  incident_id: string;
  query: string;
  summary: string;
  empirical_facts: string[];
  hypotheses_and_causes: string[];
  recommended_mitigations: string[];
  citations: RagCitation[];
  confidence: number;
  refusal: boolean;
  refusal_reason?: string;
  requires_human_review: boolean;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL.replace(/\/$/, '')}/${endpoint.replace(/^\//, '')}`;
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      throw new Error(`API ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err: any) {
    console.error(`Failed request to ${url}:`, err);
    throw err;
  }
}

export const api = {
  getHealth: () => request<{ status: string; database_connected: boolean; record_counts: Record<string, number> }>('health'),
  getKPIs: (windowHours?: number) => request<KPIsResponse>(windowHours ? `kpis?window_hours=${windowHours}` : 'kpis'),
  getIncidents: (status?: string, severity?: string) => {
    const params = new URLSearchParams();
    if (status && status !== 'ALL') params.append('status', status);
    if (severity && severity !== 'ALL') params.append('severity', severity);
    return request<Incident[]>(`incidents?${params.toString()}`);
  },
  getDataQuality: () => request<DataQualitySummary>('data-quality'),
  getForecast: (target: string = 'failure_rate', horizon: number = 7) =>
    request<ForecastResponse>(`forecast?target=${target}&horizon=${horizon}`),
  postRagTriage: (incidentId?: string, query?: string) =>
    request<RagTriageResponse>('triage/rag', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: incidentId || null, query: query || null, min_score: 0.08, top_k: 3 }),
    }),
};
