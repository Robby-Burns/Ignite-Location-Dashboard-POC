import React, { useState, useEffect } from "react";
import axios from "axios";
import { 
  Building2, 
  Flame, 
  RotateCw, 
  Layers, 
  FileText, 
  HelpCircle, 
  CheckSquare, 
  SlidersHorizontal,
  MessageCircle
} from "lucide-react";
import { FacilityBriefView } from "./components/FacilityBriefView";
import { WhatItMeansView } from "./components/WhatItMeansView";
import { RecommendationsView } from "./components/RecommendationsView";
import { TechnicalView } from "./components/TechnicalView";
import { ChatView } from "./components/ChatView";
import { 
  FacilityBriefReport, 
  FacilityTrendExplanationReport,
  RecommendationReport,
  TechnicalArchitectureReport 
} from "./types";

interface FacilityOption {
  id: string;
  name: string;
}

const DEFAULT_FACILITIES: FacilityOption[] = [
  { id: "ignite-oak-brook", name: "Ignite Oak Brook (Flagship)" },
  { id: "ignite-mokena", name: "Ignite Mokena" },
  { id: "ignite-kansas-city", name: "Ignite Kansas City" },
];

const SCENARIOS = [
  { id: "baseline", label: "Baseline (Balanced Operations)" },
  { id: "staffing_stress", label: "Staffing Stress (HPPD & Agency)" },
  { id: "hospital_transfer_spike", label: "Hospital Transfer Spike (Clinical)" },
  { id: "auth_cliff", label: "Authorization Cliff (Payer/Rehab)" },
  { id: "high_census_strain", label: "High Census Strain (Capacity)" },
  { id: "therapy_disruption", label: "Therapy Disruption (Rehab Delays)" },
];

export const App: React.FC = () => {
  const [facilities, setFacilities] = useState<FacilityOption[]>(DEFAULT_FACILITIES);
  const [selectedFacility, setSelectedFacility] = useState<string>("ignite-oak-brook");
  const [selectedScenario, setSelectedScenario] = useState<string>("baseline");
  const [activeTab, setActiveTab] = useState<"brief" | "meaning" | "recommendations" | "chat" | "technical">("brief");
  
  // Briefing Data State (Story 3.1)
  const [briefData, setBriefData] = useState<FacilityBriefReport | null>(null);
  const [briefLoading, setBriefLoading] = useState<boolean>(true);
  const [briefError, setBriefError] = useState<string | null>(null);

  // Trend Explanation Data State (Story 3.2)
  const [trendData, setTrendData] = useState<FacilityTrendExplanationReport | null>(null);
  const [trendLoading, setTrendLoading] = useState<boolean>(true);
  const [trendError, setTrendError] = useState<string | null>(null);

  // Recommendations Data State (Story 3.3)
  const [recommendationsData, setRecommendationsData] = useState<RecommendationReport | null>(null);
  const [recommendationsLoading, setRecommendationsLoading] = useState<boolean>(true);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);

  // Technical Architecture Data State (Story 3.4)
  const [technicalData, setTechnicalData] = useState<TechnicalArchitectureReport | null>(null);
  const [technicalLoading, setTechnicalLoading] = useState<boolean>(true);
  const [technicalError, setTechnicalError] = useState<string | null>(null);

  // Fetch available facilities dynamically from data source
  useEffect(() => {
    const fetchFacilities = async () => {
      try {
        const res = await axios.get<{ facility_id: string; facility_name: string }[]>("/api/facilities");
        if (Array.isArray(res.data) && res.data.length > 0) {
          setFacilities(
            res.data.map((f) => ({
              id: f.facility_id,
              name: f.facility_id === "ignite-oak-brook" ? `${f.facility_name} (Flagship)` : f.facility_name,
            }))
          );
        }
      } catch {
        // Keep default fallback
      }
    };
    fetchFacilities();
  }, []);

  const fetchBrief = async () => {
    setBriefLoading(true);
    setBriefError(null);
    try {
      const response = await axios.get<FacilityBriefReport>(
        `/api/agent/facility-brief?facility_id=${selectedFacility}&scenario=${selectedScenario}`
      );
      setBriefData(response.data);
    } catch (err: any) {
      setBriefError(err.response?.data?.detail || err.message || "Failed to fetch facility brief.");
    } finally {
      setBriefLoading(false);
    }
  };

  const fetchTrends = async () => {
    setTrendLoading(true);
    setTrendError(null);
    try {
      const response = await axios.get<FacilityTrendExplanationReport>(
        `/api/agent/explain-trends?facility_id=${selectedFacility}&scenario=${selectedScenario}&days_history=30`
      );
      setTrendData(response.data);
    } catch (err: any) {
      setTrendError(err.response?.data?.detail || err.message || "Failed to fetch trend explanations.");
    } finally {
      setTrendLoading(false);
    }
  };

  const fetchRecommendations = async () => {
    setRecommendationsLoading(true);
    setRecommendationsError(null);
    try {
      const response = await axios.get<RecommendationReport>(
        `/api/agent/recommendations?facility_id=${selectedFacility}&scenario=${selectedScenario}&days_history=30`
      );
      setRecommendationsData(response.data);
    } catch (err: any) {
      setRecommendationsError(err.response?.data?.detail || err.message || "Failed to fetch recommendations.");
    } finally {
      setRecommendationsLoading(false);
    }
  };

  const fetchTechnicalArchitecture = async () => {
    setTechnicalLoading(true);
    setTechnicalError(null);
    try {
      const response = await axios.get<TechnicalArchitectureReport>(
        `/api/agent/technical-architecture`
      );
      setTechnicalData(response.data);
    } catch (err: any) {
      setTechnicalError(err.response?.data?.detail || err.message || "Failed to fetch technical architecture.");
    } finally {
      setTechnicalLoading(false);
    }
  };

  useEffect(() => {
    fetchBrief();
    fetchTrends();
    fetchRecommendations();
    fetchTechnicalArchitecture();
  }, [selectedFacility, selectedScenario]);

  const handleRefreshAll = () => {
    fetchBrief();
    fetchTrends();
    fetchRecommendations();
    fetchTechnicalArchitecture();
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Top Header & Branding */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 sm:h-20">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-600 to-amber-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
                <Flame className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight flex items-center gap-2">
                  IGNITE <span className="text-orange-600 font-bold">INTELLIGENCE</span>
                </h1>
                <p className="text-xs text-slate-500 font-semibold tracking-wide">
                  Local Dashboard POC
                </p>
              </div>
            </div>

            {/* Facility & Scenario Controls */}
            <div className="flex items-center gap-3">
              {/* Facility Select */}
              <div className="hidden sm:flex items-center gap-1.5 bg-slate-100/80 px-3 py-1.5 rounded-xl border border-slate-200 text-xs">
                <Building2 className="w-4 h-4 text-slate-500" />
                <select
                  value={selectedFacility}
                  onChange={(e) => setSelectedFacility(e.target.value)}
                  className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer"
                >
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>

              {/* Scenario Switcher */}
              <div className="flex items-center gap-1.5 bg-orange-50 px-3 py-1.5 rounded-xl border border-orange-200 text-xs">
                <SlidersHorizontal className="w-4 h-4 text-orange-600" />
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="bg-transparent font-bold text-orange-900 outline-none cursor-pointer"
                >
                  {SCENARIOS.map((s) => (
                    <option key={s.id} value={s.id}>{s.label}</option>
                  ))}
                </select>
              </div>

              {/* Refresh Button */}
              <button
                onClick={handleRefreshAll}
                className="p-2 text-slate-500 hover:text-orange-600 hover:bg-orange-50 rounded-xl transition-colors"
                title="Refresh Briefing, Trends, and Recommendations"
              >
                <RotateCw className={`w-4 h-4 ${briefLoading || trendLoading || recommendationsLoading || technicalLoading ? "animate-spin text-orange-600" : ""}`} />
              </button>
            </div>
          </div>

          {/* Navigation Tabs (Phase 3 Stories 3.1 - 3.4) */}
          <nav className="flex space-x-1 sm:space-x-4 border-t border-slate-100 overflow-x-auto py-2">
            <button
              onClick={() => setActiveTab("brief")}
              className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                activeTab === "brief"
                  ? "bg-orange-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Facility Brief</span>
              <span className="text-[10px] uppercase font-extrabold bg-white/20 px-1.5 py-0.2 rounded">
                3.1
              </span>
            </button>

            <button
              onClick={() => setActiveTab("meaning")}
              className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                activeTab === "meaning"
                  ? "bg-orange-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>What It Means</span>
              <span className="text-[10px] uppercase font-extrabold bg-white/20 px-1.5 py-0.2 rounded">
                3.2
              </span>
            </button>

            <button
              onClick={() => setActiveTab("recommendations")}
              className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                activeTab === "recommendations"
                  ? "bg-orange-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <CheckSquare className="w-4 h-4" />
              <span>Recommendations</span>
              <span className="text-[10px] uppercase font-extrabold bg-white/20 px-1.5 py-0.2 rounded">
                3.3
              </span>
            </button>

            <button
              onClick={() => setActiveTab("chat")}
              className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                activeTab === "chat"
                  ? "bg-teal-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <MessageCircle className="w-4 h-4" />
              <span>Ask the Facility</span>
              <span className="text-[10px] uppercase font-extrabold bg-white/20 px-1.5 py-0.2 rounded">
                4.3
              </span>
            </button>

            <button
              onClick={() => setActiveTab("technical")}
              className={`flex items-center gap-2 px-3 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all ${
                activeTab === "technical"
                  ? "bg-orange-600 text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>Technical / How It Works</span>
              <span className="text-[10px] uppercase font-bold text-slate-400">
                3.4
              </span>
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === "brief" && (
          <FacilityBriefView data={briefData} loading={briefLoading} error={briefError} />
        )}

        {activeTab === "meaning" && (
          <WhatItMeansView data={trendData} loading={trendLoading} error={trendError} />
        )}

        {activeTab === "recommendations" && (
          <RecommendationsView data={recommendationsData} loading={recommendationsLoading} error={recommendationsError} />
        )}

        {activeTab === "chat" && (
          <ChatView facilityId={selectedFacility} scenario={selectedScenario} />
        )}

        {activeTab === "technical" && (
          <TechnicalView data={technicalData} loading={technicalLoading} error={technicalError} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Ignite Medical Resorts • Ignite Intelligence Local Dashboard POC
      </footer>
    </div>
  );
};
export default App;
