"use client";

import React, { useState } from "react";
import {
  CheckCircle,
  Flame,
  Forklift,
  Loader2,
  MinusCircle,
  PlusCircle,
  Send,
  Truck,
  Wifi,
  WifiOff,
  Wrench,
  XCircle,
} from "lucide-react";
import { Direction, VehicleType } from "@/types/traffic";

interface SimulationPanelProps {
  onSimulateVehicleArrival: (
    direction: Direction,
    vehicleType: VehicleType
  ) => Promise<void>;
  onSimulateVehicleClearance: (direction: Direction) => Promise<void>;
  onSimulateControllerAck: (status: "ACK" | "FAILED") => Promise<void>;
  onSimulateControllerStatus: (status: "OFFLINE" | "ONLINE") => Promise<void>;
  actionInProgress: string | null;
}

export const SimulationPanel: React.FC<SimulationPanelProps> = ({
  onSimulateVehicleArrival,
  onSimulateVehicleClearance,
  onSimulateControllerAck,
  onSimulateControllerStatus,
  actionInProgress,
}) => {
  const [selectedDirection, setSelectedDirection] = useState<Direction>("NORTH");
  const [selectedVehicleType, setSelectedVehicleType] = useState<VehicleType>("TRUCK");

  const directions: Direction[] = ["NORTH", "SOUTH", "EAST", "WEST"];

  const vehicleTypes: Array<{ type: VehicleType; label: string; icon: React.ReactNode }> = [
    { type: "TRUCK", label: "Truck", icon: <Truck className="w-3.5 h-3.5" /> },
    { type: "FORKLIFT", label: "Forklift", icon: <Forklift className="w-3.5 h-3.5" /> },
    { type: "EMPLOYEE_VEHICLE", label: "Staff Car", icon: <Truck className="w-3.5 h-3.5" /> },
    { type: "EMERGENCY", label: "Emergency", icon: <Flame className="w-3.5 h-3.5 text-rose-400" /> },
  ];

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-950/80 border border-emerald-700/50 rounded-lg text-emerald-400">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Hardware & Traffic Simulator (Section 14.8)
            </h2>
            <p className="text-xs text-slate-500 font-mono">
              Evaluator testing suite: simulate IoT events without physical hardware
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
        {/* Left Side: Sensor Ingestion (Vehicle Arrival & Clearance) */}
        <div className="p-3.5 bg-slate-950/80 border border-slate-800/80 rounded-xl flex flex-col justify-between">
          <div>
            <span className="text-xs font-mono font-semibold text-slate-300 block mb-2">
              1. SENSOR TELEMETRY SIMULATOR
            </span>

            {/* Direction Selector */}
            <label className="text-[11px] font-mono text-slate-400 block mb-1">
              Target Direction Lane:
            </label>
            <div className="grid grid-cols-4 gap-1.5 mb-3">
              {directions.map((dir) => (
                <button
                  key={dir}
                  type="button"
                  onClick={() => setSelectedDirection(dir)}
                  className={`py-1.5 text-xs font-mono rounded-lg border transition-all ${
                    selectedDirection === dir
                      ? "bg-indigo-950/80 border-indigo-500 text-indigo-300 font-bold"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {dir}
                </button>
              ))}
            </div>

            {/* Vehicle Type Selector */}
            <label className="text-[11px] font-mono text-slate-400 block mb-1">
              Vehicle Classification:
            </label>
            <div className="grid grid-cols-2 gap-1.5 mb-3">
              {vehicleTypes.map(({ type, label, icon }) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedVehicleType(type)}
                  className={`flex items-center justify-center gap-1.5 py-1.5 px-2 text-xs font-mono rounded-lg border transition-all ${
                    selectedVehicleType === type
                      ? type === "EMERGENCY"
                        ? "bg-rose-950/80 border-rose-500 text-rose-300 font-bold"
                        : "bg-indigo-950/80 border-indigo-500 text-indigo-300 font-bold"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {icon}
                  <span>{label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Action Triggers: Arrival & Clearance */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
            <button
              onClick={() => onSimulateVehicleArrival(selectedDirection, selectedVehicleType)}
              disabled={Boolean(actionInProgress)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-emerald-950/70 hover:bg-emerald-900 border border-emerald-600/60 text-emerald-300 text-xs font-mono font-semibold transition-all disabled:opacity-50"
            >
              {actionInProgress === `vehicle-${selectedDirection}` ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <PlusCircle className="w-3.5 h-3.5" />
              )}
              <span>ARRIVE (+1)</span>
            </button>

            <button
              onClick={() => onSimulateVehicleClearance(selectedDirection)}
              disabled={Boolean(actionInProgress)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-mono font-semibold transition-all disabled:opacity-50"
            >
              {actionInProgress === `clear-${selectedDirection}` ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <MinusCircle className="w-3.5 h-3.5" />
              )}
              <span>CLEAR (-1)</span>
            </button>
          </div>
        </div>

        {/* Right Side: IoT Controller Hardware Telemetry & ACKs */}
        <div className="p-3.5 bg-slate-950/80 border border-slate-800/80 rounded-xl flex flex-col justify-between">
          <div>
            <span className="text-xs font-mono font-semibold text-slate-300 block mb-2">
              2. PHYSICAL CONTROLLER ACK & FAILURE SIMULATOR
            </span>
            <p className="text-[11px] text-slate-400 font-mono mb-3 leading-relaxed">
              Test hardware correlation: dispatch confirmed signals or trigger fail-safe timeouts.
            </p>

            {/* ACK & Failure Commands */}
            <div className="flex flex-col gap-2 mb-3">
              <button
                onClick={() => onSimulateControllerAck("ACK")}
                disabled={Boolean(actionInProgress)}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-mono text-slate-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                  <span>Confirm Pending Command (ACK)</span>
                </div>
                <span className="text-[10px] text-emerald-400 font-bold">200 OK</span>
              </button>

              <button
                onClick={() => onSimulateControllerAck("FAILED")}
                disabled={Boolean(actionInProgress)}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-xs font-mono text-slate-200 transition-all disabled:opacity-50"
              >
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-rose-400" />
                  <span>Reject Command Execution (FAILED)</span>
                </div>
                <span className="text-[10px] text-rose-400 font-bold">FAIL-SAFE</span>
              </button>
            </div>
          </div>

          {/* Controller Online/Offline Toggle */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
            <button
              onClick={() => onSimulateControllerStatus("ONLINE")}
              disabled={Boolean(actionInProgress)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-emerald-400 text-xs font-mono font-semibold transition-all disabled:opacity-50"
            >
              <Wifi className="w-3.5 h-3.5" />
              <span>LINK ONLINE</span>
            </button>

            <button
              onClick={() => onSimulateControllerStatus("OFFLINE")}
              disabled={Boolean(actionInProgress)}
              className="flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-rose-950/60 hover:bg-rose-900/60 border border-rose-700/60 text-rose-300 text-xs font-mono font-semibold transition-all disabled:opacity-50"
            >
              <WifiOff className="w-3.5 h-3.5" />
              <span>LINK OFFLINE</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};