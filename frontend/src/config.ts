import type { AttentionAreaItem, OperationalRecommendation } from "./types";

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface ScenarioConfig {
  id: string;
  label: string;
  shortLabel: string;
  accent: string;
  soft: string;
  line: string;
  text: string;
}

export const SCENARIOS: ScenarioConfig[] = [
  {
    id: "baseline",
    label: "Baseline — Balanced Operations",
    shortLabel: "Baseline",
    accent: "#2F7D5C",
    soft: "#E9F3EE",
    line: "#BFDBCC",
    text: "#1F5C41",
  },
  {
    id: "staffing_stress",
    label: "Staffing Stress — HPPD & Agency",
    shortLabel: "Staffing Stress",
    accent: "#E8622C",
    soft: "#FDEEE6",
    line: "#F3CBB4",
    text: "#C2410C",
  },
  {
    id: "hospital_transfer_spike",
    label: "Hospital Transfer Spike — Clinical",
    shortLabel: "Transfer Spike",
    accent: "#C4432B",
    soft: "#FBEAE5",
    line: "#EFC0B2",
    text: "#9A2C1B",
  },
  {
    id: "auth_cliff",
    label: "Authorization Cliff — Payer/Rehab",
    shortLabel: "Authorization Cliff",
    accent: "#7C5CD6",
    soft: "#F1ECFB",
    line: "#DCD0F5",
    text: "#5B3FA6",
  },
  {
    id: "high_census_strain",
    label: "High Census Strain — Capacity",
    shortLabel: "Census Strain",
    accent: "#B17A1A",
    soft: "#FBF2DF",
    line: "#EBD69E",
    text: "#8A5C10",
  },
  {
    id: "therapy_disruption",
    label: "Therapy Disruption — Rehab Delays",
    shortLabel: "Therapy Disruption",
    accent: "#0E7490",
    soft: "#E5F4F8",
    line: "#BBDDE6",
    text: "#0A5A70",
  },
];

export function scenarioById(id: string): ScenarioConfig {
  return SCENARIOS.find((s) => s.id === id) ?? SCENARIOS[0];
}

export interface FacilityAccent {
  id: string;
  name: string;
  color: string;
}

export const FACILITY_ACCENTS: Record<string, FacilityAccent> = {
  "ignite-oak-brook": { id: "ignite-oak-brook", name: "Oak Brook", color: "#2563EB" },
  "ignite-mokena": { id: "ignite-mokena", name: "Mokena", color: "#7C3AED" },
  "ignite-kansas-city": { id: "ignite-kansas-city", name: "Kansas City", color: "#0D9488" },
};

export function facilityAccentById(id: string): FacilityAccent {
  return (
    FACILITY_ACCENTS[id] ??
    { id, name: id.replace(/^ignite-/, "").replace(/-/g, " "), color: "#E8622C" }
  );
}

export interface SeverityStyle {
  color: string;
  soft: string;
  line: string;
  label: string;
}

export const SEVERITY_STYLES: Record<Severity, SeverityStyle> = {
  CRITICAL: { color: "#C4432B", soft: "#FBEAE5", line: "#EFC0B2", label: "Critical" },
  HIGH: { color: "#E8622C", soft: "#FDEEE6", line: "#F3CBB4", label: "High" },
  MEDIUM: { color: "#B17A1A", soft: "#FBF2DF", line: "#EBD69E", label: "Medium" },
  LOW: { color: "#4B5566", soft: "#F0ECE3", line: "#E7E1D6", label: "Low" },
};

const DOMAIN_LABELS: Record<string, string> = {
  census: "Census & Capacity",
  admissions_discharges: "Admissions & Discharges",
  length_of_stay: "Length of Stay",
  staffing: "Nursing Staffing",
  therapy: "Therapy",
  payer_auth: "Authorizations",
  hospitality: "Hospitality",
  hospital_transfers: "Transfers",
};

const METRIC_LABELS: Record<string, string> = {
  occupancy_rate_pct: "Occupancy",
  hppd_actual: "Direct care",
  agency_staff_pct: "Agency staffing",
  open_shifts_count: "Open shifts",
  treatment_completion_rate_pct: "Therapy completion",
  expiring_authorizations_48h: "Authorizations expiring (48h)",
  acute_transfers_this_week: "Acute transfers (week)",
  readmission_rate_30d_pct: "Readmission rate (30d)",
  los_outliers_count: "LOS outliers",
  net_flow: "Net patient flow",
  dining_satisfaction_score: "Dining satisfaction",
  guest_satisfaction_nps: "Guest NPS",
};

const METRIC_SHORT_TITLES: Record<string, string> = {
  occupancy_rate_pct: "Occupancy",
  hppd_actual: "Nursing coverage",
  agency_staff_pct: "Agency utilization",
  open_shifts_count: "Open shifts",
  treatment_completion_rate_pct: "Therapy completion",
  expiring_authorizations_48h: "Authorization cliff",
  acute_transfers_this_week: "Acute transfers",
  readmission_rate_30d_pct: "Readmission rate",
  los_outliers_count: "Length-of-stay outliers",
  net_flow: "Patient flow",
  dining_satisfaction_score: "Dining satisfaction",
  guest_satisfaction_nps: "Guest satisfaction",
};

export function domainLabel(domain: string): string {
  return DOMAIN_LABELS[domain] ?? domain.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function metricLabel(metric: string): string {
  return METRIC_LABELS[metric] ?? metric.replace(/_/g, " ");
}

function isCountUnit(unit: string): boolean {
  return ["shifts", "patients", "transfers", "authorizations", "guests"].includes(unit);
}

export function formatMetricValue(value: number, unit: string): string {
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "HPPD") return `${value.toFixed(2)} HPPD`;
  if (unit === "NPS") return `${value >= 0 ? "+" : ""}${value} NPS`;
  if (unit === "days") return `${value.toFixed(1)} days`;
  if (isCountUnit(unit)) return `${Math.round(value)} ${unit}`;
  if (unit === "pts") return `${value.toFixed(1)} pts`;
  if (unit) return `${value.toFixed(1)} ${unit}`;
  return `${value}`;
}

export interface FindingRecommendation {
  consider: string;
  whySuggested: string;
  role: string;
  horizon: string;
}

export interface Finding {
  id: string;
  title: string;
  domain: string;
  domainDisplayName: string;
  severity: Severity;
  metricValue: string;
  metricSub: string;
  whatsHappening: string;
  whyItMatters: string;
  driving: string[];
  isCompound: boolean;
  recommendation: FindingRecommendation | null;
  evidence: { label: string; value: string }[];
}

export function horizonLabel(horizon: string): string {
  switch (horizon) {
    case "IMMEDIATE_24H":
      return "Immediate (24h)";
    case "SHORT_TERM_7D":
      return "Short-term (7d)";
    case "STRATEGIC_30D":
      return "Strategic (30d)";
    default:
      return horizon.replace(/_/g, " ");
  }
}

function buildEvidence(item: AttentionAreaItem): { label: string; value: string }[] {
  const current = formatMetricValue(item.current_value, item.unit);
  const target = formatMetricValue(item.threshold_or_target, item.unit);
  const evidence: { label: string; value: string }[] = [
    { label: metricLabel(item.metric_name), value: current },
    { label: "Target", value: target },
  ];
  return evidence;
}

function makeFinding(item: AttentionAreaItem, rec: OperationalRecommendation | null): Finding {
  const current = formatMetricValue(item.current_value, item.unit);
  const target = formatMetricValue(item.threshold_or_target, item.unit);
  return {
    id: item.item_id,
    title: METRIC_SHORT_TITLES[item.metric_name] ?? item.domain_display_name,
    domain: item.domain,
    domainDisplayName: item.domain_display_name,
    severity: item.severity,
    metricValue: current,
    metricSub: `${current} vs ${target}`,
    whatsHappening: item.evidence_statement,
    whyItMatters: item.operational_risk_summary,
    driving: item.related_domains ?? [],
    isCompound: item.is_cross_domain_compound,
    recommendation: rec
      ? {
          consider: rec.suggested_action_description,
          whySuggested: rec.expected_operational_impact,
          role: rec.target_role_or_department,
          horizon: horizonLabel(rec.time_horizon),
        }
      : null,
    evidence: buildEvidence(item),
  };
}

function makeCrossFinding(rec: OperationalRecommendation): Finding {
  const priority: Severity = rec.priority === "HIGH" ? "HIGH" : "MEDIUM";
  return {
    id: rec.recommendation_id,
    title: rec.action_title.replace(/\.\.\.$/, ""),
    domain: rec.domain,
    domainDisplayName: rec.domain_display_name,
    severity: priority,
    metricValue: "",
    metricSub: rec.domain_display_name,
    whatsHappening: rec.rationale,
    whyItMatters: rec.expected_operational_impact,
    driving: [],
    isCompound: true,
    recommendation: {
      consider: rec.suggested_action_description,
      whySuggested: rec.expected_operational_impact,
      role: rec.target_role_or_department,
      horizon: horizonLabel(rec.time_horizon),
    },
    evidence: (rec.supporting_evidence_metrics ?? []).map((e) => ({
      label: "",
      value: e,
    })),
  };
}

export function buildFindings(
  attention: AttentionAreaItem[],
  recommendations: OperationalRecommendation[],
): Finding[] {
  const recByEvidence = new Map<string, OperationalRecommendation>();
  for (const rec of recommendations) {
    if (!recByEvidence.has(rec.rationale)) recByEvidence.set(rec.rationale, rec);
  }

  const findings: Finding[] = attention.map((item) =>
    makeFinding(item, recByEvidence.get(item.evidence_statement) ?? null),
  );

  const used = new Set(attention.map((i) => i.evidence_statement));
  const crossRecs = recommendations.filter((r) => !used.has(r.rationale));
  for (const rec of crossRecs) {
    findings.push(makeCrossFinding(rec));
  }

  return findings;
}
