import React from "react";
import {
  Database,
  Calculator,
  Brain,
  ShieldCheck,
  ArrowRight,
  AlertTriangle,
  AlertOctagon,
  CheckCircle2,
  Info,
  ExternalLink,
  Layers,
  GitBranch,
  Lock,
} from "lucide-react";
import { TechnicalArchitectureReport, ArchitectureLayer, DataFlowStep } from "../types";

interface TechnicalViewProps {
  data: TechnicalArchitectureReport | null;
  loading: boolean;
  error: string | null;
}

export const TechnicalView: React.FC<TechnicalViewProps> = ({
  data,
  loading,
  error,
}) => {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="text-slate-600 font-medium animate-pulse">
          Loading technical architecture documentation...
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 space-y-3">
        <div className="flex items-center space-x-3">
          <AlertOctagon className="w-6 h-6 text-rose-600 flex-shrink-0" />
          <h3 className="text-lg font-bold">
            Failed to Load Technical Architecture
          </h3>
        </div>
        <p className="text-sm text-rose-700">
          {error || "No architecture data returned."}
        </p>
      </div>
    );
  }

  const getLayerIcon = (layerName: string) => {
    if (layerName.toLowerCase().includes("data source"))
      return <Database className="w-5 h-5 text-blue-600" />;
    if (layerName.toLowerCase().includes("numerical"))
      return <Calculator className="w-5 h-5 text-emerald-600" />;
    if (layerName.toLowerCase().includes("ai"))
      return <Brain className="w-5 h-5 text-purple-600" />;
    if (layerName.toLowerCase().includes("evidence"))
      return <ShieldCheck className="w-5 h-5 text-amber-600" />;
    return <Layers className="w-5 h-5 text-slate-600" />;
  };

  const getLayerBorderColor = (layerName: string) => {
    if (layerName.toLowerCase().includes("data source"))
      return "border-blue-200 bg-blue-50/30";
    if (layerName.toLowerCase().includes("numerical"))
      return "border-emerald-200 bg-emerald-50/30";
    if (layerName.toLowerCase().includes("ai"))
      return "border-purple-200 bg-purple-50/30";
    if (layerName.toLowerCase().includes("evidence"))
      return "border-amber-200 bg-amber-50/30";
    return "border-slate-200 bg-slate-50/30";
  };

  const renderLayer = (layer: ArchitectureLayer, index: number) => (
    <div
      key={index}
      className={`rounded-2xl border p-5 sm:p-6 space-y-3 ${getLayerBorderColor(layer.name)}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {getLayerIcon(layer.name)}
          <h3 className="text-base font-bold text-slate-900">{layer.name}</h3>
        </div>
        {layer.is_simulated && (
          <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-orange-100 text-orange-800 border border-orange-200 uppercase tracking-wide">
            <AlertTriangle className="w-3 h-3" />
            Simulated
          </span>
        )}
      </div>
      <p className="text-sm text-slate-700 leading-relaxed">
        {layer.description}
      </p>
      {layer.components.length > 0 && (
        <div className="space-y-1.5">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Key Components
          </h4>
          <ul className="space-y-1">
            {layer.components.map((comp, i) => (
              <li
                key={i}
                className="text-xs text-slate-600 flex items-start gap-2"
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 mt-0.5" />
                <span>{comp}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderDataFlowStep = (step: DataFlowStep, isLast: boolean) => (
    <div key={step.step} className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full bg-purple-100 border-2 border-purple-300 flex items-center justify-center text-xs font-black text-purple-700">
          {step.step}
        </div>
        {!isLast && <div className="w-0.5 h-full bg-purple-200 min-h-[2rem]" />}
      </div>
      <div className="pb-6 space-y-1">
        <h4 className="text-sm font-bold text-slate-900">{step.name}</h4>
        <p className="text-xs text-slate-600 leading-relaxed">
          {step.description}
        </p>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <span className="font-semibold">{step.source_component}</span>
          <ArrowRight className="w-3 h-3 text-purple-400" />
          <span className="font-semibold">{step.output_component}</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header Banner */}
      <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-slate-900 to-purple-950 text-white shadow-md border border-purple-800/40">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 text-xs font-extrabold uppercase tracking-wider rounded-full bg-purple-600 text-white shadow-xs">
              CIO & Technical Architecture
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
            {data.report_title}
          </h2>
          <p className="text-base sm:text-lg leading-relaxed text-purple-100">
            {data.overview}
          </p>
        </div>
      </div>

      {/* Architecture Layers */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Layers className="w-5 h-5 text-purple-600" />
          Architecture Layers
        </h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {renderLayer(data.data_source, 0)}
          {renderLayer(data.numerical_analysis, 1)}
          {renderLayer(data.ai_interpretation, 2)}
          {renderLayer(data.evidence_grounding, 3)}
        </div>
      </div>

      {/* Data Flow Pipeline */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 sm:p-6 space-y-5">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-purple-600" />
          Data Flow Pipeline
        </h3>
        <p className="text-sm text-slate-600">
          How data moves through the system from retrieval to user-facing
          analysis:
        </p>
        <div className="space-y-0">
          {data.data_flow.map((step, i) =>
            renderDataFlowStep(step, i === data.data_flow.length - 1)
          )}
        </div>
      </div>

      {/* Separation of Responsibilities */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 sm:p-6 space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          Separation of Responsibilities
        </h3>
        <p className="text-sm text-slate-600">
          Each layer has a clearly defined responsibility boundary. This
          separation ensures numerical accuracy and traceability.
        </p>
        <div className="space-y-3">
          {Object.entries(data.separation_of_responsibilities).map(
            ([layer, responsibility]) => (
              <div
                key={layer}
                className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100"
              >
                <Lock className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-xs font-bold text-slate-800">
                    {layer}
                  </span>
                  <p className="text-xs text-slate-600 mt-0.5">
                    {responsibility}
                  </p>
                </div>
              </div>
            )
          )}
        </div>
      </div>

      {/* Limitations */}
      <div className="bg-amber-50 rounded-2xl border border-amber-200 p-5 sm:p-6 space-y-4">
        <h3 className="text-lg font-bold text-amber-900 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-600" />
          POC Limitations & Boundaries
        </h3>
        <ul className="space-y-2">
          {data.limitations.map((limitation, i) => (
            <li
              key={i}
              className="text-sm text-amber-800 flex items-start gap-2"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-1" />
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Future Integration */}
      <div className="bg-blue-50 rounded-2xl border border-blue-200 p-5 sm:p-6 space-y-3">
        <h3 className="text-lg font-bold text-blue-900 flex items-center gap-2">
          <ExternalLink className="w-5 h-5 text-blue-600" />
          Future Domo Integration
        </h3>
        <p className="text-sm text-blue-800 leading-relaxed">
          {data.future_integration}
        </p>
      </div>

      {/* Disclaimers */}
      <div className="p-5 rounded-2xl bg-slate-100/80 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-center gap-2 font-bold text-slate-800">
          <Info className="w-4 h-4 text-slate-500" />
          Transparency Disclaimers
        </div>
        <ul className="space-y-1">
          {data.disclaimers.map((disclaimer, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-slate-400">•</span>
              <span>{disclaimer}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
