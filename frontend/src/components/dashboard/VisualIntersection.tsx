"use client";

import React from "react";
import { AlertTriangle, Flame, ShieldAlert } from "lucide-react";
import { Direction, JunctionStatus, SignalColor } from "@/types/traffic";
import { TrafficLight } from "@/components/ui/TrafficLight";

interface VisualIntersectionProps {
  status: JunctionStatus | null;
}

export const VisualIntersection: React.FC<VisualIntersectionProps> = ({ status }) => {
  // Safe fallbacks if backend status is initializing
  const desiredSignals: Record<Direction, SignalColor> = status?.desired_signals || {
    NORTH: "RED",
    SOUTH: "RED",
    EAST: "RED",
    WEST: "RED",
  };

  const actualSignals: Record<Direction, SignalColor> = status?.actual_signals || {
    NORTH: "RED",
    SOUTH: "RED",
    EAST: "RED",
    WEST: "RED",
  };

  const queues: Record<Direction, number> = status?.queues || {
    NORTH: 0,
    SOUTH: 0,
    EAST: 0,
    WEST: 0,
  };

  const isEmergencyActive = status?.mode === "EMERGENCY";
  const emergencyDir = status?.emergency_direction;
  const hasMismatch = Boolean(status?.has_signal_mismatch);

  return (
    <div className="relative w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl flex flex-col items-center overflow-hidden">
      {/* Top Banner Notice: Critical Mismatch Alert */}
      {hasMismatch && (
        <div className="absolute top-3 left-3 right-3 z-30 flex items-center justify-center gap-2 py-1.5 px-3 bg-rose-950/90 border border-rose-500 rounded-lg text-xs font-semibold text-rose-300 animate-pulse shadow-lg">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <span>WARNING: Physical signal state diverges from backend desired state!</span>
        </div>
      )}

      {/* Title & Phase Subtext */}
      <div className="w-full flex items-center justify-between mb-4 z-10">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Intersection Visualizer (Section 14.3)
          </h2>
          <p className="text-[11px] text-slate-500 font-mono">
            State controlled solely by backend engine
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isEmergencyActive && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-rose-950 border border-rose-600 text-rose-300 text-xs font-bold animate-bounce">
              <Flame className="w-3.5 h-3.5 text-rose-500" />
              EMERGENCY ON {emergencyDir || "LANE"}
            </span>
          )}
        </div>
      </div>

      {/* 4-Way Intersection Grid Layout */}
      <div className="relative w-[340px] h-[340px] sm:w-[380px] sm:h-[380px] flex items-center justify-center mt-2">
        {/* Road Surfaces */}
        {/* Vertical Road (North - South) */}
        <div className="absolute w-28 h-full bg-slate-950 border-x-2 border-dashed border-slate-800 flex flex-col justify-between items-center py-2">
          {/* North Queue Count Badge */}
          <div className="px-2 py-0.5 rounded bg-slate-900/90 border border-slate-700 text-[10px] font-mono text-slate-300 shadow">
            Queue: <span className="font-bold text-amber-400">{queues.NORTH}</span>
          </div>
          {/* South Queue Count Badge */}
          <div className="px-2 py-0.5 rounded bg-slate-900/90 border border-slate-700 text-[10px] font-mono text-slate-300 shadow">
            Queue: <span className="font-bold text-amber-400">{queues.SOUTH}</span>
          </div>
        </div>

        {/* Horizontal Road (West - East) */}
        <div className="absolute h-28 w-full bg-slate-950 border-y-2 border-dashed border-slate-800 flex justify-between items-center px-2">
          {/* West Queue Count Badge */}
          <div className="px-2 py-0.5 rounded bg-slate-900/90 border border-slate-700 text-[10px] font-mono text-slate-300 shadow">
            Queue: <span className="font-bold text-amber-400">{queues.WEST}</span>
          </div>
          {/* East Queue Count Badge */}
          <div className="px-2 py-0.5 rounded bg-slate-900/90 border border-slate-700 text-[10px] font-mono text-slate-300 shadow">
            Queue: <span className="font-bold text-amber-400">{queues.EAST}</span>
          </div>
        </div>

        {/* Intersection Center Box */}
        <div className="absolute w-28 h-28 bg-slate-900/80 border border-slate-700/60 rounded-lg flex items-center justify-center z-10">
          <div className="text-center">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Phase</span>
            <span className="text-xs font-mono font-bold text-amber-400">
              {status?.phase || "ALL_RED"}
            </span>
          </div>
        </div>

        {/* NORTH TRAFFIC LIGHT */}
        <div
          className={`absolute top-2 z-20 transition-transform ${
            emergencyDir === "NORTH" ? "ring-2 ring-rose-500 rounded-2xl p-1 animate-pulse" : ""
          }`}
        >
          <TrafficLight
            direction="NORTH"
            desiredColor={desiredSignals.NORTH}
            actualColor={actualSignals.NORTH}
            size="sm"
            orientation="vertical"
          />
        </div>

        {/* SOUTH TRAFFIC LIGHT */}
        <div
          className={`absolute bottom-2 z-20 transition-transform ${
            emergencyDir === "SOUTH" ? "ring-2 ring-rose-500 rounded-2xl p-1 animate-pulse" : ""
          }`}
        >
          <TrafficLight
            direction="SOUTH"
            desiredColor={desiredSignals.SOUTH}
            actualColor={actualSignals.SOUTH}
            size="sm"
            orientation="vertical"
          />
        </div>

        {/* WEST TRAFFIC LIGHT */}
        <div
          className={`absolute left-2 z-20 transition-transform ${
            emergencyDir === "WEST" ? "ring-2 ring-rose-500 rounded-2xl p-1 animate-pulse" : ""
          }`}
        >
          <TrafficLight
            direction="WEST"
            desiredColor={desiredSignals.WEST}
            actualColor={actualSignals.WEST}
            size="sm"
            orientation="horizontal"
          />
        </div>

        {/* EAST TRAFFIC LIGHT */}
        <div
          className={`absolute right-2 z-20 transition-transform ${
            emergencyDir === "EAST" ? "ring-2 ring-rose-500 rounded-2xl p-1 animate-pulse" : ""
          }`}
        >
          <TrafficLight
            direction="EAST"
            desiredColor={desiredSignals.EAST}
            actualColor={actualSignals.EAST}
            size="sm"
            orientation="horizontal"
          />
        </div>
      </div>

      {/* Legend & Telemetry Indicators */}
      <div className="mt-6 w-full flex flex-wrap items-center justify-around gap-2 pt-3 border-t border-slate-800/80 text-xs font-mono text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
          <span>GREEN</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.8)]" />
          <span>YELLOW</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)]" />
          <span>RED</span>
        </div>
      </div>
    </div>
  );
};