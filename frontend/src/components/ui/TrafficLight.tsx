"use client";

import React from "react";
import { Direction, SignalColor } from "@/types/traffic";

interface TrafficLightProps {
  direction: Direction;
  desiredColor: SignalColor;
  actualColor?: SignalColor;
  size?: "sm" | "md" | "lg";
  orientation?: "vertical" | "horizontal";
  showLabel?: boolean;
}

export const TrafficLight: React.FC<TrafficLightProps> = ({
  direction,
  desiredColor,
  actualColor,
  size = "md",
  orientation = "vertical",
  showLabel = true,
}) => {
  // Check if physical state confirmed by controller diverges from desired
  const hasMismatch = actualColor && actualColor !== desiredColor;

  // Size styling scales
  const bulbDimensions = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8",
  }[size];

  const housingPadding = {
    sm: "p-1.5 gap-1.5",
    md: "p-2 gap-2",
    lg: "p-3 gap-2.5",
  }[size];

  return (
    <div className="flex flex-col items-center">
      {/* Direction & Status Label */}
      {showLabel && (
        <div className="mb-1.5 flex flex-col items-center">
          <span className="text-xs font-bold tracking-wider text-slate-300">
            {direction}
          </span>
          {hasMismatch ? (
            <span className="text-[10px] font-semibold text-rose-400 animate-pulse">
              MISMATCH
            </span>
          ) : (
            <span className="text-[10px] font-mono text-slate-400">
              {desiredColor}
            </span>
          )}
        </div>
      )}

      {/* Traffic Light Housing */}
      <div
        className={`flex ${
          orientation === "vertical" ? "flex-col" : "flex-row"
        } ${housingPadding} items-center justify-center bg-slate-900 border-2 ${
          hasMismatch ? "border-rose-500 animate-pulse" : "border-slate-700"
        } rounded-2xl shadow-xl shadow-black/50`}
      >
        {/* RED BULB */}
        <div
          className={`rounded-full transition-all duration-300 ${bulbDimensions} ${
            desiredColor === "RED"
              ? "bg-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.9)] ring-2 ring-rose-400/50"
              : "bg-rose-950/40 border border-rose-900/40"
          }`}
          title="RED"
        />

        {/* YELLOW BULB */}
        <div
          className={`rounded-full transition-all duration-300 ${bulbDimensions} ${
            desiredColor === "YELLOW"
              ? "bg-amber-400 shadow-[0_0_15px_rgba(251,191,36,0.9)] ring-2 ring-amber-300/50"
              : "bg-amber-950/40 border border-amber-900/40"
          }`}
          title="YELLOW"
        />

        {/* GREEN BULB */}
        <div
          className={`rounded-full transition-all duration-300 ${bulbDimensions} ${
            desiredColor === "GREEN"
              ? "bg-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.9)] ring-2 ring-emerald-300/50"
              : "bg-emerald-950/40 border border-emerald-900/40"
          }`}
          title="GREEN"
        />
      </div>

      {/* Actual Confirmation Sub-badge (if divergent) */}
      {actualColor && actualColor !== desiredColor && (
        <div className="mt-1.5 px-1.5 py-0.5 bg-rose-950/80 border border-rose-500/50 rounded text-[9px] font-mono text-rose-300">
          ACTUAL: {actualColor}
        </div>
      )}
    </div>
  );
};