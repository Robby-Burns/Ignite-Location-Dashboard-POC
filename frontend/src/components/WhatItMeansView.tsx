import React, { useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Activity, 
  Building2, 
  Users, 
  Utensils, 
  HelpCircle, 
  AlertOctagon, 
  CheckCircle2, 
  Layers, 
  ShieldCheck, 
  History,
  Calendar
} from "lucide-react";
import { 
  FacilityTrendExplanationReport, 
  MetricTrendSummary 
} from "../types";

interface WhatItMeansViewProps {
  data: FacilityTrendExplanationReport | null;
  loading: boolean;
  error: string | null;
}

export const WhatItMeansView: React.FC<WhatItMeansViewProps> = ({ data, loading, error }) => {
  const [selectedDomain, setSelectedDomain] = useState<string>("all");

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium animate-pulse">Analyzing 30-day historical trajectories and metric context...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
        <div className="flex items-center space-x-3">
          <AlertOctagon className="w-6 h-6 text-rose-600 flex-shrink-0" />
          <h3 className="text-lg font-bold">Failed to Load Trend Analysis</h3>
        </div>
        <p className="text-sm text-rose-700">{error || "No trend explanation data returned."}</p>
      </div>
    );
  }

  const { 
    facility_name, 
    analysis_date, 
    scenario, 
    executive_trend_summary, 
    metric_explanations, 
    trend_explanations, 
    notable_shifts, 
    data_limitations_and_uncertainty,
    verified_calculations 
  } = data;

  const domainKeys = Object.keys(trend_explanations);

  const getDomainIcon = (domain: string) => {
    switch (domain.toLowerCase()) {
      case "census":
        return <Building2 className="w-5 h-5 text-indigo-600" />;
      case "staffing":
        return <Users className="w-5 h-5 text-blue-600" />;
      case "therapy":
        return <Activity className="w-5 h-5 text-teal-600" />;
      case "hospitality":
        return <Utensils className="w-5 h-5 text-amber-600" />;
      case "payer_auth":
        return <Layers className="w-5 h-5 text-purple-600" />;
      case "hospital_transfers":
        return <History className="w-5 h-5 text-rose-600" />;
      default:
        return <Activity className="w-5 h-5 text-slate-600" />;
    }
  };

  const getDomainDisplayName = (domainKey: string, fallback: string) => {
    switch (domainKey.toLowerCase()) {
      case "census":
        return "Census & Capacity";
      case "staffing":
        return "Nursing Staffing";
      case "therapy":
        return "Therapy & Progress";
      case "hospitality":
        return "Hospitality & Dining";
      case "payer_auth":
        return "Payer & Authorizations";
      case "hospital_transfers":
        return "Hospital Transfers";
      case "length_of_stay":
        return "Length of Stay";
      case "admissions_discharges":
        return "Admissions & Discharges";
      default:
        return fallback;
    }
  };

  const getTrajectoryBadge = (dir: string) => {
    switch (dir) {
      case "INCREASING":
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800">
            <TrendingUp className="w-3.5 h-3.5" />
            Increasing Trend
          </span>
        );
      case "DECREASING":
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800">
            <TrendingDown className="w-3.5 h-3.5" />
            Decreasing Trend
          </span>
        );
      case "VOLATILE":
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-purple-100 text-purple-800">
            <Activity className="w-3.5 h-3.5" />
            Fluctuating / Volatile
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            <Minus className="w-3.5 h-3.5" />
            Stable Trajectory
          </span>
        );
    }
  };

  const filteredDomains = selectedDomain === "all" 
    ? domainKeys 
    : domainKeys.filter((d) => d === selectedDomain);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* 1. Executive Momentum & 30-Day Trajectory Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white shadow-md border border-slate-700">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 text-xs font-extrabold uppercase tracking-wider rounded-full bg-orange-600 text-white shadow-xs">
                Historical Context & What It Means
              </span>
              <span className="text-xs text-slate-300 flex items-center gap-1 font-medium">
                <Calendar className="w-3.5 h-3.5 text-orange-400" />
                Snapshot: {analysis_date} (30-Day Window)
              </span>
            </div>
            <span className="text-xs px-3 py-1 rounded-md bg-slate-800 border border-slate-700 font-semibold text-slate-300">
              Scenario: <strong className="text-white">{scenario.replace(/_/g, " ")}</strong>
            </span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            {facility_name} — 30-Day Operational Momentum
          </h2>

          <p className="text-base sm:text-lg leading-relaxed text-slate-200">
            {executive_trend_summary}
          </p>

          {/* Notable Historical Shifts List */}
          {notable_shifts && notable_shifts.length > 0 && (
            <div className="pt-4 border-t border-slate-700/80">
              <p className="text-xs uppercase font-bold text-orange-400 tracking-wider mb-2">
                Notable Historical Shifts Detected (Past 30 Days)
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {notable_shifts.map((shift, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-xs text-slate-300 bg-slate-800/80 p-2.5 rounded-xl border border-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                    <span>{shift}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Operational Domain Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200">
        <button
          onClick={() => setSelectedDomain("all")}
          className={`px-4 py-2 text-xs sm:text-sm font-bold rounded-xl whitespace-nowrap transition-all ${
            selectedDomain === "all"
              ? "bg-orange-600 text-white shadow-xs"
              : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
          }`}
        >
          All Domains ({domainKeys.length})
        </button>

        {domainKeys.map((domainKey) => {
          const domain = trend_explanations[domainKey];
          const isSelected = selectedDomain === domainKey;
          return (
            <button
              key={domainKey}
              onClick={() => setSelectedDomain(domainKey)}
              className={`flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-bold rounded-xl whitespace-nowrap transition-all ${
                isSelected
                  ? "bg-orange-600 text-white shadow-xs"
                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {getDomainDisplayName(domainKey, domain.domain_display_name)}
            </button>
          );
        })}
      </div>

      {/* 3. Domain Deep-Dive Sections */}
      <div className="space-y-8">
        {filteredDomains.map((domainKey) => {
          const domainExpl = trend_explanations[domainKey];
          // Find metric explanations belonging to this domain
          const domainMetrics = Object.values(metric_explanations).filter(
            (m) => m.domain === domainKey || m.domain.toLowerCase() === domainKey.toLowerCase()
          );

          return (
            <div 
              key={domainKey}
              className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden"
            >
              {/* Domain Header */}
              <div className="p-6 bg-gradient-to-r from-slate-50 to-orange-50/30 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-3">
                  <span className="p-2.5 bg-white rounded-xl shadow-xs border border-slate-200">
                    {getDomainIcon(domainKey)}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-slate-900">{getDomainDisplayName(domainKey, domainExpl.domain_display_name)}</h3>
                      {domainExpl.is_meaningful_shift && (
                        <span className="text-[10px] bg-orange-100 text-orange-800 font-extrabold px-2 py-0.5 rounded-full uppercase">
                          Material Shift
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-semibold text-slate-600">{domainExpl.headline}</p>
                  </div>
                </div>

                <div>
                  {getTrajectoryBadge(domainExpl.trajectory_direction)}
                </div>
              </div>

              {/* Domain Narrative */}
              <div className="p-6 bg-slate-50/50 border-b border-slate-100">
                <p className="text-sm text-slate-700 leading-relaxed font-medium">
                  {domainExpl.narrative}
                </p>
              </div>

              {/* Metric Breakdown Grid (Observation -> Meaning -> Significance -> Target) */}
              <div className="p-6">
                <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-1.5">
                  <HelpCircle className="w-4 h-4 text-orange-500" />
                  Detailed Metric Explanations & Historical Trajectories (AC-3.2.1, INV-003)
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {domainMetrics.map((metric) => {
                    const calc = verified_calculations.trends[metric.metric_name] as MetricTrendSummary | undefined;
                    
                    return (
                      <div 
                        key={metric.metric_name}
                        className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs hover:border-orange-300 transition-colors flex flex-col justify-between space-y-4"
                      >
                        {/* 1. Observation Layer: Raw Values & Historical Deltas */}
                        <div>
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div>
                              <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
                                {metric.display_name}
                              </span>
                              <p className="text-2xl font-black text-slate-900 tracking-tight">
                                {metric.current_value_formatted}
                              </p>
                            </div>

                            {calc && (
                              <div className="text-right">
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                                  (calc.delta_7d || 0) > 0 ? "bg-emerald-50 text-emerald-700" :
                                  (calc.delta_7d || 0) < 0 ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600"
                                }`}>
                                  7d: {calc.delta_7d !== null ? `${calc.delta_7d > 0 ? "+" : ""}${calc.delta_7d.toFixed(1)}${calc.unit}` : "N/A"}
                                </span>
                                <p className="text-[10px] text-slate-400 mt-1">
                                  30d: {calc.delta_30d !== null ? `${calc.delta_30d > 0 ? "+" : ""}${calc.delta_30d.toFixed(1)}${calc.unit}` : "N/A"}
                                </p>
                              </div>
                            )}
                          </div>

                          {/* Historical Progression Bar */}
                          {calc && (
                            <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-100 mt-3 grid grid-cols-4 gap-1 text-center text-[10px]">
                              <div>
                                <span className="text-slate-400 block">30d Ago</span>
                                <span className="font-semibold text-slate-700">{calc.value_30d_ago !== null ? `${calc.value_30d_ago.toFixed(1)}${calc.unit}` : "—"}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">14d Ago</span>
                                <span className="font-semibold text-slate-700">{calc.value_14d_ago !== null ? `${calc.value_14d_ago.toFixed(1)}${calc.unit}` : "—"}</span>
                              </div>
                              <div>
                                <span className="text-slate-400 block">7d Ago</span>
                                <span className="font-semibold text-slate-700">{calc.value_7d_ago !== null ? `${calc.value_7d_ago.toFixed(1)}${calc.unit}` : "—"}</span>
                              </div>
                              <div className="bg-white rounded-md shadow-xs py-0.5 border border-slate-200">
                                <span className="text-orange-600 font-bold block">Current</span>
                                <span className="font-extrabold text-slate-900">{calc.current_value.toFixed(1)}{calc.unit}</span>
                              </div>
                            </div>
                          )}
                        </div>

                        {/* 2. Interpretation Layer: What It Measures */}
                        <div className="text-xs text-slate-600 bg-blue-50/50 p-3 rounded-xl border border-blue-100/80 space-y-1">
                          <p className="font-bold text-blue-950 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
                            What This Measures
                          </p>
                          <p className="leading-relaxed">{metric.plain_language_meaning}</p>
                        </div>

                        {/* 3. Significance Layer: Why It Matters */}
                        <div className="text-xs text-slate-700 bg-amber-50/50 p-3 rounded-xl border border-amber-100/80 space-y-1">
                          <p className="font-bold text-amber-950 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                            Why It Matters (Operational Impact)
                          </p>
                          <p className="leading-relaxed">{metric.operational_significance}</p>
                        </div>

                        {/* 4. Target / Benchmark Context */}
                        <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                          <span className="font-semibold text-slate-600">Benchmark / Target:</span>
                          <span className="font-medium text-slate-800">{metric.benchmark_context}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. Data Boundaries & Limitations Notice */}
      <div className="p-5 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-center gap-2 font-bold text-slate-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Trend Analysis Boundaries & Non-Technical Governance
        </div>
        <p className="leading-relaxed">
          {data_limitations_and_uncertainty}
        </p>
        <p className="text-[11px] text-slate-500 pt-1">
          Historical trajectories and deltas are derived deterministically across standard rolling 7-day and 30-day windows. All metrics are non-identifying operational indicators.
        </p>
      </div>
    </div>
  );
};
