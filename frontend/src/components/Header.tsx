import React from "react";
import { Building2, RotateCcw } from "lucide-react";
import logoImg from "../assets/logo.png";
import { SCENARIOS, scenarioById, FacilityAccent } from "../config";

const IGNITE_ORANGE = "#DB3C0A";
const NAVY = "#16233F";
const SLATE = "#5B6B82";
const LINE = "#E2E6EC";

export interface FacilityOption {
  id: string;
  name: string;
}

interface HeaderProps {
  facilities: FacilityOption[];
  selectedFacility: string;
  setSelectedFacility: (id: string) => void;
  selectedScenario: string;
  setSelectedScenario: (id: string) => void;
  facilityAccent: FacilityAccent;
  onReset: () => void;
  isResetting: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  facilities,
  selectedFacility,
  setSelectedFacility,
  selectedScenario,
  setSelectedScenario,
  facilityAccent,
  onReset,
  isResetting,
}) => {
  const accent = scenarioById(selectedScenario);

  return (
    <header
      style={{
        background: "#fff",
        borderBottom: `1px solid ${LINE}`,
        position: "sticky",
        top: 0,
        zIndex: 50,
        boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
      }}
    >
      {/* 1. Orange Top Bar */}
      <div
        style={{
          background: IGNITE_ORANGE,
          color: "#fff",
          padding: "6px 24px 6px 30px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            style={{
              background: "rgba(255, 255, 255, 0.22)",
              border: "1px solid rgba(255, 255, 255, 0.4)",
              padding: "3px 12px",
              borderRadius: 4,
              fontWeight: 700,
              letterSpacing: 0.4,
              fontSize: 12,
              boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            }}
          >
            Prepared for Robby Burns Interview
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={onReset}
            disabled={isResetting}
            style={{
              background: "rgba(255, 255, 255, 0.15)",
              border: "1px solid rgba(255, 255, 255, 0.3)",
              borderRadius: 6,
              color: "#fff",
              fontSize: 11.5,
              padding: "4px 10px",
              display: "flex",
              alignItems: "center",
              gap: 5,
              cursor: isResetting ? "not-allowed" : "pointer",
              fontWeight: 600,
              transition: "background 0.15s ease",
            }}
          >
            <RotateCcw size={12} className={isResetting ? "animate-spin" : ""} />
            {isResetting ? "Resetting Sandbox..." : "Reset Sandbox"}
          </button>
        </div>
      </div>

      {/* 2. White Application Banner */}
      <div
        style={{
          maxWidth: 1440,
          margin: "0 auto",
          padding: "0 24px 0 30px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          minHeight: 62,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        {/* Left Side: Brand & Product Name */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              textDecoration: "none",
            }}
          >
            <img
              src={logoImg}
              alt="Ignite Logo"
              style={{
                height: 38,
                width: 38,
                objectFit: "contain",
                borderRadius: 6,
                boxShadow: "0 2px 5px rgba(0,0,0,0.06)",
                border: `1px solid ${LINE}`,
              }}
            />
            <div>
              <div
                style={{
                  fontFamily: "'Fraunces', Georgia, serif",
                  fontSize: 19,
                  fontWeight: 700,
                  color: NAVY,
                  lineHeight: 1.1,
                }}
              >
                Location Intelligence Agent
              </div>
              <div style={{ fontSize: 11.5, color: SLATE, marginTop: 2, fontWeight: 500 }}>
                Operational Decision Support
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Only the two dropdowns */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          {/* Location Dropdown */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "#FFFFFF",
              border: `1px solid ${LINE}`,
              borderRadius: 8,
              padding: "6px 12px",
              fontSize: 13,
              fontWeight: 500,
              color: "#4B5566",
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                flexShrink: 0,
                backgroundColor: facilityAccent.color,
              }}
            />
            <Building2 style={{ width: 15, height: 15, color: SLATE, flexShrink: 0 }} />
            <select
              value={selectedFacility}
              onChange={(e) => setSelectedFacility(e.target.value)}
              style={{
                background: "transparent",
                fontWeight: 600,
                color: NAVY,
                outline: "none",
                cursor: "pointer",
                border: "none",
                fontSize: 13,
                maxWidth: 220,
              }}
            >
              {facilities.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>

          {/* Scenario Dropdown */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              borderRadius: 8,
              border: `1px solid ${accent.line}`,
              background: accent.soft,
              padding: "6px 12px",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                flexShrink: 0,
                backgroundColor: accent.accent,
              }}
            />
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              style={{
                background: "transparent",
                fontWeight: 700,
                color: accent.text,
                outline: "none",
                cursor: "pointer",
                border: "none",
                fontSize: 13,
                maxWidth: 240,
              }}
            >
              {SCENARIOS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
export default Header;
