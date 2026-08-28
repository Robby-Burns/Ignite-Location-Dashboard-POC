import React from "react";
import {
  ChevronRight,
  CheckCircle2,
  Sparkles,
  Info,
  TrendingUp,
} from "lucide-react";
import type { BriefHighlightCard } from "../types";

interface PositiveFindingCardProps {
  highlight: BriefHighlightCard;
  index: number;
  open: boolean;
  onToggle: () => void;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-bold uppercase tracking-wider text-muted">
      {children}
    </p>
  );
}

export const PositiveFindingCard: React.FC<PositiveFindingCardProps> = ({
  highlight,
  index,
  open,
  onToggle,
}) => {
  const whatsHappening =
    highlight.whats_happening || highlight.plain_language_description;
  const whyItMatters = highlight.why_it_matters || highlight.significance;
  const whatsDriving =
    highlight.whats_driving_it ||
    "The specific operational or clinical factors driving this strong performance cannot be determined from the available data alone.";
  const whatWeCouldLearn =
    highlight.what_we_could_learn ||
    "Consider identifying and preserving the practices contributing to this strong result and determining whether they can be sustained or applied elsewhere.";
  const evidenceList =
    highlight.supporting_metrics && highlight.supporting_metrics.length > 0
      ? highlight.supporting_metrics
      : [highlight.supporting_metric];

  return (
    <div
      className="bg-surface border rounded-[14px] shadow-card overflow-hidden transition-colors duration-150"
      style={{ borderColor: open ? "#BFDBCC" : undefined }}
    >
      {/* Head / Header Button */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3.5 px-4 py-3.5 sm:px-5 text-left hover:bg-line-soft/30 transition-colors"
        aria-expanded={open}
      >
        <span className="w-7 h-7 rounded-lg flex items-center justify-center text-[13px] font-bold flex-shrink-0 bg-good-soft text-good">
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-[14.5px] text-ink">
              {highlight.title}
            </span>
            {highlight.category === "TRAJECTORY_IMPROVEMENT" && (
              <span className="inline-flex items-center gap-1 text-[10.5px] font-bold px-2 py-0.5 rounded-md bg-good-soft text-good border border-good-line/40">
                <TrendingUp className="w-3 h-3" />
                Positive Trajectory
              </span>
            )}
            {highlight.category === "EXEMPLARY_ACHIEVEMENT" && (
              <span className="inline-flex items-center gap-1 text-[10.5px] font-bold px-2 py-0.5 rounded-md bg-good-soft text-good border border-good-line/40">
                <Sparkles className="w-3 h-3" />
                Exemplary
              </span>
            )}
          </div>
          <p className="text-[12.5px] text-muted truncate mt-0.5">
            {highlight.metric_sub || highlight.domain_display_name || highlight.domain}
          </p>
        </div>

        {highlight.metric_value ? (
          <span className="font-display font-extrabold text-[16px] num text-good whitespace-nowrap">
            {highlight.metric_value}
          </span>
        ) : (
          <span className="font-display font-extrabold text-[14.5px] num text-good whitespace-nowrap">
            {highlight.supporting_metric}
          </span>
        )}

        <ChevronRight
          className="w-5 h-5 text-muted flex-shrink-0 transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        />
      </button>

      {/* Expanded Body: 5-Section Deep Analysis */}
      {open && (
        <div className="border-t border-line-soft px-4 sm:px-5 pt-4 pb-5 space-y-4 bg-white/50">
          {/* 1. What's happening */}
          <div>
            <SectionLabel>What's happening</SectionLabel>
            <p className="mt-1 text-[13.5px] text-ink-soft leading-relaxed">
              {whatsHappening}
            </p>
          </div>

          {/* 2. Why it matters */}
          <div>
            <SectionLabel>Why it matters</SectionLabel>
            <p className="mt-1 text-[13.5px] text-ink-soft leading-relaxed">
              {whyItMatters}
            </p>
          </div>

          {/* 3. What's driving it */}
          <div>
            <SectionLabel>What's driving it</SectionLabel>
            <div className="mt-1 text-[13.5px] text-ink-soft leading-relaxed bg-paper border border-line-soft rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Info className="w-4 h-4 text-muted flex-shrink-0 mt-0.5" />
                <p className="text-[13px] text-ink-soft leading-relaxed">
                  {whatsDriving}
                </p>
              </div>
            </div>
          </div>

          {/* 4. What we could learn from it / How leadership might maintain */}
          <div className="rounded-xl border border-good-line bg-good-soft p-3.5 space-y-2">
            <div className="flex items-center gap-1.5 text-good font-bold text-[11px] uppercase tracking-wider">
              <CheckCircle2 className="w-3.5 h-3.5" />
              What we could learn from it
            </div>
            <p className="text-[13.5px] text-ink leading-relaxed font-medium">
              {whatWeCouldLearn}
            </p>
          </div>

          {/* 5. Evidence */}
          {evidenceList.length > 0 && (
            <div>
              <SectionLabel>Evidence</SectionLabel>
              <div className="mt-1.5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {evidenceList.map((metricItem, i) => {
                  const colonIndex = metricItem.indexOf(":");
                  const label =
                    colonIndex > -1
                      ? metricItem.substring(0, colonIndex).trim()
                      : "Supporting metric";
                  const val =
                    colonIndex > -1
                      ? metricItem.substring(colonIndex + 1).trim()
                      : metricItem;

                  return (
                    <div
                      key={i}
                      className="rounded-lg bg-paper border border-line-soft px-3 py-2"
                    >
                      <p className="text-[10.5px] text-muted font-medium">
                        {label}
                      </p>
                      <p className="text-[13px] font-bold text-ink num">{val}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PositiveFindingCard;
