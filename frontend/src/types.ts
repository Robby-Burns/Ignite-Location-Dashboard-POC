export interface FacilityBriefHeader {
  facility_id: string;
  facility_name: string;
  location: string;
  report_date: string;
  scenario: string;
  overall_status: "HEALTHY" | "WATCH" | "NEEDS_ATTENTION" | "CRITICAL";
  status_label: string;
  executive_summary: string;
}

export interface BriefVitalMetric {
  metric_name: string;
  label: string;
  formatted_value: string;
  subtitle: string;
  status: "POSITIVE" | "NEUTRAL" | "ATTENTION" | "CRITICAL";
  trend: "UP" | "DOWN" | "STABLE";
}

export interface BriefHighlightCard {
  title: string;
  domain: string;
  plain_language_description: string;
  supporting_metric: string;
  significance: string;
}

export interface BriefWatchItemCard {
  title: string;
  domain: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  plain_language_concern: string;
  supporting_metric: string;
  is_compound_risk: boolean;
  related_domains: string[];
}

export interface BriefActionItemCard {
  priority: "HIGH" | "MEDIUM" | "LOW";
  title: string;
  department: string;
  suggested_action: string;
  why_it_matters: string;
  time_horizon: string;
}

export interface BriefLimitations {
  is_simulated_domo: boolean;
  data_freshness: string;
  disclaimer: string;
  data_completeness_notes: string[];
}

export interface FacilityBriefReport {
  header: FacilityBriefHeader;
  vitals: BriefVitalMetric[];
  positive_highlights: BriefHighlightCard[];
  watch_items: BriefWatchItemCard[];
  action_items: BriefActionItemCard[];
  limitations: BriefLimitations;
  generated_at: string;
}

export interface MetricExplanationDetail {
  metric_name: string;
  display_name: string;
  domain: string;
  current_value_formatted: string;
  plain_language_meaning: string;
  operational_significance: string;
  benchmark_context: string;
}

export interface DomainTrendExplanation {
  domain: string;
  domain_display_name: string;
  headline: string;
  narrative: string;
  trajectory_direction: "INCREASING" | "DECREASING" | "STABLE" | "VOLATILE";
  is_meaningful_shift: boolean;
  cited_metrics: string[];
}

export interface MetricTrendSummary {
  metric_name: string;
  display_name: string;
  domain: string;
  unit: string;
  current_value: number;
  value_7d_ago: number | null;
  value_14d_ago: number | null;
  value_30d_ago: number | null;
  delta_7d: number | null;
  delta_30d: number | null;
  pct_change_7d: number | null;
  pct_change_30d: number | null;
  rolling_7d_avg: number;
  rolling_30d_avg: number;
  min_30d: number;
  max_30d: number;
  trend_direction: "INCREASING" | "DECREASING" | "STABLE" | "VOLATILE";
  is_meaningful_shift: boolean;
  shift_summary: string;
}

export interface FacilityTrendCalculations {
  facility_id: string;
  scenario: string;
  days_analyzed: number;
  is_context_sufficient: boolean;
  trends: Record<string, MetricTrendSummary>;
  meaningful_shifts: string[];
  context_limitations: string[];
}

export interface FacilityTrendExplanationReport {
  facility_id: string;
  facility_name: string;
  analysis_date: string;
  scenario: string;
  analysis_state: "ANALYSIS_COMPLETE" | "AI_ANALYSIS_UNAVAILABLE" | "INSUFFICIENT_CONTEXT";
  executive_trend_summary: string;
  metric_explanations: Record<string, MetricExplanationDetail>;
  trend_explanations: Record<string, DomainTrendExplanation>;
  notable_shifts: string[];
  data_limitations_and_uncertainty: string;
  verified_calculations: FacilityTrendCalculations;
  generated_at: string;
}

export interface OperationalRecommendation {
  recommendation_id: string;
  domain: string;
  domain_display_name: string;
  target_role_or_department: string;
  priority: "HIGH" | "MEDIUM" | "LOW";
  time_horizon: "IMMEDIATE_24H" | "SHORT_TERM_7D" | "STRATEGIC_30D";
  action_title: string;
  suggested_action_description: string;
  rationale: string;
  supporting_evidence_metrics: string[];
  expected_operational_impact: string;
  governance_disclaimer: string;
}

export interface FacilityRecommendationsSummary {
  facility_id: string;
  scenario: string;
  total_recommendations_count: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  recommendations: OperationalRecommendation[];
  calculated_at: string;
}

export interface RecommendationReport {
  facility_id: string;
  facility_name: string;
  snapshot_date: string;
  scenario: string;
  analysis_state: "ANALYSIS_COMPLETE" | "AI_ANALYSIS_UNAVAILABLE" | "INSUFFICIENT_DATA";
  executive_action_plan_overview: string;
  top_priority_recommendations: OperationalRecommendation[];
  departmental_action_items: Record<string, OperationalRecommendation[]>;
  verified_recommendations_summary: FacilityRecommendationsSummary;
  decision_authority_notice: string;
  data_limitations_and_uncertainty: string;
  generated_at: string;
}
