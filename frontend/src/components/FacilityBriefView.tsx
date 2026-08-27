import React from "react";
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertOctagon, 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  ShieldCheck, 
  Sparkles, 
  Clock, 
  Building2, 
  Users, 
  Activity, 
  Utensils, 
  HeartHandshake,
  Info
} from "lucide-react";
import { FacilityBriefReport } from "../types";

interface FacilityBriefViewProps {
  data: FacilityBriefReport | null;
  loading: boolean;
  error: string | null;
}

export const FacilityBriefView: React.FC<FacilityBriefViewProps> = ({ data, loading, error }) => {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium animate-pulse">Synthesizing facility operational brief...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
        <div className="flex items-center space-x-3">
          <AlertOctagon className="w-6 h-6 text-rose-600 flex-shrink-0" />
          <h3 className="text-lg font-bold">Failed to Load Facility Brief</h3>
        </div>
        <p className="text-sm text-rose-700">{error || "No brief data returned."}</p>
      </div>
    );
  }

  const { header, vitals, positive_highlights, watch_items, action_items, limitations } = data;

  const getStatusTheme = (status: string) => {
    switch (status) {
      case "CRITICAL":
        return {
          bg: "bg-rose-50 border-rose-200",
          badge: "bg-rose-600 text-white",
          text: "text-rose-950",
          subtext: "text-rose-800",
          icon: <AlertOctagon className="w-6 h-6 text-rose-600" />
        };
      case "NEEDS_ATTENTION":
        return {
          bg: "bg-orange-50 border-orange-200",
          badge: "bg-orange-600 text-white",
          text: "text-orange-950",
          subtext: "text-orange-800",
          icon: <AlertTriangle className="w-6 h-6 text-orange-600" />
        };
      case "WATCH":
        return {
          bg: "bg-amber-50 border-amber-200",
          badge: "bg-amber-600 text-white",
          text: "text-amber-950",
          subtext: "text-amber-800",
          icon: <AlertTriangle className="w-6 h-6 text-amber-600" />
        };
      default:
        return {
          bg: "bg-emerald-50 border-emerald-200",
          badge: "bg-emerald-600 text-white",
          text: "text-emerald-950",
          subtext: "text-emerald-800",
          icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />
        };
    }
  };

  const theme = getStatusTheme(header.overall_status);

  const getVitalIcon = (metricName: string) => {
    switch (metricName) {
      case "occupancy_rate_pct":
        return <Building2 className="w-5 h-5 text-indigo-600" />;
      case "hppd_actual":
        return <Users className="w-5 h-5 text-blue-600" />;
      case "agency_staff_pct":
        return <Users className="w-5 h-5 text-purple-600" />;
      case "treatment_completion_rate_pct":
        return <Activity className="w-5 h-5 text-teal-600" />;
      case "dining_satisfaction_score":
        return <Utensils className="w-5 h-5 text-amber-600" />;
      default:
        return <Activity className="w-5 h-5 text-slate-600" />;
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* 1. Executive Status Banner */}
      <div className={`p-6 sm:p-8 rounded-2xl border ${theme.bg} shadow-sm transition-all duration-300`}>
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-3 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full shadow-sm ${theme.badge}`}>
                {header.status_label}
              </span>
              <span className="text-xs font-semibold text-slate-600 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                Snapshot: {header.report_date}
              </span>
              <span className="text-xs px-2.5 py-0.5 rounded-md bg-white/80 border border-slate-200 font-medium text-slate-700">
                Scenario: <strong className="font-semibold">{header.scenario.replace(/_/g, " ")}</strong>
              </span>
            </div>
            
            <h2 className={`text-2xl sm:text-3xl font-extrabold tracking-tight ${theme.text}`}>
              {header.facility_name} — Operational Pulse
            </h2>

            <p className={`text-base sm:text-lg leading-relaxed ${theme.subtext}`}>
              {header.executive_summary}
            </p>
          </div>

          <div className="hidden lg:flex flex-col items-end justify-center pl-6 border-l border-slate-200/60">
            <div className="p-3 bg-white rounded-xl shadow-xs border border-slate-100 flex items-center gap-3">
              {theme.icon}
              <div>
                <p className="text-xs text-slate-500 font-medium uppercase">Overall State</p>
                <p className="text-sm font-bold text-slate-900">{header.overall_status.replace(/_/g, " ")}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Key Operational Vitals Grid */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-orange-600" />
            Facility Vitals & Benchmark Status
          </h3>
          <span className="text-xs text-slate-500 font-medium">Direct Daily Telemetry</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {vitals.map((vital) => {
            const isPositive = vital.status === "POSITIVE";
            return (
              <div 
                key={vital.metric_name}
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:shadow-md transition-shadow duration-200 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                    {getVitalIcon(vital.metric_name)}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                    isPositive ? "bg-emerald-100 text-emerald-800" : "bg-orange-100 text-orange-800"
                  }`}>
                    {vital.status}
                  </span>
                </div>

                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{vital.label}</p>
                  <p className="text-2xl font-extrabold text-slate-900 tracking-tight">{vital.formatted_value}</p>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                  <span className="truncate">{vital.subtitle}</span>
                  {vital.trend === "UP" && <TrendingUp className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />}
                  {vital.trend === "DOWN" && <TrendingDown className="w-3.5 h-3.5 text-rose-600 flex-shrink-0" />}
                  {vital.trend === "STABLE" && <Minus className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Three-Column Executive Brief Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Column 1: What is Going Well (Story 2.3) */}
        <div className="bg-white rounded-2xl border border-emerald-200/80 shadow-xs overflow-hidden flex flex-col">
          <div className="p-5 bg-gradient-to-r from-emerald-50 to-teal-50 border-b border-emerald-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-xs">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">What's Going Well</h3>
                <p className="text-xs text-emerald-800 font-medium">Standout Strengths & Benchmarks</p>
              </div>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
              {positive_highlights.length} Items
            </span>
          </div>

          <div className="p-5 space-y-4 flex-1">
            {positive_highlights.length === 0 ? (
              <p className="text-sm text-slate-500 italic">No standout positive highlights detected for this scenario.</p>
            ) : (
              positive_highlights.map((h, i) => (
                <div key={i} className="p-4 rounded-xl bg-emerald-50/40 border border-emerald-100/80 space-y-2 hover:bg-emerald-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-700 uppercase tracking-wide">{h.domain}</span>
                    <span className="text-xs bg-emerald-100 text-emerald-800 font-medium px-2 py-0.5 rounded-md">
                      {h.supporting_metric}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">{h.title}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{h.plain_language_description}</p>
                  <p className="text-xs font-medium text-emerald-900 bg-white/70 p-2 rounded-lg border border-emerald-100">
                    💡 <strong>Impact:</strong> {h.significance}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Column 2: Areas Requiring Attention (Story 2.4) */}
        <div className="bg-white rounded-2xl border border-amber-200/80 shadow-xs overflow-hidden flex flex-col">
          <div className="p-5 bg-gradient-to-r from-amber-50 to-orange-50 border-b border-amber-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-amber-600 text-white rounded-xl shadow-xs">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Areas to Watch</h3>
                <p className="text-xs text-amber-800 font-medium">Prioritized Concerns & Deficits</p>
              </div>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
              {watch_items.length} Items
            </span>
          </div>

          <div className="p-5 space-y-4 flex-1">
            {watch_items.length === 0 ? (
              <div className="p-6 text-center space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
                <p className="text-sm font-medium text-slate-700">No active operational deficits</p>
                <p className="text-xs text-slate-500">All core domains are tracking within normal operating parameters.</p>
              </div>
            ) : (
              watch_items.map((item, i) => (
                <div key={i} className="p-4 rounded-xl bg-amber-50/40 border border-amber-100/80 space-y-2 hover:bg-amber-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-amber-800 uppercase tracking-wide">{item.domain}</span>
                      {item.is_compound_risk && (
                        <span className="text-[10px] bg-purple-100 text-purple-800 font-bold px-1.5 py-0.2 rounded">
                          Compound
                        </span>
                      )}
                    </div>
                    <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full uppercase ${
                      item.severity === "CRITICAL" ? "bg-rose-100 text-rose-800" :
                      item.severity === "HIGH" ? "bg-orange-100 text-orange-800" : "bg-amber-100 text-amber-800"
                    }`}>
                      {item.severity}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">{item.title}</h4>
                  <p className="text-xs text-slate-600 leading-relaxed">{item.plain_language_concern}</p>
                  <div className="text-xs font-medium text-slate-800 bg-white/70 p-2 rounded-lg border border-amber-100 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                    <span>{item.supporting_metric}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Column 3: Immediate Suggested Next Steps (Story 2.5) */}
        <div className="bg-white rounded-2xl border border-blue-200/80 shadow-xs overflow-hidden flex flex-col">
          <div className="p-5 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-blue-600 text-white rounded-xl shadow-xs">
                <HeartHandshake className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-base">Suggested Next Steps</h3>
                <p className="text-xs text-blue-800 font-medium">Departmental Action Plan</p>
              </div>
            </div>
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
              {action_items.length} Actions
            </span>
          </div>

          <div className="p-5 space-y-4 flex-1">
            {action_items.length === 0 ? (
              <p className="text-sm text-slate-500 italic">No specific action items required.</p>
            ) : (
              action_items.map((action, i) => (
                <div key={i} className="p-4 rounded-xl bg-blue-50/40 border border-blue-100/80 space-y-2 hover:bg-blue-50 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-blue-800 uppercase tracking-wide">{action.department}</span>
                    <span className="text-[10px] bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded-md">
                      {action.time_horizon}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">{action.title}</h4>
                  <p className="text-xs text-slate-700 leading-relaxed font-medium bg-white/80 p-2.5 rounded-lg border border-blue-100">
                    👉 <strong>Action:</strong> {action.suggested_action}
                  </p>
                  <p className="text-[11px] text-slate-500 leading-tight">
                    <strong>Why:</strong> {action.why_it_matters}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 4. Boundaries, Governance & Limitations (FR-009, INV-008, Spec §1) */}
      <div className="p-5 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 font-bold text-slate-800">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            Decision-Support Boundaries & Data Governance
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Telemetry Connection: Operational Data Stream
          </span>
        </div>

        <p className="leading-relaxed">
          {limitations.disclaimer}
        </p>

        <div className="flex flex-wrap gap-x-6 gap-y-1.5 pt-2 border-t border-slate-200 text-[11px] text-slate-500">
          {limitations.data_completeness_notes.map((note, i) => (
            <span key={i} className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              {note}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
