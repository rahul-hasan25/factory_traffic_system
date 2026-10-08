"use client";

import React from "react";
import { AlertTriangle, Loader2, RefreshCw, WifiOff } from "lucide-react";
import { useTrafficDashboard } from "@/hooks/useTrafficDashboard";
import { HeaderBanner } from "@/components/dashboard/HeaderBanner";
import { VisualIntersection } from "@/components/dashboard/VisualIntersection";
import { QueueMetrics } from "@/components/dashboard/QueueMetrics";
import { ManualControls } from "@/components/dashboard/ManualControls";
import { SimulationPanel } from "@/components/dashboard/SimulationPanel";
import { AuditActivityLog } from "@/components/dashboard/AuditActivityLog";
import { AlertNotice } from "@/components/ui/AlertNotice";

export default function TrafficDashboardPage() {
  const {
    status,
    history,
    alerts,
    isInitialLoading,
    isBackendConnected,
    lastError,
    actionInProgress,
    refreshNow,
    executeManualGreen,
    executeReturnToAutomatic,
    simulateVehicleArrival,
    simulateVehicleClearance,
    simulateControllerAck,
    simulateControllerStatus,
  } = useTrafficDashboard({
    junctionId: "A",
    pollingIntervalMs: 1000,
    historyLimit: 40,
  });

  // Initial Full-Screen Loading State
  if (isInitialLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-200">
        <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
        <h2 className="text-lg font-mono font-semibold">Connecting to Traffic Control Engine...</h2>
        <p className="text-xs font-mono text-slate-500 mt-1">Polling backend APIs at 127.0.0.1:8000</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8 font-sans">
      <div className="max-w-7xl mx-auto flex flex-col gap-6">
        {/* 1. Header & Live Status Telemetry (Section 14.1, 14.2 & 14.6) */}
        <HeaderBanner
          status={status}
          isBackendConnected={isBackendConnected}
          onRefresh={refreshNow}
          isRefreshing={Boolean(actionInProgress)}
        />

        {/* 2. Global Error / Offline Notice (Section 14.10) */}
        {!isBackendConnected && (
          <div className="w-full p-4 bg-rose-950/80 border border-rose-600 rounded-2xl flex items-center justify-between text-rose-200 shadow-xl">
            <div className="flex items-center gap-3">
              <WifiOff className="w-5 h-5 text-rose-400 animate-pulse flex-shrink-0" />
              <div>
                <h3 className="text-sm font-bold">Backend Connection Lost</h3>
                <p className="text-xs text-rose-300/90">
                  {lastError || "Failed to reach Django server. Ensure backend service is running on port 8000."}
                </p>
              </div>
            </div>
            <button
              onClick={refreshNow}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-900 hover:bg-rose-800 border border-rose-500 rounded-lg text-xs font-mono font-semibold transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>RECONNECT</span>
            </button>
          </div>
        )}

        {/* 3. Active Alert Stream (Section 14.5 & 14.6) */}
        {alerts.length > 0 && (
          <div className="w-full flex flex-col">
            {alerts.map((alert) => (
              <AlertNotice key={alert.id} alert={alert} />
            ))}
          </div>
        )}

        {/* 4. Top Grid: Intersection Visualizer & Queue Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Visual 4-Way Intersection (Section 14.3) */}
          <div className="lg:col-span-5 flex">
            <VisualIntersection status={status} />
          </div>

          {/* Real-time Vehicle Queue Metrics (Section 14.1 & 14.2) */}
          <div className="lg:col-span-7 flex">
            <QueueMetrics status={status} />
          </div>
        </div>

        {/* 5. Middle Grid: Manual Admin Controls & Evaluator Simulator */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Manual Control Panel (Section 14.4) */}
          <div className="lg:col-span-5 flex">
            <ManualControls
              status={status}
              onManualGreen={executeManualGreen}
              onReturnToAutomatic={executeReturnToAutomatic}
              actionInProgress={actionInProgress}
            />
          </div>

          {/* Test & Simulation Suite (Section 14.8) */}
          <div className="lg:col-span-7 flex">
            <SimulationPanel
              onSimulateVehicleArrival={simulateVehicleArrival}
              onSimulateVehicleClearance={simulateVehicleClearance}
              onSimulateControllerAck={simulateControllerAck}
              onSimulateControllerStatus={simulateControllerStatus}
              actionInProgress={actionInProgress}
            />
          </div>
        </div>

        {/* 6. Bottom Full Width: Chronological Audit Activity Log (Section 14.7) */}
        <div className="w-full">
          <AuditActivityLog logs={history} />
        </div>
      </div>
    </main>
  );
}