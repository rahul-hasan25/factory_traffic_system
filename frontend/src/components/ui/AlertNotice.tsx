"use client";

import React from "react";
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from "lucide-react";
import { ActiveAlert } from "@/types/traffic";

interface AlertNoticeProps {
  alert: ActiveAlert;
  onDismiss?: (id: string) => void;
}

export const AlertNotice: React.FC<AlertNoticeProps> = ({ alert, onDismiss }) => {
  // Severity-based visual styling
  const severityStyles = {
    CRITICAL: {
      container: "bg-rose-950/40 border-rose-600/60 text-rose-200",
      icon: <AlertCircle className="w-5 h-5 text-rose-500 animate-pulse flex-shrink-0" />,
      badge: "bg-rose-900/60 text-rose-300 border-rose-700/50",
    },
    WARNING: {
      container: "bg-amber-950/40 border-amber-600/60 text-amber-200",
      icon: <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />,
      badge: "bg-amber-900/60 text-amber-300 border-amber-700/50",
    },
    INFO: {
      container: "bg-sky-950/40 border-sky-600/60 text-sky-200",
      icon: <Info className="w-5 h-5 text-sky-400 flex-shrink-0" />,
      badge: "bg-sky-900/60 text-sky-300 border-sky-700/50",
    },
  }[alert.severity];

  return (
    <div
      className={`relative flex items-start justify-between p-3.5 mb-2.5 rounded-xl border backdrop-blur-md shadow-lg transition-all duration-200 ${severityStyles.container}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        {/* Severity Icon */}
        <div className="mt-0.5">{severityStyles.icon}</div>

        {/* Content Body */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold tracking-wide text-white">
              {alert.title}
            </span>
            <span
              className={`text-[10px] uppercase font-mono font-bold px-1.5 py-0.5 rounded border ${severityStyles.badge}`}
            >
              {alert.severity}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-slate-300/90 leading-relaxed">
            {alert.description}
          </p>
          <span className="mt-1 text-[10px] font-mono text-slate-400">
            {new Date(alert.timestamp).toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Optional Dismiss Button */}
      {onDismiss && (
        <button
          onClick={() => onDismiss(alert.id)}
          className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};