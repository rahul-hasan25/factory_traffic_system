# Factory Traffic Management System - Backend Engine

A robust, domain-driven Django backend engineered to control real-time 4-way industrial intersections. Built strictly on **Hexagonal (Ports & Adapters)** architectural principles, this engine isolates core traffic safety rules, priority scheduling, and emergency preemption logic from the HTTP layer and database ORM.

---

## 🏗 Architecture & Core Design

* **Domain-Driven Design:** Traffic safety invariants, phase state machines, and scheduling algorithms reside in pure Python modules (`apps.traffic_control.domain`), completely independent of Django[cite: 3, 5].
* **Decoupled Hardware Communication:** Employs an outbound `ControllerPort` gateway interface to command edge physical controllers independently of database state[cite: 3, 5].
* **Idempotency & Concurrency:** Sensor telemetry ingestion strictly handles duplicate event IDs (`status: IGNORED`)[cite: 4]. All mutating events utilize `transaction.atomic()` and pessimistic row-level locking (`select_for_update()`) to eliminate race conditions[cite: 3, 4, 5].
* **Continuous State Machine:** A standalone background ticker safely manages non-blocking phase transitions (e.g., `STABLE_GREEN` $\rightarrow$ `CLEARING_YELLOW` $\rightarrow$ `ALL_RED_CLEARANCE`).

---

## 🛠 Prerequisites

* **Python:** `3.11+`
* **Database:** PostgreSQL (recommended for production) or SQLite3 (default for local development)

---

## 🚀 Installation & Setup (A to Z)

### 1. Clone & Navigate
```bash
git clone <repository-url>
cd factory_traffic_system/backend