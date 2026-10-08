// 1. Primary Direction & Traffic Phase Topologies
export type Direction = "NORTH" | "SOUTH" | "EAST" | "WEST";

export type TrafficPhase = "NORTH_SOUTH" | "EAST_WEST" | "ALL_RED";

// 2. Physical Signal Colors & Micro-Transition Steps
export type SignalColor = "RED" | "YELLOW" | "GREEN";

export type TransitionStep =
  | "STABLE_GREEN"
  | "CLEARING_YELLOW"
  | "ALL_RED_CLEARANCE";

// 3. Junction Operating Modes
export type JunctionMode = "AUTOMATIC" | "MANUAL" | "EMERGENCY" | "DEGRADED";

// 4. Controller Connectivity & Telemetry Status 
export type ControllerStatus = "ONLINE" | "OFFLINE" | "DEGRADED" | "WARNING" | "UNKNOWN";

// 5. Factory Vehicle Classifications & Priority Hierarchy 
export type VehicleType =
  | "EMERGENCY"
  | "TRUCK"
  | "FORKLIFT"
  | "EMPLOYEE_VEHICLE";

// 6. Sensor Event Classifications 
export type SensorEventType = "VEHICLE_ARRIVED" | "VEHICLE_CLEARED";

// 7. Core Junction Status Payload 
export interface JunctionStatus {
  junction_id: string;
  mode: JunctionMode;
  phase: string;
  controller_status: ControllerStatus;
  desired_signals: Record<Direction, SignalColor>;
  actual_signals: Record<Direction, SignalColor>;
  queues: Record<Direction, number>;
  has_signal_mismatch: boolean;
  active_emergencies_count: number;
  emergency_direction?: Direction | null;
  manual_direction?: Direction | null;
  last_updated?: string;
}

// 8. Junction Core Entity 
export interface JunctionEntity {
  junction_id: string;
  name: string;
  mode: JunctionMode;
  current_phase: TrafficPhase;
  transition_step: TransitionStep;
  controller_status: ControllerStatus;
  desired_signals: Record<Direction, SignalColor>;
  actual_signals: Record<Direction, SignalColor>;
  has_signal_mismatch: boolean;
  active_emergencies_count: number;
  created_at: string;
  updated_at: string;
}

// 9. Manual Control Request Command Payloads 
export type ManualCommandType = "MANUAL_GREEN_REQUEST" | "RETURN_TO_AUTOMATIC";

export interface ManualGreenRequestPayload {
  command: "MANUAL_GREEN_REQUEST";
  direction: Direction;
}

export interface ReturnToAutomaticPayload {
  command: "RETURN_TO_AUTOMATIC";
}

export type JunctionCommandPayload =
  | ManualGreenRequestPayload
  | ReturnToAutomaticPayload;

export interface CommandApiResponse {
  status: "ACCEPTED" | "REJECTED";
  command_id?: string;
  junction_id?: string;
  mode?: JunctionMode;
  transition_step?: TransitionStep;
  desired_signals?: Record<Direction, SignalColor>;
  message?: string;
  errors?: Record<string, string[]>;
}

// 10. IoT Sensor Event Payload 
export interface SensorEventPayload {
  event_id: string;
  junction_id: string;
  direction: Direction;
  event_type: SensorEventType;
  vehicle_id: string;
  vehicle_type?: VehicleType;
  sequence_no?: number;
  timestamp: string;
}

export interface SensorApiResponse {
  status: "PROCESSED" | "IGNORED" | "REJECTED";
  event_id?: string;
  action?: string;
  queue_length?: number;
  message?: string;
  errors?: Record<string, string[]>;
}

// 11. Controller Feedback & ACK Simulator Payload 
export type ControllerAckStatus = "ACK" | "FAILED" | "OFFLINE" | "ONLINE";

export interface ControllerEventPayload {
  command_id?: string;
  junction_id: string;
  status: ControllerAckStatus;
  actual_state?: SignalColor;
  device_type?: "SIGNAL_CONTROLLER" | "SENSOR";
  direction?: Direction;
  timestamp?: string;
}

export interface ControllerApiResponse {
  status: "PROCESSED" | "IGNORED" | "REJECTED";
  command_id?: string;
  actual_signals?: Record<Direction, SignalColor>;
  message?: string;
  errors?: Record<string, string[]>;
}

// 12. Audit History & System Logs 
export type AuditEventType =
  | "VEHICLE_DETECTED"
  | "VEHICLE_CLEARED"
  | "SENSOR_EVENT_DUPLICATE"
  | "SENSOR_EVENT_REJECTED"
  | "SIGNAL_TRANSITION_STARTED"
  | "SIGNAL_STATE_REQUESTED"
  | "SIGNAL_STATE_CONFIRMED"
  | "SIGNAL_CHANGED"
  | "EMERGENCY_DETECTED"
  | "EMERGENCY_CLEARED"
  | "MANUAL_OVERRIDE"
  | "RETURN_TO_AUTOMATIC"
  | "MODE_CHANGED"
  | "CONTROLLER_ACKNOWLEDGED"
  | "CONTROLLER_TIMEOUT"
  | "DEVICE_FAILURE"
  | "DEVICE_RECONNECTED";

export interface AuditLog {
  id: number;
  junction_id: string;
  event_type: AuditEventType;
  direction?: Direction | "ALL" | null;
  previous_state?: string | null;
  new_state?: string | null;
  command_id?: string | null;
  details: Record<string, any>;
  timestamp: string;
}

// 13. UI Specific Alert State 
export interface ActiveAlert {
  id: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  title: string;
  description: string;
  timestamp: Date;
}