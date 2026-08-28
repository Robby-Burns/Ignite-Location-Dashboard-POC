import React from "react";
import {
  ChevronRight,
  AlertTriangle,
  Link2,
  ListChecks,
} from "lucide-react";
import { Finding, SEVERITY_STYLES, domainLabel } from "../config";

interface FindingCardProps {
  finding: Finding;
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

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  index,
  open,
  onToggle,
}) => {
  const sev = SEVERITY_STYLES[finding.severity];

  return (
    <div
      className="bg-surface border rounded-[14px] shadow-card overflow-hidden"
      style={{ borderColor: open ? sev.line : undefined }}
    >
      {/* Head */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3.5 px-4 py-3.5 sm:px-5 text-left"
        aria-expanded={open}
      >
        <span
          className="w-7 h-7 rounded-lg flex items-center justify-center text-[13px] font-bold flex-shrink-0"
          style={{ backgroundColor: sev.soft, color: sev.color }}
        >
          {index + 1}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-[14.5px] text-ink">{finding.title}</span>
            {finding.isCompound && (
              <span
                className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-md"
                style={{ backgroundColor: sev.soft, color: sev.color }}
              >
                <Link2 className="w-3 h-3" />
                Cross-domain
              </span>
            )}
          </div>
          <p className="text-[12.5px] text-muted truncate">{finding.metricSub}</p>
        </div>

        {finding.metricValue && (
          <span
            className="font-display font-extrabold text-[16px] num whitespace-nowrap"
            style={{ color: sev.color }}
          >
            {finding.metricValue}
          </span>
        )}

        <ChevronRight
          className="w-5 h-5 text-muted flex-shrink-0 transition-transform duration-200"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        />
      </button>

      {/* Body */}
      {open && (
        <div className="border-t px-4 sm:px-5 pt-4 pb-5 space-y-4">
          {/* What's happening */}
          <div>
            <SectionLabel>What's happening</SectionLabel>
            <p className="mt-1 text-[13.5px] text-ink-soft leading-relaxed">
              {finding.whatsHappening}
            </p>
          </div>

          {/* Why it matters */}
          <div>
            <SectionLabel>Why it matters</SectionLabel>
            <p className="mt-1 text-[13.5px] text-ink-soft leading-relaxed">
              {finding.whyItMatters}
            </p>
          </div>

          {/* What's driving it */}
          {finding.driving.length > 0 && (
            <div>
              <SectionLabel>What's driving it</SectionLabel>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {finding.driving.map((d) => (
                  <span
                    key={d}
                    className="text-[11.5px] font-semibold px-2 py-0.5 rounded-md bg-paper border border-line text-ink-soft"
                  >
                    {domainLabel(d)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Recommendation */}
          {finding.recommendation && (
            <div
              className="rounded-xl border p-3.5 space-y-3"
              style={{ backgroundColor: sev.soft, borderColor: sev.line }}
            >
              <div>
                <SectionLabel>What you could consider</SectionLabel>
                <p className="mt-1 text-[13.5px] text-ink leading-relaxed font-medium">
                  {finding.recommendation.consider}
                </p>
              </div>

              <div>
                <SectionLabel>Why this was suggested</SectionLabel>
                <p className="mt-1 text-[12.5px] text-ink-soft leading-relaxed">
                  {finding.recommendation.whySuggested}
                </p>
              </div>

              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-muted">
                <span className="inline-flex items-center gap-1">
                  <ListChecks className="w-3.5 h-3.5" />
                  {finding.recommendation.role}
                </span>
                <span>{finding.recommendation.horizon}</span>
              </div>
            </div>
          )}

          {/* Evidence */}
          {finding.evidence.length > 0 && (
            <div>
              <SectionLabel>Evidence</SectionLabel>
              <div className="mt-1.5 grid grid-cols-2 sm:grid-cols-4 gap-2">
                {finding.evidence.map((e, i) => (
                  <div
                    key={i}
                    className="rounded-lg bg-paper border border-line-soft px-3 py-2"
                  >
                    <p className="text-[10.5px] text-muted font-medium">
                      {e.label || "Verified metric"}
                    </p>
                    <p className="text-[13px] font-bold text-ink num">{e.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!finding.recommendation && (
            <div className="flex items-start gap-2 text-[12.5px] text-muted">
              <AlertTriangle className="w-4 h-4 text-watch flex-shrink-0 mt-0.5" />
              <span>
                A recommendation for this finding is not yet available in the
                current analysis.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default FindingCard;
