# Factory Traffic Management System - Frontend Dashboard

A real-time, interactive operator dashboard for the Factory Traffic Management System. Built with **Next.js (App Router)**, **TypeScript**, and **Tailwind CSS**, this frontend provides complete visibility and control over 4-way industrial intersections.

---

## ✨ Key Features (Section 14 Compliant)

* **Real-Time Telemetry (1.0s Polling):** Continuously synchronizes state with the backend engine without manual page refreshes.
* **Visual Intersection Canvas:** Displays live traffic light states (Red, Yellow, Green) for NORTH, SOUTH, EAST, and WEST approaches.
* **Live Queue Metrics:** Shows real-time vehicle counts and congestion density for all four lanes.
* **Manual Override Controls:** Allows administrators to lock the junction into manual mode, dispatch specific `GREEN` signals, and return to automatic scheduling safely.
* **Evaluator Simulation Suite:** A built-in testing panel to simulate IoT edge events without physical hardware:
  * Ingest vehicle arrivals (`TRUCK`, `EMERGENCY`, etc.) and clearances.
  * Simulate hardware controller ACKs, fail-safe timeouts, and offline statuses.
* **Chronological Audit Trail:** A scrollable, filterable ledger showing signal transitions, emergency preemptions, and hardware failures.
* **Divergence Alerts:** Dynamic UI warnings if the physical signal state diverges from the backend's desired state, or if the backend goes offline.

---

## 🛠 Tech Stack

* **Framework:** Next.js (App Router)
* **Language:** TypeScript
* **Styling:** Tailwind CSS
* **Icons:** Lucide React
* **Data Fetching:** Native `fetch` with custom React Hooks

---

## 🚀 Setup & Installation

### 1. Prerequisites
Ensure you have the following installed on your machine:
* Node.js (v18 or v20+)
* npm (or yarn / pnpm)

### 2. Clone & Navigate
If you haven't already, clone the repository and navigate to the frontend directory:
```bash
git clone <repository-url>
cd factory_traffic_system/frontend