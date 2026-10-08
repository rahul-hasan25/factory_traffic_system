# Factory Traffic Management System

A robust, full-stack IoT edge traffic management system engineered to control 4-way industrial intersections. Built with a decoupled **Hexagonal (Ports & Adapters)** architecture, featuring a **Django** backend engine and a real-time **Next.js** operator dashboard.

---

## Assumptions / Questions / Requirement Issues

During development, several scenarios were identified as unclear, unsafe, or technically problematic. The following engineering decisions were made to resolve them safely:

*   **Unsafe / Missing (Sensor Failure Lockout):** If an emergency vehicle triggers preemption but its `VEHICLE_CLEARED` event is lost due to sensor failure, the junction could remain locked in `EMERGENCY` mode indefinitely.
    *   *Decision:* Implemented a maximum stale timeout (180s). If an emergency vehicle doesn't clear within this window, the system safely restores `AUTOMATIC` scheduling.
*   **Contradictory (Manual Override vs. Emergency):** The specification allows administrators to lock the junction (`MANUAL`), but also requires emergency vehicles to perform safe transitions.
    *   *Decision:* Life safety takes absolute precedence. An incoming `EMERGENCY` vehicle will automatically preempt an active `MANUAL` override and take control of the junction.
*   **Technically Problematic (Race Conditions & Concurrency):** High-frequency, simultaneous IoT events (e.g., arrival, manual override, and clearance at the exact same millisecond) could corrupt the finite state machine.
    *   *Decision:* Enforced pessimistic row-level locking (`select_for_update()`) combined with atomic database transactions. The system serializes all concurrent requests, ensuring safety invariants are never breached.
*   **Unclear (Clearance of Empty Queue):** Receiving a `VEHICLE_CLEARED` event without a preceding `VEHICLE_ARRIVED` event, or when the queue is already empty.
    *   *Decision:* The event is safely dropped and logged as rejected. The system strictly enforces a `queue >= 0` invariant to prevent negative vehicle counts.
*   **Dependent on a Business Decision (Traffic Priority):** The specification states that `TRUCK` and `FORKLIFT` affect scheduling compared to ordinary traffic, but doesn't define the mathematical ratio.
    *   *Decision:* Implemented a weight-based multiplier in the `TrafficScheduler` (e.g., Truck = 2x, Employee = 1x). The scheduler aggregates lane weights rather than simple vehicle counts to determine the next phase.
*   **Technically Problematic (Hardware Divergence):** The physical controller may fail to execute a backend command, leading to a mismatch between `desired_signals` and `actual_signals`.
    *   *Decision:* The backend awaits a hardware `ACK` for 5.0 seconds. If it times out or receives a `FAILED` status, the backend immediately transitions the junction to a safe `DEGRADED` (ALL_RED) mode and alerts the frontend.

---

## Traffic-Control Algorithm & State Transitions

### The Algorithm
The core scheduling relies on a **Weight-Based Priority Queue**. Vehicles are assigned weights based on classification (`TRUCK` > `EMPLOYEE_VEHICLE`). The `TrafficScheduler` evaluates the aggregate weight of waiting vehicles on opposing approaches. If the active phase reaches its maximum dynamic green time, or if the opposing lane crosses a starvation threshold, a transition is scheduled. Emergency vehicles bypass weight calculations and trigger immediate preemption.

### State Transitions (FSM)
State transitions are governed by a deterministic Finite State Machine (FSM) to prevent conflicting greens:
1.  **`STABLE_GREEN`**: Normal traffic flow for the active approach.
2.  **`CLEARING_YELLOW`**: Initiated when a phase swap is triggered (fixed 3.0s duration).
3.  **`ALL_RED_CLEARANCE`**: A mandatory safety buffer (fixed 2.0s duration) ensuring the physical intersection is completely empty.
4.  **Phase Swap**: The target phase enters `STABLE_GREEN`.

---

## Setup & Installation

### Prerequisites
*   Python 3.11+
*   Node.js v18+ (and npm)
*   PostgreSQL or SQLite3 (default)

### 1. Backend Setup (Django)
Open a terminal and navigate to the `backend` directory:
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Run migrations and seed default Junction 'A'
python manage.py makemigrations traffic_control
python manage.py migrate
python manage.py shell -c "from apps.traffic_control.models import Junction; Junction.objects.get_or_create(junction_id='A')"