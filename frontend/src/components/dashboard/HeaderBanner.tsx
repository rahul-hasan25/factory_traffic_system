"use client";

import React from "react";
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  Cpu,
  Radio,
  RefreshCw,
  ShieldAlert,
  Sliders,
  WifiOff,
} from "lucide-react";
import { ControllerStatus, JunctionMode, JunctionStatus } from "@/types/traffic";

interface HeaderBannerProps {
  status: JunctionStatus | null;
  isBackendConnected: boolean;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const HeaderBanner: React.FC<HeaderBannerProps> = ({
  status,
  isBackendConnected,
  onRefresh,
  isRefreshing = false,
}) => {
  // 1. Operating Mode Visual Configuration (Section 14.2)
  const getModeBadge = (mode?: JunctionMode) => {
    switch (mode) {
      case "AUTOMATIC":
        return {
          label: "AUTOMATIC",
          icon: <Activity className="w-3.5 h-3.5 mr-1" />,
          classes: "bg-emerald-950/70 text-emerald-300 border-emerald-500/50",
        };
      case "MANUAL":
        return {
          label: "MANUAL OVERRIDE",
          icon: <Sliders className="w-3.5 h-3.5 mr-1 text-sky-400" />,
          classes: "bg-sky-950/70 text-sky-300 border-sky-500/50 animate-pulse",
        };
      case "EMERGENCY":
        return {
          label: "EMERGENCY PREEMPTION",
          icon: <AlertOctagon className="w-3.5 h-3.5 mr-1 text-rose-400" />,
          classes: "bg-rose-950/80 text-rose-300 border-rose-500 animate-bounce",
        };
      case "DEGRADED":
        return {
          label: "DEGRADED / FAIL-SAFE",
          icon: <ShieldAlert className="w-3.5 h-3.5 mr-1 text-amber-400" />,
          classes: "bg-amber-950/70 text-amber-300 border-amber-500/60 animate-pulse",
        };
      default:
        return {
          label: "INITIALIZING",
          icon: <Radio className="w-3.5 h-3.5 mr-1" />,
          classes: "bg-slate-800 text-slate-300 border-slate-600",
        };
    }
  };

  // 2. Hardware Controller Connectivity Badge (Section 14.6)
  const getControllerBadge = (ctrlStatus?: ControllerStatus) => {
    if (!isBackendConnected) {
      return {
        label: "BACKEND OFFLINE",
        icon: <WifiOff className="w-3.5 h-3.5 mr-1 text-rose-400" />,
        classes: "bg-rose-950/80 text-rose-300 border-rose-600",
      };
    }

    switch (ctrlStatus) {
      case "ONLINE":
        return {
          label: "CONTROLLER ONLINE",
          icon: <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" />,
          classes: "bg-emerald-950/60 text-emerald-300 border-emerald-600/40",
        };
      case "OFFLINE":
        return {
          label: "CONTROLLER OFFLINE",
          icon: <WifiOff className="w-3.5 h-3.5 mr-1 text-rose-400" />,
          classes: "bg-rose-950/80 text-rose-300 border-rose-500 animate-pulse",
        };
      case "DEGRADED":
        return {
          label: "CONTROLLER DEGRADED",
          icon: <AlertOctagon className="w-3.5 h-3.5 mr-1 text-amber-400" />,
          classes: "bg-amber-950/70 text-amber-300 border-amber-500/50",
        };
      default:
        return {
          label: "UNKNOWN",
          icon: <Cpu className="w-3.5 h-3.5 mr-1 text-slate-400" />,
          classes: "bg-slate-800 text-slate-300 border-slate-600",
        };
    }
  };

  const modeBadge = getModeBadge(status?.mode);
  const controllerBadge = getControllerBadge(status?.controller_status);

  return (
    <header className="w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-4 md:p-6 backdrop-blur-md shadow-2xl mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left Side: System & Junction Title */}
        <div className="flex items-center gap-3">
          <div className="p-3 bg-indigo-950/80 border border-indigo-700/50 rounded-xl shadow-inner">
            <Cpu className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Factory Traffic Control
              </h1>
              <span className="px-2 py-0.5 text-xs font-mono font-semibold bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 rounded-md">
                Junction {status?.junction_id || "A"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              IoT Edge Traffic Signal Management & Safety Engine
            </p>
          </div>
        </div>

        {/* Right Side: Telemetry Badges & Refresh Action */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Active Operating Mode Badge */}
          <div
            className={`flex items-center px-3 py-1.5 rounded-lg border text-xs font-semibold tracking-wider ${modeBadge.classes}`}
          >
            {modeBadge.icon}
            {modeBadge.label}
          </div>

          {/* Active Traffic Phase Badge */}
          <div className="flex items-center px-3 py-1.5 rounded-lg border bg-slate-800/80 border-slate-700 text-slate-200 text-xs font-mono">
            <span className="text-slate-400 mr-1.5">PHASE:</span>
            <span className="font-bold text-amber-400">
              {status?.phase || "ALL_RED"}
            </span>
          </div>

          {/* Hardware Controller Status Badge */}
          <div
            className={`flex items-center px-3 py-1.5 rounded-lg border text-xs font-semibold tracking-wider ${controllerBadge.classes}`}
          >
            {controllerBadge.icon}
            {controllerBadge.label}
          </div>

          {/* Manual Refresh Trigger */}
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="p-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-slate-300 hover:text-white transition-colors disabled:opacity-50"
              title="Force Sync State"
              aria-label="Force Sync State"
            >
              <RefreshCw
                className={`w-4 h-4 ${isRefreshing ? "animate-spin text-indigo-400" : ""}`}
              />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};