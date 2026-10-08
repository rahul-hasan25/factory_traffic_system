# Final Submission Documentation

## 6. Traffic-Control Algorithm
The core traffic scheduling algorithm relies on a **Weight-Based Priority Queue**. 
- Vehicles are assigned weights based on their classification (e.g., `EMERGENCY` = Absolute Priority, `TRUCK`/`FORKLIFT` = High Weight, `EMPLOYEE_VEHICLE` = Standard Weight).
- The `TrafficScheduler` aggregates the total weight of waiting vehicles for each approach (NORTH_SOUTH vs EAST_WEST). 
- If the current phase reaches its maximum dynamic green time, or if an opposing lane accumulates a significantly higher priority threshold, the algorithm signals a phase transition. Emergency vehicles bypass the weight calculation and trigger immediate safe preemption.

## 7. Traffic-State Transitions
State transitions are strictly governed by a deterministic Finite State Machine (FSM) to ensure safety invariants:
1. **`STABLE_GREEN`**: Normal traffic flow for the active phase.
2. **`CLEARING_YELLOW`**: Initiated when a phase change is triggered. Lasts for a fixed 3.0 seconds to warn drivers.
3. **`ALL_RED_CLEARANCE`**: A mandatory 2.0-second safety buffer where all directions are `RED` to ensure the intersection is physically clear.
4. **Phase Swap**: Following clearance, the new target phase enters `STABLE_GREEN`. 
Direct jumping from `GREEN` to opposing `GREEN` is mathematically impossible in the FSM.

## 10. Assumptions / Questions / Requirement Issues
- **Assumption 1 (Conflicting Movements):** Assumed NORTH/SOUTH operate concurrently, and EAST/WEST operate concurrently. They are strictly mutually exclusive.
- **Assumption 2 (Event Idempotency):** Assumed the `event_id` in the sensor payload is globally unique and authoritative. Duplicates are logged but do not mutate the database queue.
- **Assumption 3 (Queue Integrity):** A `VEHICLE_CLEARED` event for an empty queue safely resolves to `queue = 0` rather than allowing negative queue counts.
- **Assumption 4 (Manual Override):** Assumed human operators might forget to release manual mode; thus, a 120-second inactivity timeout automatically restores `AUTOMATIC` scheduling.
- **Assumption 5 (Hardware Failures):** Assumed the controller must ACK within 5.0 seconds. Failure degrades the junction to a safe `ALL_RED` state.

## 11. Major Architectural Decisions
- **Hexagonal Architecture (Ports & Adapters):** Decoupled the pure traffic domain logic (`apps/traffic_control/domain`) from the Django framework. The FSM and Scheduler have no dependencies on HTTP requests, ORM models, or MQTT.
- **Database Concurrency Limits:** Implemented pessimistic row-level locking (`select_for_update()`) inside atomic transactions to prevent race conditions during simultaneous vehicle arrivals and admin overrides.
- **Event-Driven Hardware Gateway:** Controller commands are dispatched through a decoupled `ControllerPort` interface, allowing easy replacement with real MQTT clients in the future.

## 12. AI / Tool Usage
- **AI Assistant:** Used Google Gemini to assist with generating boilerplate Django configuration, structuring the Next.js/Tailwind UI components, and scaffolding the hexagonal architecture.
- **Usage Context:** AI was primarily used to accelerate repetitive typing, generate React functional components from design requirements, and format the documentation.
- **Verification:** All generated architectural decisions, concurrency locks, and state-machine transitions were manually reviewed, verified, and thoroughly debugged to ensure compliance with the core safety invariants.