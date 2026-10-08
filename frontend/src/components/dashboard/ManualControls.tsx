"use client";

import React from "react";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  Loader2,
  Lock,
  Play,
  RotateCcw,
  Sliders,
} from "lucide-react";
import { Direction, JunctionStatus } from "@/types/traffic";

interface ManualControlsProps {
  status: JunctionStatus | null;
  onManualGreen: (direction: Direction) => Promise<void>;
  onReturnToAutomatic: () => Promise<void>;
  actionInProgress: string | null;
}

export const ManualControls: React.FC<ManualControlsProps> = ({
  status,
  onManualGreen,
  onReturnToAutomatic,
  actionInProgress,
}) => {
  const currentMode = status?.mode;
  const isManualActive = currentMode === "MANUAL";
  const manualDir = status?.manual_direction;
  const isDegraded = currentMode === "DEGRADED";

  const directions: Array<{
    direction: Direction;
    label: string;
    icon: React.ReactNode;
  }> = [
    {
      direction: "NORTH",
      label: "North Green",
      icon: <ArrowDown className="w-4 h-4" />,
    },
    {
      direction: "SOUTH",
      label: "South Green",
      icon: <ArrowUp className="w-4 h-4" />,
    },
    {
      direction: "EAST",
      label: "East Green",
      icon: <ArrowRight className="w-4 h-4" />,
    },
    {
      direction: "WEST",
      label: "West Green",
      icon: <ArrowLeft className="w-4 h-4" />,
    },
  ];

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-sky-950/80 border border-sky-700/50 rounded-lg text-sky-400">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Manual Override Controls (Section 14.4)
            </h2>
            <p className="text-xs text-slate-500 font-mono">
              Admin intent dispatching directly to backend state machine
            </p>
          </div>
        </div>

        {/* Current State Status Tag */}
        {isManualActive ? (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-bold bg-sky-950 border border-sky-500 text-sky-300 animate-pulse">
            <Lock className="w-3.5 h-3.5" />
            MANUAL: {manualDir || "LOCKED"}
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-medium bg-slate-950 border border-slate-800 text-slate-400">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            AUTO ACTIVE
          </span>
        )}
      </div>

      {/* Override Notice if Degraded */}
      {isDegraded && (
        <div className="my-3 p-2.5 bg-rose-950/50 border border-rose-800 rounded-xl text-xs text-rose-300 flex items-center gap-2">
          <Lock className="w-4 h-4 flex-shrink-0 text-rose-400" />
          <span>
            Manual overrides are disabled while junction is in DEGRADED safe mode.
          </span>
        </div>
      )}

      {/* 4 Directions Manual Green Triggers */}
      <div className="grid grid-cols-2 gap-2.5 my-3.5">
        {directions.map(({ direction, label, icon }) => {
          const isCurrentActiveGreen = isManualActive && manualDir === direction;
          const isLoading = actionInProgress === `manual-${direction}`;

          return (
            <button
              key={direction}
              onClick={() => onManualGreen(direction)}
              disabled={Boolean(actionInProgress) || isDegraded}
              className={`flex items-center justify-between p-3 rounded-xl border text-xs font-semibold transition-all duration-200 ${
                isCurrentActiveGreen
                  ? "bg-emerald-950/80 border-emerald-500 text-emerald-300 shadow-[0_0_15px_rgba(16,185,129,0.3)] ring-1 ring-emerald-400"
                  : "bg-slate-950 border-slate-800 text-slate-200 hover:bg-slate-800/80 hover:border-slate-700"
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <div className="flex items-center gap-2">
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin text-sky-400" />
                ) : (
                  icon
                )}
                <span className="font-mono">{label}</span>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                {isCurrentActiveGreen ? "ACTIVE" : "REQ"}
              </span>
            </button>
          );
        })}
      </div>

      {/* Return to Automatic Mode Action */}
      <div className="pt-3 border-t border-slate-800/80">
        <button
          onClick={onReturnToAutomatic}
          disabled={Boolean(actionInProgress) || !isManualActive}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border font-semibold text-xs transition-all duration-200 bg-slate-800 hover:bg-slate-700/80 border-slate-700 text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
        >
          {actionInProgress === "return-auto" ? (
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
          ) : (
            <RotateCcw className="w-4 h-4 text-emerald-400" />
          )}
          <span>RETURN TO AUTOMATIC SCHEDULING</span>
        </button>
      </div>
    </div>
  );
};