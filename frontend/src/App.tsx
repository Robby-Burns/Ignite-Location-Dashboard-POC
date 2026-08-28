import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  Building2,
  Flame,
  RotateCw,
  ArrowLeft,
  Layers,
} from "lucide-react";
import { OperationalDashboard } from "./components/OperationalDashboard";
import { ExploreAnalysis } from "./components/ExploreAnalysis";
import { TechnicalView } from "./components/TechnicalView";
import {
  FacilityBriefReport,
  AttentionAnalysisReport,
  RecommendationReport,
  FollowUpQuestionReport,
  TechnicalArchitectureReport,
} from "./types";
import { SCENARIOS, scenarioById, buildFindings } from "./config";

interface FacilityOption {
  id: string;
  name: string;
}

const DEFAULT_FACILITIES: FacilityOption[] = [
  { id: "ignite-oak-brook", name: "Ignite Medical Resort Oak Brook" },
  { id: "ignite-mokena", name: "Ignite Medical Resort Mokena" },
  { id: "ignite-kansas-city", name: "Ignite Medical Resort Kansas City" },
];

export const App: React.FC = () => {
  const [facilities, setFacilities] = useState<FacilityOption[]>(DEFAULT_FACILITIES);
  const [selectedFacility, setSelectedFacility] = useState<string>("ignite-oak-brook");
  const [selectedScenario, setSelectedScenario] = useState<string>("baseline");
  const [view, setView] = useState<"dashboard" | "technical">("dashboard");

  const [brief, setBrief] = useState<FacilityBriefReport | null>(null);
  const [attention, setAttention] = useState<AttentionAnalysisReport | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationReport | null>(null);
  const [questions, setQuestions] = useState<FollowUpQuestionReport | null>(null);

  const [briefLoading, setBriefLoading] = useState(true);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [questionsLoading, setQuestionsLoading] = useState(true);
  const [questionsError, setQuestionsError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [technicalData, setTechnicalData] = useState<TechnicalArchitectureReport | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState(false);
  const [technicalError, setTechnicalError] = useState<string | null>(null);

  const [updatedAt] = useState<string>(() =>
    new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
  );

  const accent = scenarioById(selectedScenario);

  useEffect(() => {
    const fetchFacilities = async () => {
      try {
        const res = await axios.get<{ facility_id: string; facility_name: string }[]>(
          "/api/facilities",
        );
        if (Array.isArray(res.data) && res.data.length > 0) {
          setFacilities(
            res.data.map((f) => ({ id: f.facility_id, name: f.facility_name })),
          );
        }
      } catch {
        // keep fallback facilities
      }
    };
    fetchFacilities();
  }, []);

  const loadDashboard = useCallback(async () => {
    setBriefLoading(true);
    setBriefError(null);
    setQuestionsLoading(true);
    setQuestionsError(null);

    const params = `facility_id=${selectedFacility}&scenario=${selectedScenario}`;
    try {
      const [briefRes, attentionRes, recRes, questionsRes] = await Promise.all([
        axios.get<FacilityBriefReport>(`/api/agent/facility-brief?${params}`),
        axios.get<AttentionAnalysisReport>(`/api/agent/attention-areas?${params}`),
        axios.get<RecommendationReport>(`/api/agent/recommendations?${params}`),
        axios.get<FollowUpQuestionReport>(`/api/agent/follow-up-questions?${params}`),
      ]);
      setBrief(briefRes.data);
      setAttention(attentionRes.data);
      setRecommendations(recRes.data);
      setQuestions(questionsRes.data);
    } catch (err: any) {
      setBriefError(err.response?.data?.detail || err.message || "Failed to fetch facility brief.");
      setQuestionsError(err.response?.data?.detail || err.message || "Failed to fetch suggested questions.");
    } finally {
      setBriefLoading(false);
      setQuestionsLoading(false);
    }
  }, [selectedFacility, selectedScenario]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadDashboard();
    setRefreshing(false);
  };

  const loadTechnical = async () => {
    setTechnicalLoading(true);
    setTechnicalError(null);
    try {
      const res = await axios.get<TechnicalArchitectureReport>(
        "/api/agent/technical-architecture",
      );
      setTechnicalData(res.data);
    } catch (err: any) {
      setTechnicalError(
        err.response?.data?.detail || err.message || "Failed to load technical architecture.",
      );
    } finally {
      setTechnicalLoading(false);
    }
  };

  const findings = useMemo(() => {
    if (!attention || !recommendations) return [];
    return buildFindings(
      attention.prioritized_operational_concerns,
      recommendations.verified_recommendations_summary.recommendations,
    );
  }, [attention, recommendations]);

  const topSummary = useMemo(() => {
    if (!findings || findings.length === 0) return null;
    const top = findings[0];
    return {
      title: top.title,
      metric: top.metricSub,
    };
  }, [findings]);

  const openTechnical = () => {
    setView("technical");
    if (!technicalData && !technicalLoading) loadTechnical();
  };

  return (
    <div className="min-h-screen bg-paper flex flex-col">
      {/* Header */}
      <header className="bg-surface border-b border-line sticky top-0 z-40">
        <div className="max-w-[1440px] mx-auto px-5 sm:px-7 py-3.5">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="w-[38px] h-[38px] rounded-[10px] flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-[#F0703C] to-[#D6501F] text-white shadow-md">
                <Flame className="w-5 h-5" />
              </div>
              <div>
                <h1 className="font-display font-extrabold text-[16.5px] leading-tight tracking-tight text-ink">
                  IGNITE <span className="text-flame">INTELLIGENCE</span>
                </h1>
                <p className="text-[11.5px] text-muted leading-none mt-0.5">
                  Operational Decision Support
                </p>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center gap-2.5 flex-wrap">
              {/* Facility selector */}
              <div className="flex items-center gap-2 bg-surface border border-line rounded-[10px] px-3 py-2 text-[13px] font-medium text-ink-soft">
                <span className="w-1.5 h-1.5 rounded-full bg-flame flex-shrink-0" />
                <Building2 className="w-4 h-4 text-muted flex-shrink-0" />
                <select
                  value={selectedFacility}
                  onChange={(e) => setSelectedFacility(e.target.value)}
                  className="bg-transparent font-semibold text-ink outline-none cursor-pointer max-w-[200px]"
                >
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Scenario selector */}
              <div
                className="flex items-center gap-2 rounded-[10px] border px-3 py-2 text-[13px] font-medium"
                style={{ backgroundColor: accent.soft, borderColor: accent.line }}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ backgroundColor: accent.accent }}
                />
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="bg-transparent font-bold outline-none cursor-pointer max-w-[180px]"
                  style={{ color: accent.text }}
                >
                  {SCENARIOS.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Updated + refresh */}
              <div className="flex items-center gap-2">
                <span className="text-[12px] text-muted whitespace-nowrap">
                  Updated {updatedAt}
                </span>
                <button
                  onClick={handleRefresh}
                  aria-label="Refresh analysis"
                  title="Refresh analysis"
                  className="w-8 h-8 rounded-lg border border-line bg-surface flex items-center justify-center text-ink-soft hover:bg-line-soft transition-colors"
                >
                  <RotateCw
                    className={`w-4 h-4 ${refreshing || briefLoading ? "animate-spin text-flame" : ""}`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-5 sm:px-7 py-5 pb-12">
        {view === "dashboard" ? (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4 items-start">
            <OperationalDashboard
              brief={brief}
              findings={findings}
              loading={briefLoading}
              error={briefError}
              scenario={selectedScenario}
            />
            <div className="xl:sticky xl:top-[84px]">
              <ExploreAnalysis
                facilityId={selectedFacility}
                scenario={selectedScenario}
                questionsData={questions}
                questionsLoading={questionsLoading}
                questionsError={questionsError}
                onRefreshQuestions={loadDashboard}
                topSummary={topSummary}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <button
              onClick={() => setView("dashboard")}
              className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-flame hover:text-flame-deep transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to dashboard
            </button>
            <TechnicalView
              data={technicalData}
              loading={technicalLoading}
              error={technicalError}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-surface border-t border-line py-4">
        <div className="max-w-[1440px] mx-auto px-5 sm:px-7 flex items-center justify-between gap-3 flex-wrap text-[12px] text-muted">
          <span>Ignite Medical Resorts · Ignite Intelligence POC</span>
          <button
            onClick={openTechnical}
            className="inline-flex items-center gap-1.5 font-semibold text-ink-soft hover:text-flame transition-colors"
          >
            <Layers className="w-3.5 h-3.5" />
            How it works
          </button>
        </div>
      </footer>
    </div>
  );
};

export default App;
