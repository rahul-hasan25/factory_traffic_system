"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { TrafficAPI, parseApiError } from "@/services/api";
import {
  ActiveAlert,
  AuditLog,
  Direction,
  JunctionStatus,
  SensorEventPayload,
  VehicleType,
} from "@/types/traffic";

interface UseTrafficDashboardOptions {
  junctionId?: string;
  pollingIntervalMs?: number;
  historyLimit?: number;
}

export function useTrafficDashboard({
  junctionId = "A",
  pollingIntervalMs = 1000,
  historyLimit = 30,
}: UseTrafficDashboardOptions = {}) {
  // 1. Core State
  const [status, setStatus] = useState<JunctionStatus | null>(null);
  const [history, setHistory] = useState<AuditLog[]>([]);
  const [alerts, setAlerts] = useState<ActiveAlert[]>([]);

  // 2. Network & Loading States
  const [isInitialLoading, setIsInitialLoading] = useState<boolean>(true);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(true);
  const [lastError, setLastError] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Polling lock to prevent overlapping asynchronous requests
  const isFetchingRef = useRef<boolean>(false);

  // 3. Derived Alert Evaluation Engine
  const deriveAlerts = useCallback((currentStatus: JunctionStatus): ActiveAlert[] => {
    const activeAlerts: ActiveAlert[] = [];

    // Alert: Signal Mismatch (Desired != Actual physical confirmation)
    if (currentStatus.has_signal_mismatch) {
      activeAlerts.push({
        id: "alert-signal-mismatch",
        severity: "CRITICAL",
        title: "Signal State Mismatch",
        description: "Confirmed physical signal state diverged from backend desired state.",
        timestamp: new Date(),
      });
    }

    // Alert: Hardware Connectivity Failures
    if (currentStatus.controller_status === "OFFLINE") {
      activeAlerts.push({
        id: "alert-controller-offline",
        severity: "CRITICAL",
        title: "Controller Offline",
        description: "Physical intersection controller disconnected. Hardware telemetry lost.",
        timestamp: new Date(),
      });
    } else if (currentStatus.controller_status === "DEGRADED") {
      activeAlerts.push({
        id: "alert-controller-degraded",
        severity: "CRITICAL",
        title: "Junction Operating in DEGRADED Mode",
        description: "Fail-safe mode active. Intersection forced to clearance / ALL_RED.",
        timestamp: new Date(),
      });
    }

    // Alert: Active Emergency Preemption 
    if (currentStatus.mode === "EMERGENCY" || currentStatus.active_emergencies_count > 0) {
      activeAlerts.push({
        id: "alert-emergency-active",
        severity: "WARNING",
        title: "Emergency Vehicle Preemption Active",
        description: `Priority vehicle detected on ${currentStatus.emergency_direction || "approach lane"}. Safe clearance sequence running.`,
        timestamp: new Date(),
      });
    }

    // Alert: Manual Mode Override Active
    if (currentStatus.mode === "MANUAL") {
      activeAlerts.push({
        id: "alert-manual-override",
        severity: "INFO",
        title: "Manual Control Active",
        description: `Operator manual green request in effect for ${currentStatus.manual_direction || "selected phase"}.`,
        timestamp: new Date(),
      });
    }

    return activeAlerts;
  }, []);

  // 4. Primary Data Synchronization Routine
  const fetchDashboardData = useCallback(async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;

    try {
      const [fetchedStatus, fetchedHistory] = await Promise.all([
        TrafficAPI.getJunctionStatus(junctionId),
        TrafficAPI.getJunctionHistory(junctionId, historyLimit),
      ]);

      setStatus(fetchedStatus);
      setHistory(fetchedHistory);
      setAlerts(deriveAlerts(fetchedStatus));
      setIsBackendConnected(true);
      setLastError(null);
    } catch (err) {
      const formattedError = parseApiError(err);
      setIsBackendConnected(false);
      setLastError(formattedError);
    } finally {
      setIsInitialLoading(false);
      isFetchingRef.current = false;
    }
  }, [junctionId, historyLimit, deriveAlerts]);

  // 5. Polling Lifecycle 
  useEffect(() => {
    fetchDashboardData();
    const intervalTimer = setInterval(fetchDashboardData, pollingIntervalMs);
    return () => clearInterval(intervalTimer);
  }, [fetchDashboardData, pollingIntervalMs]);

  // 6. User Action Handlers 

  // Manual Green Request 
  const executeManualGreen = async (direction: Direction) => {
    setActionInProgress(`manual-${direction}`);
    try {
      await TrafficAPI.requestManualGreen(junctionId, direction);
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  // Return to Automatic Mode 
  const executeReturnToAutomatic = async () => {
    setActionInProgress("return-auto");
    try {
      await TrafficAPI.returnToAutomatic(junctionId);
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  // Dispatch Sensor Vehicle Ingestion 
  const simulateVehicleArrival = async (
    direction: Direction,
    vehicleType: VehicleType = "TRUCK"
  ) => {
    setActionInProgress(`vehicle-${direction}`);
    const eventPayload: SensorEventPayload = {
      event_id: `evt-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`,
      junction_id: junctionId,
      direction,
      event_type: "VEHICLE_ARRIVED",
      vehicle_id: `VH-${Math.floor(100 + Math.random() * 900)}`,
      vehicle_type: vehicleType,
      timestamp: new Date().toISOString(),
    };

    try {
      await TrafficAPI.submitSensorEvent(eventPayload);
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  // Dispatch Vehicle Clearance 
  const simulateVehicleClearance = async (direction: Direction) => {
    setActionInProgress(`clear-${direction}`);
    const eventPayload: SensorEventPayload = {
      event_id: `evt-clr-${Date.now().toString(36)}`,
      junction_id: junctionId,
      direction,
      event_type: "VEHICLE_CLEARED",
      vehicle_id: "ANY_FRONT_VEHICLE",
      timestamp: new Date().toISOString(),
    };

    try {
      await TrafficAPI.submitSensorEvent(eventPayload);
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  // Simulate Controller Hardware ACK 
  const simulateControllerAck = async (statusOverride: "ACK" | "FAILED" = "ACK") => {
    setActionInProgress(`ack-${statusOverride}`);
    try {
      // Find the most recent command id from audit history if available
      const latestCommandLog = history.find((h) => h.command_id);
      const targetCommandId = latestCommandLog?.command_id || "cmd-simulated";

      await TrafficAPI.submitControllerEvent({
        command_id: targetCommandId,
        junction_id: junctionId,
        status: statusOverride,
        timestamp: new Date().toISOString(),
      });
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  // Simulate Controller Offline / Online Toggle 
  const simulateControllerStatus = async (targetStatus: "OFFLINE" | "ONLINE") => {
    setActionInProgress(`status-${targetStatus}`);
    try {
      await TrafficAPI.submitControllerEvent({
        junction_id: junctionId,
        status: targetStatus,
        device_type: "SIGNAL_CONTROLLER",
        timestamp: new Date().toISOString(),
      });
      await fetchDashboardData();
    } catch (err) {
      setLastError(parseApiError(err));
    } finally {
      setActionInProgress(null);
    }
  };

  return {
    status,
    history,
    alerts,
    isInitialLoading,
    isBackendConnected,
    lastError,
    actionInProgress,
    refreshNow: fetchDashboardData,
    executeManualGreen,
    executeReturnToAutomatic,
    simulateVehicleArrival,
    simulateVehicleClearance,
    simulateControllerAck,
    simulateControllerStatus,
  };
}