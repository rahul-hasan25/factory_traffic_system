"use client";

import React from "react";
import { AlertCircle, ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Car, Flame, Layers } from "lucide-react";
import { Direction, JunctionStatus } from "@/types/traffic";

interface QueueMetricsProps {
  status: JunctionStatus | null;
}

export const QueueMetrics: React.FC<QueueMetricsProps> = ({ status }) => {
  const queues: Record<Direction, number> = status?.queues || {
    NORTH: 0,
    SOUTH: 0,
    EAST: 0,
    WEST: 0,
  };

  const totalWaiting = Object.values(queues).reduce((sum, count) => sum + count, 0);
  const emergencyDir = status?.emergency_direction;

  // Approach configuration metadata
  const approaches: Array<{
    direction: Direction;
    label: string;
    icon: React.ReactNode;
  }> = [
    {
      direction: "NORTH",
      label: "North Approach",
      icon: <ArrowDown className="w-4 h-4 text-sky-400" />,
    },
    {
      direction: "SOUTH",
      label: "South Approach",
      icon: <ArrowUp className="w-4 h-4 text-emerald-400" />,
    },
    {
      direction: "EAST",
      label: "East Approach",
      icon: <ArrowLeft className="w-4 h-4 text-amber-400" />,
    },
    {
      direction: "WEST",
      label: "West Approach",
      icon: <ArrowRight className="w-4 h-4 text-purple-400" />,
    },
  ];

  // Dynamically compute visual density badge
  const getQueueDensityBadge = (count: number) => {
    if (count >= 6) {
      return {
        label: "HEAVY CONGESTION",
        classes: "bg-rose-950/60 text-rose-300 border-rose-600/50",
      };
    } else if (count >= 3) {
      return {
        label: "MODERATE",
        classes: "bg-amber-950/60 text-amber-300 border-amber-600/50",
      };
    } else if (count > 0) {
      return {
        label: "LIGHT",
        classes: "bg-emerald-950/60 text-emerald-300 border-emerald-600/50",
      };
    }
    return {
      label: "CLEAR",
      classes: "bg-slate-800 text-slate-400 border-slate-700",
    };
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Header Metric Summary */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-950/80 border border-indigo-700/50 rounded-lg text-indigo-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Live Queue Status (Section 14.1)
            </h2>
            <p className="text-xs text-slate-500 font-mono">
              Real-time vehicle backlog by approach lane
            </p>
          </div>
        </div>

        {/* Total Waiting Count Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl">
          <Car className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-mono text-slate-400">TOTAL:</span>
          <span className="text-sm font-mono font-bold text-white">{totalWaiting}</span>
        </div>
      </div>

      {/* Grid of 4 Approach Lanes */}
      <div className="grid grid-cols-2 gap-3 my-4">
        {approaches.map(({ direction, label, icon }) => {
          const count = queues[direction];
          const isEmergency = emergencyDir === direction;
          const density = getQueueDensityBadge(count);

          return (
            <div
              key={direction}
              className={`relative p-3.5 rounded-xl border transition-all duration-200 bg-slate-950/60 ${
                isEmergency
                  ? "border-rose-500 ring-2 ring-rose-500/20 bg-rose-950/20 animate-pulse"
                  : "border-slate-800/80 hover:border-slate-700"
              }`}
            >
              {/* Emergency Warning Tag */}
              {isEmergency && (
                <div className="absolute top-2 right-2 flex items-center gap-1 text-[10px] font-bold text-rose-400 uppercase">
                  <Flame className="w-3 h-3 text-rose-500" />
                  EMERGENCY
                </div>
              )}

              {/* Lane Title & Direction Icon */}
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1 rounded bg-slate-900 border border-slate-800">{icon}</div>
                <span className="text-xs font-semibold text-slate-300 font-mono">{label}</span>
              </div>

              {/* Counter Display & Density Pill */}
              <div className="flex items-end justify-between mt-2">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold font-mono text-white">{count}</span>
                  <span className="text-[10px] text-slate-500 font-mono">units</span>
                </div>

                <span
                  className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded border ${density.classes}`}
                >
                  {density.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer System Notice */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span className="flex items-center gap-1 text-slate-500">
          <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
          Queue weights prioritized by Safety & Scheduling engine
        </span>
        <span className="text-slate-500">Auto-balanced</span>
      </div>
    </div>
  );
};