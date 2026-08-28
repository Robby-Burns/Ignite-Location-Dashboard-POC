import React, { useEffect, useMemo, useState } from "react";
import {
  Flame,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import type { FacilityBriefReport, BriefVitalMetric } from "../types";
import { Finding, operationalAreaById, matchesOperationalArea } from "../config";
import { FindingCard } from "./FindingCard";
import { PositiveFindingCard } from "./PositiveFindingCard";

interface OperationalDashboardProps {
  brief: FacilityBriefReport | null;
  findings: Finding[];
  loading: boolean;
  error: string | null;
  selectedArea: string;
}

const VITAL_STATUS: Record<
  string,
  { color: string; soft: string; label: string }
> = {
  POSITIVE: { color: "#2F7D5C", soft: "#E9F3EE", label: "On target" },
  NEUTRAL: { color: "#4B5566", soft: "#F0ECE3", label: "Stable" },
  ATTENTION: { color: "#AD7B1F", soft: "#FBF2DF", label: "Needs attention" },
  CRITICAL: { color: "#C4432B", soft: "#FBEAE5", label: "Critical" },
};

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "UP") return <TrendingUp className="w-3 h-3" />;
  if (trend === "DOWN") return <TrendingDown className="w-3 h-3" />;
  return <Minus className="w-3 h-3" />;
}

function VitalCard({ vital }: { vital: BriefVitalMetric }) {
  const status = VITAL_STATUS[vital.status] ?? VITAL_STATUS.NEUTRAL;
  return (
    <div
      className="relative bg-surface border border-line rounded-[14px] shadow-card px-4 py-3.5 overflow-hidden"
      style={{ borderLeft: `3px solid ${status.color}` }}
    >
      <p className="text-[11.5px] text-muted font-semibold">{vital.label}</p>
      <p className="mt-1 font-display font-extrabold text-[22px] leading-none num text-ink">
        {vital.formatted_value}
      </p>
      <span
        className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full"
        style={{ backgroundColor: status.soft, color: status.color }}
      >
        <TrendIcon trend={vital.trend} />
        {status.label}
      </span>
      <p className="mt-1.5 text-[11px] text-muted truncate" title={vital.subtitle}>
        {vital.subtitle}
      </p>
    </div>
  );
}

export const OperationalDashboard: React.FC<OperationalDashboardProps> = ({
  brief,
  findings,
  loading,
  error,
  selectedArea,
}) => {
  const areaConfig = operationalAreaById(selectedArea);
  const [activeTab, setActiveTab] = useState<"attention" | "strengths">(
    "attention",
  );
  const [openId, setOpenId] = useState<string | null>(null);
  const [openPositiveIndex, setOpenPositiveIndex] = useState<number | null>(0);

  // Client-side instant lens filtering (0 API calls, 0 LLM calls, 0 network latency)
  const filteredFindings = useMemo(() => {
    return findings.filter((f) => matchesOperationalArea(f.domain, selectedArea));
  }, [findings, selectedArea]);

  const filteredHighlights = useMemo(() => {
    if (!brief) return [];
    return brief.positive_highlights.filter((h) =>
      matchesOperationalArea(h.domain, selectedArea)
    );
  }, [brief, selectedArea]);

  useEffect(() => {
    setActiveTab(filteredFindings.length > 0 ? "attention" : "strengths");
    setOpenId(filteredFindings.length > 0 ? filteredFindings[0].id : null);
    setOpenPositiveIndex(0);
  }, [filteredFindings]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="w-11 h-11 border-4 border-flame border-t-transparent rounded-full animate-spin" />
        <p className="text-ink-soft font-medium animate-pulse">
          Synthesizing facility operational brief…
        </p>
      </div>
    );
  }

  if (error || !brief) {
    return (
      <div className="p-6 bg-critical-soft border border-critical-line rounded-2xl text-critical space-y-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5" />
          <h3 className="font-bold">Failed to load facility analysis</h3>
        </div>
        <p className="text-sm">{error || "No data returned."}</p>
      </div>
    );
  }

  const { header, vitals, limitations, time_context } = brief;

  return (
    <div className="space-y-4 min-w-0">

      {/* Vitals strip (Always facility-wide) */}
      <div>
        <div className="flex items-center justify-between mb-2.5 flex-wrap gap-2">
          <h2 className="flex items-center gap-2 text-[12.5px] font-bold uppercase tracking-wide text-muted">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: areaConfig.accent }}
            />
            Facility vitals (Facility-Wide)
          </h2>
          <span className="text-[11.5px] text-muted flex items-center gap-1.5 font-medium">
            <Clock className="w-3.5 h-3.5" />
            {time_context ? `Data through ${time_context.data_as_of} · 30-Day Trend · 90-Day Baseline` : `Snapshot ${header.report_date}`}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
          {vitals.map((v) => (
            <VitalCard key={v.metric_name} vital={v} />
          ))}
        </div>
      </div>

      {/* Main tabs */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-1 bg-surface border border-line rounded-[11px] p-1 w-fit">
          <button
            onClick={() => setActiveTab("attention")}
            className="flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-semibold transition-colors"
            style={
              activeTab === "attention"
                ? { backgroundColor: "#1A2332", color: "#fff" }
                : { color: "#847C6E" }
            }
          >
            Needs attention
            <span
              className="text-[10.5px] rounded-full px-1.5 py-px"
              style={
                activeTab === "attention"
                  ? { backgroundColor: "rgba(255,255,255,0.18)", color: "#fff" }
                  : { backgroundColor: "#F0ECE3", color: "#4B5566" }
              }
            >
              {filteredFindings.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("strengths")}
            className="flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[13px] font-semibold transition-colors"
            style={
              activeTab === "strengths"
                ? { backgroundColor: "#1A2332", color: "#fff" }
                : { color: "#847C6E" }
            }
          >
            Going well
            <span
              className="text-[10.5px] rounded-full px-1.5 py-px"
              style={
                activeTab === "strengths"
                  ? { backgroundColor: "rgba(255,255,255,0.18)", color: "#fff" }
                  : { backgroundColor: "#F0ECE3", color: "#4B5566" }
              }
            >
              {filteredHighlights.length}
            </span>
          </button>
        </div>

        {selectedArea !== "all" && (
          <span className="text-[12px] text-muted font-medium">
            Filtering by: <strong className="text-ink">{areaConfig.label}</strong>
          </span>
        )}
      </div>

      {/* Attention panel */}
      {activeTab === "attention" && (
        <div className="space-y-3">
          {filteredFindings.length === 0 && (
            <div className="bg-surface border border-line rounded-[14px] p-10 text-center space-y-2">
              <CheckCircle2 className="w-9 h-9 text-good mx-auto" />
              <p className="font-bold text-ink">
                {selectedArea === "all"
                  ? "No active operational deficits identified"
                  : `No active operational concerns identified in ${areaConfig.label}`}
              </p>
              <p className="text-[13px] text-muted max-w-md mx-auto">
                {selectedArea === "all"
                  ? "All evaluated domains are currently tracking within normal operational parameters."
                  : `Operations in ${areaConfig.label} are currently tracking within healthy benchmarks based on the available data.`}
              </p>
            </div>
          )}
          {filteredFindings.map((f, i) => (
            <div key={f.id} id={`finding-${f.id}`}>
              <FindingCard
                finding={f}
                index={i}
                open={openId === f.id}
                onToggle={() => setOpenId(openId === f.id ? null : f.id)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Strengths panel */}
      {activeTab === "strengths" && (
        <div className="space-y-3">
          {filteredHighlights.length === 0 && (
            <div className="bg-surface border border-line rounded-[14px] p-10 text-center space-y-2">
              <p className="text-[13px] text-muted italic">
                {selectedArea === "all"
                  ? "No standout positive highlights detected for this evaluation."
                  : `No standout positive highlights detected for ${areaConfig.label}.`}
              </p>
            </div>
          )}
          {filteredHighlights.map((h, i) => (
            <div key={i} id={`positive-highlight-${i}`}>
              <PositiveFindingCard
                highlight={h}
                index={i}
                open={openPositiveIndex === i}
                onToggle={() =>
                  setOpenPositiveIndex(openPositiveIndex === i ? null : i)
                }
              />
            </div>
          ))}
        </div>
      )}

      {/* Footer note */}
      <div className="mt-5 bg-surface border border-line rounded-[14px] px-4 py-3.5 flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5 text-[12.5px] text-ink-soft">
          <Flame className="w-4 h-4 text-flame flex-shrink-0" />
          <span>{limitations.disclaimer}</span>
        </div>
        <div className="flex gap-3.5 text-[11.5px] text-muted">
          {limitations.data_completeness_notes.map((note, i) => (
            <span key={i} className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-good" />
              {note.split(":")[0]}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default OperationalDashboard;
