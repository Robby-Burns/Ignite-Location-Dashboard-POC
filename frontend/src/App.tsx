import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ArrowLeft, Layers } from "lucide-react";
import { Header, FacilityOption } from "./components/Header";
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
import { buildFindings, facilityAccentById } from "./config";

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
  const [isResetting, setIsResetting] = useState(false);

  const [technicalData, setTechnicalData] = useState<TechnicalArchitectureReport | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState(false);
  const [technicalError, setTechnicalError] = useState<string | null>(null);

  const facilityAccent = facilityAccentById(selectedFacility);

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

  const handleResetSandbox = async () => {
    setIsResetting(true);
    setSelectedFacility("ignite-oak-brook");
    setSelectedScenario("baseline");
    setView("dashboard");
    try {
      await loadDashboard();
    } finally {
      setIsResetting(false);
    }
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
      {/* Location color strip */}
      <div
        className="fixed inset-y-0 left-0 w-1.5 z-50"
        style={{ backgroundColor: facilityAccent.color }}
        aria-hidden="true"
      />

      {/* Header */}
      <Header
        facilities={facilities}
        selectedFacility={selectedFacility}
        setSelectedFacility={setSelectedFacility}
        selectedScenario={selectedScenario}
        setSelectedScenario={setSelectedScenario}
        facilityAccent={facilityAccent}
        onReset={handleResetSandbox}
        isResetting={isResetting}
      />

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
