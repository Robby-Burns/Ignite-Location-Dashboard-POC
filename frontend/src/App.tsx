import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ArrowLeft, Layers } from "lucide-react";
import { Header, FacilityOption } from "./components/Header";
import { OperationalDashboard } from "./components/OperationalDashboard";
import { ExploreAnalysis } from "./components/ExploreAnalysis";
import { TechnicalView } from "./components/TechnicalView";
import {
  FacilityBriefReport,
  FollowUpQuestionReport,
  TechnicalArchitectureReport,
  UnifiedFacilityAnalysisResponse,
} from "./types";
import { Finding, facilityAccentById } from "./config";

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

  const [analysis, setAnalysis] = useState<UnifiedFacilityAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingData, setIsUpdatingData] = useState(false);

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

  const loadDashboard = useCallback(
    async (forceRefresh = false) => {
      setLoading(true);
      setError(null);

      const params = `facility_id=${selectedFacility}&scenario=${selectedScenario}${forceRefresh ? "&force_refresh=true" : ""}`;
      try {
        // Single unified structured analysis call
        const res = await axios.get<UnifiedFacilityAnalysisResponse>(
          `/api/agent/facility-analysis?${params}`,
        );
        setAnalysis(res.data);
      } catch (err: any) {
        setError(
          err.response?.data?.detail || err.message || "Failed to fetch facility analysis.",
        );
      } finally {
        setLoading(false);
      }
    },
    [selectedFacility, selectedScenario],
  );

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const handleTryNewFacilityData = async () => {
    setIsUpdatingData(true);
    try {
      await axios.post(
        `/api/facilities/${selectedFacility}/try-new-data?scenario=${selectedScenario}`,
      );
      await loadDashboard(true);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to update synthetic facility data.",
      );
    } finally {
      setIsUpdatingData(false);
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

  // Construct brief report from unified response
  const brief: FacilityBriefReport | null = useMemo(() => {
    if (!analysis) return null;
    return {
      header: {
        facility_id: analysis.facility_id,
        facility_name: analysis.facility_name,
        location: "Midwest / Chicago Metro",
        report_date: analysis.report_date,
        scenario: analysis.scenario,
        overall_status: analysis.overall_status,
        status_label: analysis.status_label,
        executive_summary: analysis.executive_summary,
      },
      vitals: analysis.vitals,
      positive_highlights: analysis.positive_highlights,
      watch_items: [],
      action_items: [],
      limitations: {
        is_simulated_domo: true,
        data_freshness: analysis.data_freshness,
        disclaimer: analysis.limitations_disclaimer,
        data_completeness_notes: [
          `Analysis Mode: ${analysis.analysis_state === "LLM_ANALYSIS" ? "LLM Analysis (Live)" : "Deterministic Fallback"}`,
          `Model: ${analysis.audit_receipt?.model || "Gemini 2.5 Flash Lite"}`,
          `Latency: ${analysis.audit_receipt?.latency_ms ? (analysis.audit_receipt.latency_ms / 1000).toFixed(2) + "s" : "N/A"}`,
        ],
      },
      generated_at: analysis.data_freshness,
    };
  }, [analysis]);

  // Use LLM-generated findings directly
  const findings: Finding[] = useMemo(() => {
    if (!analysis) return [];
    return analysis.findings.map((f) => ({
      id: f.id,
      title: f.title,
      domain: f.domain,
      domainDisplayName: f.domainDisplayName,
      severity: f.severity,
      metricValue: f.metricValue,
      metricSub: f.metricSub,
      whatsHappening: f.whatsHappening,
      whyItMatters: f.whyItMatters,
      driving: f.driving,
      isCompound: f.isCompound,
      recommendation: f.recommendation
        ? {
            consider: f.recommendation.consider,
            whySuggested: f.recommendation.whySuggested,
            role: f.recommendation.role,
            horizon: f.recommendation.horizon,
          }
        : null,
      evidence: f.evidence,
    }));
  }, [analysis]);

  const questionsData: FollowUpQuestionReport | null = useMemo(() => {
    if (!analysis) return null;
    return {
      facility_id: analysis.facility_id,
      facility_name: analysis.facility_name,
      scenario: analysis.scenario,
      analysis_state: analysis.analysis_state === "LLM_ANALYSIS" ? "ANALYSIS_COMPLETE" : "AI_ANALYSIS_UNAVAILABLE",
      questions: analysis.suggested_questions,
      generated_at: analysis.data_freshness,
    };
  }, [analysis]);

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
        onTryNewData={handleTryNewFacilityData}
        isUpdatingData={isUpdatingData}
      />

      {/* Main */}
      <main className="flex-1 max-w-[1440px] w-full mx-auto px-5 sm:px-7 py-5 pb-12">
        {view === "dashboard" ? (
          <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-4 items-start">
            <OperationalDashboard
              brief={brief}
              findings={findings}
              loading={loading}
              error={error}
              scenario={selectedScenario}
            />
            <div className="xl:sticky xl:top-[84px]">
              <ExploreAnalysis
                facilityId={selectedFacility}
                scenario={selectedScenario}
                questionsData={questionsData}
                questionsLoading={loading}
                questionsError={error}
                onRefreshQuestions={loadDashboard}
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
