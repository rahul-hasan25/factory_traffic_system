"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  CheckCircle2,
  Clock,
  Filter,
  Flame,
  Radio,
  Sliders,
  Terminal,
} from "lucide-react";
import { AuditEventType, AuditLog } from "@/types/traffic";

interface AuditActivityLogProps {
  logs: AuditLog[];
}

export const AuditActivityLog: React.FC<AuditActivityLogProps> = ({ logs }) => {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");

  // Filter categorization logic
  const filteredLogs = logs.filter((log) => {
    if (selectedFilter === "ALL") return true;
    if (selectedFilter === "SIGNALS")
      return log.event_type.startsWith("SIGNAL_");
    if (selectedFilter === "EMERGENCY")
      return log.event_type.startsWith("EMERGENCY_");
    if (selectedFilter === "CONTROLLER")
      return (
        log.event_type.startsWith("CONTROLLER_") ||
        log.event_type.startsWith("DEVICE_")
      );
    if (selectedFilter === "SENSORS")
      return (
        log.event_type.startsWith("VEHICLE_") ||
        log.event_type.startsWith("SENSOR_")
      );
    return true;
  });

  // Event category visual styling
  const getEventBadge = (eventType: AuditEventType) => {
    if (eventType.startsWith("EMERGENCY_")) {
      return {
        icon: <Flame className="w-3.5 h-3.5 text-rose-400" />,
        classes: "bg-rose-950/70 text-rose-300 border-rose-700/60",
      };
    }
    if (eventType.startsWith("SIGNAL_")) {
      return {
        icon: <Activity className="w-3.5 h-3.5 text-emerald-400" />,
        classes: "bg-emerald-950/70 text-emerald-300 border-emerald-700/60",
      };
    }
    if (
      eventType.startsWith("CONTROLLER_") ||
      eventType.startsWith("DEVICE_")
    ) {
      return {
        icon: <Radio className="w-3.5 h-3.5 text-amber-400" />,
        classes: "bg-amber-950/70 text-amber-300 border-amber-700/60",
      };
    }
    if (eventType === "MANUAL_OVERRIDE" || eventType === "RETURN_TO_AUTOMATIC") {
      return {
        icon: <Sliders className="w-3.5 h-3.5 text-sky-400" />,
        classes: "bg-sky-950/70 text-sky-300 border-sky-700/60",
      };
    }
    return {
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-slate-400" />,
      classes: "bg-slate-800 text-slate-300 border-slate-700",
    };
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-950/80 border border-indigo-700/50 rounded-lg text-indigo-400">
            <Terminal className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Audit & System History Trail (Section 14.7)
            </h2>
            <p className="text-xs text-slate-500 font-mono">
              Chronological immutable event ledger explaining system state
            </p>
          </div>
        </div>

        {/* Filter Selection Pill Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          <Filter className="w-3.5 h-3.5 text-slate-500 mr-1 flex-shrink-0" />
          {["ALL", "SIGNALS", "EMERGENCY", "CONTROLLER", "SENSORS"].map(
            (category) => (
              <button
                key={category}
                onClick={() => setSelectedFilter(category)}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg border transition-all ${
                  selectedFilter === category
                    ? "bg-indigo-950/80 border-indigo-500 text-indigo-300 font-bold"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                {category}
              </button>
            )
          )}
        </div>
      </div>

      {/* Activity Table & Log Stream */}
      <div className="mt-3.5 overflow-x-auto max-h-[360px] overflow-y-auto pr-1">
        {filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-xs font-mono text-slate-500">
            No audit records found matching selected filter.
          </div>
        ) : (
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                <th className="py-2.5 px-3">TIMESTAMP</th>
                <th className="py-2.5 px-3">EVENT CLASSIFICATION</th>
                <th className="py-2.5 px-3">LANE</th>
                <th className="py-2.5 px-3">STATE CHANGE</th>
                <th className="py-2.5 px-3">CORRELATED CMD</th>
                <th className="py-2.5 px-3">DETAILS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredLogs.map((log) => {
                const badge = getEventBadge(log.event_type);
                const timeString = new Date(log.timestamp).toLocaleTimeString();

                return (
                  <tr
                    key={log.id}
                    className="hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Timestamp */}
                    <td className="py-2.5 px-3 whitespace-nowrap text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3 text-slate-500" />
                        <span>{timeString}</span>
                      </div>
                    </td>

                    {/* Event Type Badge */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-semibold ${badge.classes}`}
                      >
                        {badge.icon}
                        <span>{log.event_type}</span>
                      </span>
                    </td>

                    {/* Direction Lane */}
                    <td className="py-2.5 px-3 text-slate-300 font-bold">
                      {log.direction || "ALL"}
                    </td>

                    {/* State Change Transition (previous -> new) */}
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      {log.previous_state || log.new_state ? (
                        <div className="flex items-center gap-1.5 text-[11px]">
                          <span className="text-slate-400">
                            {log.previous_state || "INIT"}
                          </span>
                          <ArrowRight className="w-3 h-3 text-slate-500" />
                          <span className="text-emerald-400 font-bold">
                            {log.new_state}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Correlated Command ID */}
                    <td className="py-2.5 px-3 whitespace-nowrap text-slate-400">
                      {log.command_id ? (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-indigo-300">
                          {log.command_id}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>

                    {/* Additional Metadata / Details */}
                    <td className="py-2.5 px-3 text-slate-400 max-w-[240px] truncate">
                      {log.details && Object.keys(log.details).length > 0 ? (
                        <span
                          className="text-[11px] text-slate-400"
                          title={JSON.stringify(log.details)}
                        >
                          {JSON.stringify(log.details)}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Footer Info */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-500">
        <span>Displaying latest {filteredLogs.length} events</span>
        <span>Polling rate: 1.0s (Live sync)</span>
      </div>
    </div>
  );
};