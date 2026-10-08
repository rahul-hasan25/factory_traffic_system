from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .safety import (
    DEFAULT_JUNCTION_CONFIG,
    Direction,
    JunctionConfiguration,
    SafetyPolicy,
    TrafficPhase,
)


class VehicleType(str, Enum):
    EMERGENCY = "EMERGENCY"
    TRUCK = "TRUCK"
    FORKLIFT = "FORKLIFT"
    EMPLOYEE_VEHICLE = "EMPLOYEE_VEHICLE"


# Base priority weights as required by specification:
# EMERGENCY > TRUCK > FORKLIFT > EMPLOYEE_VEHICLE
VEHICLE_PRIORITY_WEIGHTS: Dict[VehicleType, float] = {
    VehicleType.EMERGENCY: 1000.0,
    VehicleType.TRUCK: 25.0,
    VehicleType.FORKLIFT: 15.0,
    VehicleType.EMPLOYEE_VEHICLE: 5.0,
}


@dataclass
class WaitingVehicle:
    vehicle_id: str
    vehicle_type: VehicleType
    arrival_time: datetime


@dataclass
class DirectionQueue:
    direction: Direction
    vehicles: List[WaitingVehicle]


class TrafficScheduler:
    """
    Traffic Phase Scheduling Algorithm.
    
    Formula per Direction:
      Score = (Queue Count * QUEUE_WEIGHT)
            + (Sum of Vehicle Priority Weights)
            + (Max Waiting Time in seconds * WAIT_TIME_WEIGHT)
            + Starvation Penalty (if applicable)
    
    Phase Score = Score(Dir_1) + Score(Dir_2)
    """

    QUEUE_WEIGHT: float = 10.0
    WAIT_TIME_WEIGHT: float = 1.5
    STARVATION_THRESHOLD_SECONDS: float = 60.0
    STARVATION_PENALTY: float = 50.0

    @classmethod
    def calculate_direction_score(
        cls, queue: DirectionQueue, now: Optional[datetime] = None
    ) -> float:
        """Calculates scheduling score for a single direction queue."""
        if not queue.vehicles:
            return 0.0

        current_time = now or datetime.now(timezone.utc)
        vehicle_count = len(queue.vehicles)

        total_priority_weight = sum(
            VEHICLE_PRIORITY_WEIGHTS.get(v.vehicle_type, 1.0)
            for v in queue.vehicles
        )

        # Calculate max waiting time (oldest vehicle in queue)
        oldest_arrival = min(v.arrival_time for v in queue.vehicles)
        max_waiting_seconds = max(0.0, (current_time - oldest_arrival).total_seconds())

        # Starvation protection: add aggressive penalty if waiting too long
        starvation_score = 0.0
        if max_waiting_seconds >= cls.STARVATION_THRESHOLD_SECONDS:
            intervals_past = max_waiting_seconds / cls.STARVATION_THRESHOLD_SECONDS
            starvation_score = cls.STARVATION_PENALTY * intervals_past

        score = (
            (vehicle_count * cls.QUEUE_WEIGHT)
            + total_priority_weight
            + (max_waiting_seconds * cls.WAIT_TIME_WEIGHT)
            + starvation_score
        )
        return score

    @classmethod
    def select_next_phase(
        cls,
        queues: Dict[Direction, DirectionQueue],
        current_phase: TrafficPhase,
        now: Optional[datetime] = None,
        config: Optional[JunctionConfiguration] = None,
    ) -> TrafficPhase:
        """
        Evaluates active queues and picks the optimal safe phase.
        Emergency preemption takes immediate precedence.
        When multiple competing emergencies exist, uses a deterministic FIFO resolution.
        Avoids unnecessary switching if no conflicting traffic exists.
        """
        active_config = config or DEFAULT_JUNCTION_CONFIG
        current_time = now or datetime.now(timezone.utc)

        # 1. Competing Emergency Policy: FIFO (Oldest arriving emergency vehicle first)
        active_emergencies: List[Tuple[datetime, Direction]] = []
        for direction, dir_queue in queues.items():
            for v in dir_queue.vehicles:
                if v.vehicle_type == VehicleType.EMERGENCY:
                    active_emergencies.append((v.arrival_time, direction))

        if active_emergencies:
            # Sort chronologically by sensor arrival timestamp
            active_emergencies.sort(key=lambda item: item[0])
            first_emergency_dir = active_emergencies[0][1]
            emergency_target_phase = SafetyPolicy.get_phase_for_direction(
                first_emergency_dir, active_config
            )

            # If current phase already serves this emergency, maintain it
            if current_phase == emergency_target_phase:
                return current_phase
            return emergency_target_phase

        # 2. Phase Scoring Calculation based on injected topology config
        phase_scores: Dict[TrafficPhase, float] = {}

        for phase, directions in active_config.phase_directions.items():
            if phase == TrafficPhase.ALL_RED:
                continue
            score_sum = sum(
                cls.calculate_direction_score(queues.get(d, DirectionQueue(d, [])), current_time)
                for d in directions
            )
            phase_scores[phase] = score_sum

        ns_score = phase_scores.get(TrafficPhase.NORTH_SOUTH, 0.0)
        ew_score = phase_scores.get(TrafficPhase.EAST_WEST, 0.0)

        # 3. Decision & Hysteresis (Avoid unnecessary flipping if both empty)
        if ns_score == 0.0 and ew_score == 0.0:
            return current_phase if current_phase != TrafficPhase.ALL_RED else TrafficPhase.NORTH_SOUTH

        # Tie-breaker: keep current phase unless competing phase has strictly higher demand
        if current_phase == TrafficPhase.NORTH_SOUTH:
            return TrafficPhase.EAST_WEST if ew_score > ns_score else TrafficPhase.NORTH_SOUTH
        elif current_phase == TrafficPhase.EAST_WEST:
            return TrafficPhase.NORTH_SOUTH if ns_score > ew_score else TrafficPhase.EAST_WEST

        # If currently in ALL_RED clearance, choose the one with higher score
        return TrafficPhase.NORTH_SOUTH if ns_score >= ew_score else TrafficPhase.EAST_WEST