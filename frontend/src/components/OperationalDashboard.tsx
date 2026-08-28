import React, { useEffect, useState } from "react";
import {
  Flame,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";
import type { FacilityBriefReport, BriefVitalMetric } from "../types";
import { Finding, scenarioById } from "../config";
import { FindingCard } from "./FindingCard";

interface OperationalDashboardProps {
  brief: FacilityBriefReport | null;
  findings: Finding[];
  loading: boolean;
  error: string | null;
  scenario: string;
}

type OverallStatus = "HEALTHY" | "WATCH" | "NEEDS_ATTENTION" | "CRITICAL";

const STATUS_THEME: Record<
  OverallStatus,
  { bg: string; line: string; text: string; label: string }
> = {
  HEALTHY: { bg: "#E9F3EE", line: "#BFDBCC", text: "#1F5C41", label: "Stable" },
  WATCH: { bg: "#FBF2DF", line: "#EBD69E", text: "#8A5C10", label: "Watch" },
  NEEDS_ATTENTION: {
    bg: "#FDEEE6",
    line: "#F3CBB4",
    text: "#C2410C",
    label: "Attention",
  },
  CRITICAL: { bg: "#FBEAE5", line: "#EFC0B2", text: "#9A2C1B", label: "Critical" },
};

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
  scenario,
}) => {
  const accent = scenarioById(scenario);
  const [activeTab, setActiveTab] = useState<"attention" | "strengths">(
    "attention",
  );
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    setActiveTab(findings.length > 0 ? "attention" : "strengths");
    setOpenId(findings.length > 0 ? findings[0].id : null);
  }, [findings]);

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

  const { header, vitals, positive_highlights, limitations } = brief;
  const statusKey = (header.overall_status as OverallStatus) ?? "WATCH";
  const theme = STATUS_THEME[statusKey] ?? STATUS_THEME.WATCH;
  const topFinding = findings[0];

  const bannerTitle =
    topFinding?.title ?? "Operations are stable and meeting benchmarks";
  const bannerDetail =
    topFinding?.whatsHappening ?? header.executive_summary;

  const openTopFinding = () => {
    if (!topFinding) return;
    setActiveTab("attention");
    setOpenId(topFinding.id);
    requestAnimationFrame(() => {
      document
        .getElementById(`finding-${topFinding.id}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  };

  return (
    <div className="space-y-4 min-w-0">
      {/* Priority banner / Operational summary */}
      <div
        className="rounded-[14px] border px-5 py-4 flex items-center justify-between gap-5 flex-wrap"
        style={{ backgroundColor: theme.bg, borderColor: theme.line }}
      >
        <div className="flex gap-3.5 items-start min-w-0">
          <div
            className="w-[34px] h-[34px] rounded-[9px] flex items-center justify-center flex-shrink-0 text-white"
            style={{ backgroundColor: theme.text }}
          >
            {statusKey === "HEALTHY" ? (
              <CheckCircle2 className="w-[17px] h-[17px]" />
            ) : (
              <AlertTriangle className="w-[17px] h-[17px]" />
            )}
          </div>
          <div className="min-w-0">
            <p
              className="text-[11px] font-bold uppercase tracking-wide"
              style={{ color: theme.text }}
            >
              {header.status_label}
            </p>
            <p className="font-display font-bold text-[17px] text-ink leading-snug">
              {bannerTitle}
            </p>
            <p className="text-[13px] text-ink-soft mt-0.5 max-w-[640px]">
              {bannerDetail}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="hidden sm:flex items-center gap-2 bg-white border border-line rounded-lg px-3 py-2 shadow-card">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: theme.text }}
            />
            <div>
              <p className="text-[10px] text-muted font-medium uppercase">
                Overall state
              </p>
              <p className="text-[13px] font-bold text-ink">
                {theme.label}
              </p>
            </div>
          </div>

          {topFinding && (
            <button
              onClick={openTopFinding}
              className="inline-flex items-center gap-1.5 text-white text-[13px] font-semibold rounded-[9px] px-4 py-2.5 hover:opacity-90 transition-opacity"
              style={{ backgroundColor: theme.text }}
            >
              View recommendation
              <ArrowRight className="w-[13px] h-[13px]" />
            </button>
          )}
        </div>
      </div>

      {/* Vitals strip */}
      <div>
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="flex items-center gap-2 text-[12.5px] font-bold uppercase tracking-wide text-muted">
            <span
              className="w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: accent.accent }}
            />
            Facility vitals
          </h2>
          <span className="text-[11.5px] text-muted flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            Snapshot {header.report_date}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
          {vitals.map((v) => (
            <VitalCard key={v.metric_name} vital={v} />
          ))}
        </div>
      </div>

      {/* Main tabs */}
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
            {findings.length}
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
            {positive_highlights.length}
          </span>
        </button>
      </div>

      {/* Attention panel */}
      {activeTab === "attention" && (
        <div className="space-y-3">
          {findings.length === 0 && (
            <div className="bg-surface border border-line rounded-[14px] p-10 text-center space-y-2">
              <CheckCircle2 className="w-9 h-9 text-good mx-auto" />
              <p className="font-bold text-ink">No active operational deficits</p>
              <p className="text-[13px] text-muted">
                All core domains are tracking within normal operating parameters.
              </p>
            </div>
          )}
          {findings.map((f, i) => (
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
        <div className="space-y-2.5">
          {positive_highlights.length === 0 && (
            <p className="text-[13px] text-muted italic">
              No standout positive highlights detected for this scenario.
            </p>
          )}
          {positive_highlights.map((h, i) => (
            <div
              key={i}
              className="bg-surface border border-line rounded-[14px] shadow-card px-4 py-3.5 flex items-center gap-3.5"
            >
              <span className="w-[30px] h-[30px] rounded-[9px] bg-good-soft text-good flex items-center justify-center flex-shrink-0">
                <CheckCircle2 className="w-[15px] h-[15px]" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-bold text-[14px] text-ink">{h.title}</p>
                <p className="text-[12.5px] text-muted">{h.domain}</p>
              </div>
              <span className="font-display font-extrabold text-[15.5px] text-good num whitespace-nowrap">
                {h.supporting_metric}
              </span>
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
