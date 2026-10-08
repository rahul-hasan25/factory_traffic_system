import axios, { AxiosError, AxiosInstance } from "axios";
import {
  AuditLog,
  CommandApiResponse,
  ControllerApiResponse,
  ControllerEventPayload,
  Direction,
  JunctionCommandPayload,
  JunctionEntity,
  JunctionStatus,
  SensorApiResponse,
  SensorEventPayload,
} from "@/types/traffic";

// Base API URL injected from environment or defaults to local Django server
const BASE_URL: string =
  process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://127.0.0.1:8000/api";

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 8000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Standardized error extractor to prevent UI crashes 
export function parseApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<any>;
    if (axiosErr.response) {
      const data = axiosErr.response.data;
      if (typeof data === "string") return data;
      if (data?.message) return data.message;
      if (data?.error) return data.error;
      if (data?.errors) {
        return Object.entries(data.errors)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(", ") : val}`)
          .join(" | ");
      }
      return `Server error (${axiosErr.response.status})`;
    } else if (axiosErr.request) {
      return "Backend server is unavailable or offline (Check Django connection).";
    }
  }
  return error instanceof Error ? error.message : "An unexpected network error occurred.";
}

export const TrafficAPI = {
  // GET /api/junctions
  getJunctions: async (): Promise<JunctionEntity[]> => {
    try {
      const response = await apiClient.get<JunctionEntity[]>("/junctions");
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  // GET /api/junctions/:id
  getJunctionDetail: async (junctionId: string): Promise<JunctionEntity> => {
    try {
      const cleanId = junctionId.trim().toUpperCase();
      const response = await apiClient.get<JunctionEntity>(`/junctions/${cleanId}`);
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  // GET /api/junctions/:id/status (Primary Polling Endpoint)
  getJunctionStatus: async (junctionId: string = "A"): Promise<JunctionStatus> => {
    try {
      const cleanId = junctionId.trim().toUpperCase();
      const response = await apiClient.get<JunctionStatus>(`/junctions/${cleanId}/status`);
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  //  POST /api/junctions/:id/commands (Manual Controls)
  sendCommand: async (
    junctionId: string,
    payload: JunctionCommandPayload
  ): Promise<CommandApiResponse> => {
    try {
      const cleanId = junctionId.trim().toUpperCase();
      const response = await apiClient.post<CommandApiResponse>(
        `/junctions/${cleanId}/commands`,
        payload
      );
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  requestManualGreen: async (
    junctionId: string,
    direction: Direction
  ): Promise<CommandApiResponse> => {
    return TrafficAPI.sendCommand(junctionId, {
      command: "MANUAL_GREEN_REQUEST",
      direction,
    });
  },

  returnToAutomatic: async (junctionId: string): Promise<CommandApiResponse> => {
    return TrafficAPI.sendCommand(junctionId, {
      command: "RETURN_TO_AUTOMATIC",
    });
  },

  //POST /api/sensor-events (Vehicle Arrival/Clearance Ingestion)
  submitSensorEvent: async (
    payload: SensorEventPayload
  ): Promise<SensorApiResponse> => {
    try {
      const response = await apiClient.post<SensorApiResponse>(
        "/sensor-events",
        payload
      );
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  //POST /api/controller-events (Hardware ACK / Failure Simulator)
  submitControllerEvent: async (
    payload: ControllerEventPayload
  ): Promise<ControllerApiResponse> => {
    try {
      const response = await apiClient.post<ControllerApiResponse>(
        "/controller-events",
        payload
      );
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },

  // GET /api/junctions/:id/history (Chronological Audit Logs)
  getJunctionHistory: async (
    junctionId: string = "A",
    limit: number = 50,
    eventType?: string
  ): Promise<AuditLog[]> => {
    try {
      const cleanId = junctionId.trim().toUpperCase();
      const params: Record<string, any> = { limit };
      if (eventType) {
        params.event_type = eventType;
      }
      const response = await apiClient.get<AuditLog[]>(
        `/junctions/${cleanId}/history`,
        { params }
      );
      return response.data;
    } catch (error) {
      throw new Error(parseApiError(error));
    }
  },
};