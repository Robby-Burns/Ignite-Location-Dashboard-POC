import React, { useState } from "react";
import {
  AlertTriangle,
  Clock,
  CheckSquare,
  ShieldCheck,
  Building2,
  Users,
  Activity,
  Utensils,
  Layers,
  History,
  AlertOctagon,
  TrendingUp,
  Sparkles,
  Calendar,
  Filter
} from "lucide-react";
import {
  RecommendationReport,
  OperationalRecommendation
} from "../types";

interface RecommendationsViewProps {
  data: RecommendationReport | null;
  loading: boolean;
  error: string | null;
}

export const RecommendationsView: React.FC<RecommendationsViewProps> = ({
  data,
  loading,
  error,
}) => {
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [horizonFilter, setHorizonFilter] = useState<string>("all");
  const [departmentFilter, setDepartmentFilter] = useState<string>("all");

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium animate-pulse">
          Synthesizing prioritized cross-departmental recommendations and verifying evidence...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
        <div className="flex items-center space-x-3">
          <AlertOctagon className="w-6 h-6 text-rose-600 flex-shrink-0" />
          <h3 className="text-lg font-bold">Failed to Load Operational Recommendations</h3>
        </div>
        <p className="text-sm text-rose-700">{error || "No recommendation data returned."}</p>
      </div>
    );
  }

  const {
    facility_name,
    snapshot_date,
    scenario,
    executive_action_plan_overview,
    verified_recommendations_summary,
    decision_authority_notice,
    data_limitations_and_uncertainty,
  } = data;

  const allRecommendations: OperationalRecommendation[] =
    verified_recommendations_summary.recommendations || [];

  // Extract unique departments for filter dropdown
  const uniqueDepartments = Array.from(
    new Set(allRecommendations.map((r) => r.target_role_or_department))
  ).sort();

  // Apply multi-dimensional filters
  const filteredRecommendations = allRecommendations.filter((rec) => {
    if (priorityFilter !== "all" && rec.priority !== priorityFilter) return false;
    if (horizonFilter !== "all" && rec.time_horizon !== horizonFilter) return false;
    if (departmentFilter !== "all" && rec.target_role_or_department !== departmentFilter)
      return false;
    return true;
  });

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "HIGH":
        return (
          <span className="flex items-center gap-1 text-xs font-black px-2.5 py-1 rounded-full bg-rose-100 text-rose-800 border border-rose-200 uppercase tracking-wide">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            High Priority
          </span>
        );
      case "MEDIUM":
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-wide">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            Medium Priority
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 border border-blue-200 uppercase tracking-wide">
            <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
            Low / Maintenance
          </span>
        );
    }
  };

  const getTimeHorizonLabel = (horizon: string) => {
    switch (horizon) {
      case "IMMEDIATE_24H":
        return "Immediate (24–48h)";
      case "SHORT_TERM_7D":
        return "Short-Term (7 Days)";
      case "STRATEGIC_30D":
        return "Strategic (30 Days)";
      default:
        return horizon;
    }
  };

  const getDomainIcon = (domain: string) => {
    switch (domain.toLowerCase()) {
      case "census":
        return <Building2 className="w-4 h-4 text-indigo-600" />;
      case "staffing":
        return <Users className="w-4 h-4 text-blue-600" />;
      case "therapy":
        return <Activity className="w-4 h-4 text-teal-600" />;
      case "hospitality":
        return <Utensils className="w-4 h-4 text-amber-600" />;
      case "payer_auth":
        return <Layers className="w-4 h-4 text-purple-600" />;
      case "hospital_transfers":
        return <History className="w-4 h-4 text-rose-600" />;
      default:
        return <CheckSquare className="w-4 h-4 text-slate-600" />;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* 1. Executive Action Roadmap Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white shadow-md border border-slate-700">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-extrabold uppercase tracking-wider rounded-full bg-orange-600 text-white shadow-xs">
                Leadership Action Roadmap
              </span>
              <span className="text-xs text-slate-300 flex items-center gap-1 font-medium">
                <Calendar className="w-3.5 h-3.5 text-orange-400" />
                Snapshot: {snapshot_date}
              </span>
            </div>
            <span className="text-xs px-3 py-1 rounded-md bg-slate-800 border border-slate-700 font-semibold text-slate-300">
              Scenario: <strong className="text-white">{scenario.replace(/_/g, " ")}</strong>
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            {facility_name} — Prioritized Operational Action Plan
          </h2>

          <p className="text-base sm:text-lg leading-relaxed text-slate-200">
            {executive_action_plan_overview}
          </p>

          {/* Action Counters Summary */}
          <div className="pt-4 border-t border-slate-700/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 bg-slate-800/80 rounded-xl border border-slate-700">
              <span className="text-xs text-slate-400 font-semibold block">Total Actions</span>
              <span className="text-xl font-black text-white">
                {verified_recommendations_summary.total_recommendations_count}
              </span>
            </div>
            <div className="p-3 bg-rose-950/40 rounded-xl border border-rose-800/60">
              <span className="text-xs text-rose-300 font-semibold block">High Priority</span>
              <span className="text-xl font-black text-rose-400">
                {verified_recommendations_summary.high_priority_count}
              </span>
            </div>
            <div className="p-3 bg-amber-950/40 rounded-xl border border-amber-800/60">
              <span className="text-xs text-amber-300 font-semibold block">Medium Priority</span>
              <span className="text-xl font-black text-amber-400">
                {verified_recommendations_summary.medium_priority_count}
              </span>
            </div>
            <div className="p-3 bg-blue-950/40 rounded-xl border border-blue-800/60">
              <span className="text-xs text-blue-300 font-semibold block">Low Priority</span>
              <span className="text-xl font-black text-blue-400">
                {verified_recommendations_summary.low_priority_count}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Interactive Multi-Dimensional Filter Toolbar */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-2 text-slate-700 font-bold text-sm">
          <Filter className="w-4 h-4 text-orange-600" />
          <span>Filter Action Roadmap:</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Priority Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 text-xs">
            <span className="text-slate-500 font-semibold">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-transparent font-bold text-slate-800 outline-none cursor-pointer w-full"
            >
              <option value="all">All Priorities</option>
              <option value="HIGH">High Priority Only</option>
              <option value="MEDIUM">Medium Priority Only</option>
              <option value="LOW">Low Priority Only</option>
            </select>
          </div>

          {/* Time Horizon Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 text-xs">
            <span className="text-slate-500 font-semibold">Horizon:</span>
            <select
              value={horizonFilter}
              onChange={(e) => setHorizonFilter(e.target.value)}
              className="bg-transparent font-bold text-slate-800 outline-none cursor-pointer w-full"
            >
              <option value="all">All Timeframes</option>
              <option value="IMMEDIATE_24H">Immediate (24–48h)</option>
              <option value="SHORT_TERM_7D">Short-Term (7 Days)</option>
              <option value="STRATEGIC_30D">Strategic (30 Days)</option>
            </select>
          </div>

          {/* Department Filter */}
          <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 text-xs">
            <span className="text-slate-500 font-semibold">Dept:</span>
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="bg-transparent font-bold text-slate-800 outline-none cursor-pointer w-full"
            >
              <option value="all">All Departments</option>
              {uniqueDepartments.map((dept) => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* 3. Actionable Recommendations List */}
      <div className="space-y-6">
        {filteredRecommendations.length === 0 ? (
          <div className="p-12 bg-white rounded-2xl border border-slate-200 text-center space-y-3">
            <CheckSquare className="w-10 h-10 text-slate-400 mx-auto" />
            <h4 className="text-base font-bold text-slate-800">No Actions Match the Selected Filters</h4>
            <p className="text-xs text-slate-500">
              Try adjusting your priority, time horizon, or department filters above to view other suggested actions.
            </p>
          </div>
        ) : (
          filteredRecommendations.map((rec) => (
            <div
              key={rec.recommendation_id}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-shadow overflow-hidden"
            >
              {/* Header: Title, Priority, Horizon, Role */}
              <div className="p-6 bg-gradient-to-r from-slate-50 to-orange-50/20 border-b border-slate-100 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    {getPriorityBadge(rec.priority)}
                    <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                      <Clock className="w-3.5 h-3.5 text-slate-500" />
                      {getTimeHorizonLabel(rec.time_horizon)}
                    </span>
                    <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {getDomainIcon(rec.domain)}
                      {rec.domain_display_name}
                    </span>
                  </div>

                  <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                    {rec.action_title}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-orange-100/80 text-orange-900 border border-orange-200 whitespace-nowrap">
                    Lead: {rec.target_role_or_department}
                  </span>
                </div>
              </div>

              {/* Body: 4 Core Sections (Rationale -> Suggested Steps -> Impact -> Supporting Evidence) */}
              <div className="p-6 space-y-5">
                {/* 1. Operational Rationale (Why This Action Was Suggested) */}
                <div className="bg-amber-50/50 p-4 rounded-xl border border-amber-100 space-y-1">
                  <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                    Operational & Clinical Rationale (AC-3.3.1)
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed font-medium">
                    {rec.rationale}
                  </p>
                </div>

                {/* 2. Suggested Next Steps (Action Checklist) */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckSquare className="w-4 h-4 text-orange-600" />
                    Suggested Practical Steps for Leadership Evaluation
                  </h4>
                  <p className="text-sm text-slate-800 bg-slate-50 p-4 rounded-xl border border-slate-100 leading-relaxed font-medium">
                    {rec.suggested_action_description}
                  </p>
                </div>

                {/* 3. Expected Operational Impact */}
                <div className="flex items-start gap-2 text-xs bg-emerald-50/60 p-3 rounded-xl border border-emerald-100 text-emerald-900">
                  <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-bold">Projected Operational Benefit: </strong>
                    <span>{rec.expected_operational_impact}</span>
                  </div>
                </div>

                {/* 4. Supporting Metric Evidence Tracing (AC-3.3.2) */}
                {rec.supporting_evidence_metrics && rec.supporting_evidence_metrics.length > 0 && (
                  <div className="pt-3 border-t border-slate-100">
                    <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                      <TrendingUp className="w-3.5 h-3.5 text-slate-400" />
                      Supporting Verifiable Evidence Metrics (AC-3.3.2 Grounding)
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {rec.supporting_evidence_metrics.map((evidence, idx) => (
                        <span
                          key={idx}
                          className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 border border-slate-200"
                        >
                          {evidence}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* 4. Human Decision Authority & Governance Notice (AC-2.5.3, FR-009) */}
      <div className="p-5 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-center gap-2 font-bold text-slate-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Decision Support Governance & Human Authority (AC-2.5.3, FR-009)
        </div>
        <p className="leading-relaxed">
          {decision_authority_notice}
        </p>
        {data_limitations_and_uncertainty && (
          <p className="text-[11px] text-slate-500 pt-1">
            {data_limitations_and_uncertainty}
          </p>
        )}
      </div>
    </div>
  );
};
