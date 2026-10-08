# Section 17: Architectural Decisions & Domain Assumptions

This document outlines the engineering assumptions, fail-safe mechanisms, and trade-offs adopted to resolve intentionally ambiguous specifications in the Factory Traffic Management System.

---

### 1. Traffic Movement Conflicts & Safety Invariants
* **Decision:** `NORTH_SOUTH` and `EAST_WEST` movements are strictly conflicting.
* **Safety Invariant:** Under no condition are opposing directions granted a simultaneous `GREEN` light. When transitioning between phases, the system enforces a non-negotiable intermediate sequence: `CLEARING_YELLOW` (3s) followed by `ALL_RED_CLEARANCE` (2s).

### 2. Sensor Telemetry & Event Ordering
* **Authoritative Identification:** The incoming `event_id` is globally authoritative for idempotency. Any payload matching an existing `event_id` is treated as a duplicate (`status: IGNORED`), logged to audit history, and does not alter queue states.
* **Out-of-Order / Missing Arrivals:** If a `VEHICLE_CLEARED` event arrives without a recorded arrival or when the queue is empty, the system drops the event safely, preserving the invariant that `queue >= 0`.
* **Authoritative Timestamp:** The server's UTC time serves as the primary ground truth for scheduler wait times, while sensor timestamps are retained for audit and telemetry reconciliation.

### 3. Emergency Preemption & Conflict Resolution
* **Priority Hierarchy:** `EMERGENCY` strictly preempts both `AUTOMATIC` scheduling and `MANUAL` operator overrides.
* **Conflicting Emergencies:** If emergency vehicles arrive on conflicting approaches simultaneously, the lane with the earliest detected emergency is served first, followed immediately by safe clearance and service for the second approach.
* **Emergency Clearance:** An emergency phase is considered cleared once all detected emergency vehicles dispatch `VEHICLE_CLEARED` events, or after a maximum safety timeout (180s) to guard against broken sensor transmitters.

### 4. Administrative Manual Overrides
* **Inactivity Expiration:** Manual mode expires automatically after 120 seconds of operator inactivity, restoring `AUTOMATIC` scheduling to prevent factory traffic blockages.
* **Simultaneous Admin Requests:** Database transaction locks (`select_for_update()`) serialize concurrent commands; the latest valid administrative intent supersedes preceding requests.

### 5. Physical Controller Telemetry & Fail-Safe Modes
* **Acknowledgement Window:** The backend expects a hardware ACK within 5.0 seconds. If an ACK times out or the controller emits `OFFLINE`, the junction transitions into `DEGRADED` safe mode, forcing all approaches to `ALL_RED`.
* **Duplicate ACKs:** Duplicate controller ACKs are safely ignored without re-triggering signal transitions.
* **Desired vs. Actual Mismatch:** If the physically confirmed signal (`actual_signals`) diverges from the commanded state (`desired_signals`), a high-priority mismatch alert is raised on the operator dashboard.

### 6. Crash Recovery & Server Restarts
* **Startup Crash Recovery:** If the server restarts mid-transition (`CLEARING_YELLOW` or `ALL_RED_CLEARANCE`) or with an unconfirmed physical state, the system rejects stale in-flight commands and initializes into a safe `ALL_RED` clearance state before resuming automatic scheduling.