from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Tuple

from .safety import (
    DEFAULT_JUNCTION_CONFIG,
    Direction,
    JunctionConfiguration,
    SafetyPolicy,
    SafetyViolationError,
    SignalColor,
    TrafficPhase,
)


class JunctionMode(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"
    EMERGENCY = "EMERGENCY"
    DEGRADED = "DEGRADED"


class TransitionStep(str, Enum):
    STABLE_GREEN = "STABLE_GREEN"
    CLEARING_YELLOW = "CLEARING_YELLOW"
    ALL_RED_CLEARANCE = "ALL_RED_CLEARANCE"


@dataclass
class JunctionState:
    junction_id: str
    mode: JunctionMode
    current_phase: TrafficPhase
    transition_step: TransitionStep
    signals: Dict[Direction, SignalColor]
    target_phase: Optional[TrafficPhase]
    phase_started_at: datetime
    manual_requested_direction: Optional[Direction] = None
    emergency_direction: Optional[Direction] = None
    config: Optional[JunctionConfiguration] = None


class TrafficStateMachine:
    GREEN_DURATION_SECONDS: float = 30.0
    YELLOW_DURATION_SECONDS: float = 5.0
    ALL_RED_DURATION_SECONDS: float = 2.0

    @classmethod
    def create_initial_state(
        cls,
        junction_id: str,
        now: Optional[datetime] = None,
        config: Optional[JunctionConfiguration] = None,
    ) -> JunctionState:
        """Creates the initial safe fail-over state (ALL_RED)."""
        current_time = now or datetime.now(timezone.utc)
        safe_signals = SafetyPolicy.get_safe_all_red_state(config)
        SafetyPolicy.validate_signal_state(safe_signals, config)

        return JunctionState(
            junction_id=junction_id,
            mode=JunctionMode.AUTOMATIC,
            current_phase=TrafficPhase.ALL_RED,
            transition_step=TransitionStep.ALL_RED_CLEARANCE,
            signals=safe_signals,
            target_phase=TrafficPhase.NORTH_SOUTH,
            phase_started_at=current_time,
            manual_requested_direction=None,
            emergency_direction=None,
            config=config,
        )

    @classmethod
    def _apply_phase_signals(
        cls,
        phase: TrafficPhase,
        color: SignalColor,
        config: Optional[JunctionConfiguration] = None,
    ) -> Dict[Direction, SignalColor]:
        """Generates signal dictionary ensuring conflicting paths remain RED."""
        signals = SafetyPolicy.get_safe_all_red_state(config)
        if phase == TrafficPhase.ALL_RED:
            return signals

        active_config = config or DEFAULT_JUNCTION_CONFIG
        for direction in active_config.phase_directions.get(phase, set()):
            signals[direction] = color
        return signals

    @classmethod
    def trigger_phase_change(
        cls,
        state: JunctionState,
        desired_phase: TrafficPhase,
        now: Optional[datetime] = None,
    ) -> Tuple[JunctionState, bool]:
        """
        Requests transition to a new phase safely.
        Validates transitions to strictly prevent conflicting GREEN activations.
        """
        current_time = now or datetime.now(timezone.utc)

        if state.mode == JunctionMode.DEGRADED:
            raise SafetyViolationError(
                f"Cannot change phase while Junction {state.junction_id} is in DEGRADED mode."
            )

        if state.current_phase == desired_phase and state.transition_step == TransitionStep.STABLE_GREEN:
            return state, False

        # If junction is currently stable GREEN on another phase, begin YELLOW transition
        if state.transition_step == TransitionStep.STABLE_GREEN:
            new_signals = cls._apply_phase_signals(state.current_phase, SignalColor.YELLOW, state.config)
            SafetyPolicy.validate_transition(state.signals, new_signals, state.config)

            state.target_phase = desired_phase
            state.transition_step = TransitionStep.CLEARING_YELLOW
            state.signals = new_signals
            state.phase_started_at = current_time
            return state, True

        # If already transitioning (YELLOW or ALL_RED), queue the target phase safely
        state.target_phase = desired_phase
        return state, False

    @classmethod
    def request_manual(
        cls, state: JunctionState, direction: Direction, now: Optional[datetime] = None
    ) -> JunctionState:
        """Handles manual green request safely through the strict transition sequence."""
        target_phase = SafetyPolicy.get_phase_for_direction(direction, state.config)
        state.mode = JunctionMode.MANUAL
        state.manual_requested_direction = direction
        state, _ = cls.trigger_phase_change(state, target_phase, now=now)
        return state

    @classmethod
    def return_to_automatic(cls, state: JunctionState) -> JunctionState:
        """Returns junction control back to automatic scheduler."""
        state.mode = JunctionMode.AUTOMATIC
        state.manual_requested_direction = None
        return state

    @classmethod
    def request_emergency(
        cls, state: JunctionState, direction: Direction, now: Optional[datetime] = None
    ) -> JunctionState:
        """Handles high-priority emergency preemption safely through yellow/all-red sequence."""
        target_phase = SafetyPolicy.get_phase_for_direction(direction, state.config)
        state.mode = JunctionMode.EMERGENCY
        state.emergency_direction = direction
        state, _ = cls.trigger_phase_change(state, target_phase, now=now)
        return state

    @classmethod
    def clear_emergency(cls, state: JunctionState) -> JunctionState:
        """Clears emergency mode back to automatic operation."""
        state.mode = JunctionMode.AUTOMATIC
        state.emergency_direction = None
        return state

    @classmethod
    def set_degraded(cls, state: JunctionState, now: Optional[datetime] = None) -> JunctionState:
        """Forces fail-safe ALL_RED state upon critical device or controller failure."""
        current_time = now or datetime.now(timezone.utc)
        safe_signals = SafetyPolicy.get_safe_all_red_state(state.config)
        SafetyPolicy.validate_signal_state(safe_signals, state.config)

        state.mode = JunctionMode.DEGRADED
        state.current_phase = TrafficPhase.ALL_RED
        state.transition_step = TransitionStep.ALL_RED_CLEARANCE
        state.signals = safe_signals
        state.target_phase = None
        state.phase_started_at = current_time
        return state

    @classmethod
    def tick(cls, state: JunctionState, now: Optional[datetime] = None) -> Tuple[JunctionState, bool]:
        """
        Periodic non-blocking tick evaluation based on elapsed time.
        Validates every phase transition with SafetyPolicy.
        """
        current_time = now or datetime.now(timezone.utc)
        elapsed = (current_time - state.phase_started_at).total_seconds()
        state_changed = False

        if state.mode == JunctionMode.DEGRADED:
            return state, False

        # 1. Handling STABLE_GREEN expiration in AUTOMATIC mode
        if state.transition_step == TransitionStep.STABLE_GREEN:
            if elapsed >= cls.GREEN_DURATION_SECONDS and state.mode == JunctionMode.AUTOMATIC:
                next_phase = (
                    TrafficPhase.EAST_WEST
                    if state.current_phase == TrafficPhase.NORTH_SOUTH
                    else TrafficPhase.NORTH_SOUTH
                )
                state.target_phase = next_phase
                new_signals = cls._apply_phase_signals(state.current_phase, SignalColor.YELLOW, state.config)
                SafetyPolicy.validate_transition(state.signals, new_signals, state.config)

                state.signals = new_signals
                state.transition_step = TransitionStep.CLEARING_YELLOW
                state.phase_started_at = current_time
                state_changed = True

        # 2. Handling CLEARING_YELLOW expiration (5 seconds)
        elif state.transition_step == TransitionStep.CLEARING_YELLOW:
            if elapsed >= cls.YELLOW_DURATION_SECONDS:
                all_red_signals = SafetyPolicy.get_safe_all_red_state(state.config)
                SafetyPolicy.validate_transition(state.signals, all_red_signals, state.config)

                state.signals = all_red_signals
                state.current_phase = TrafficPhase.ALL_RED
                state.transition_step = TransitionStep.ALL_RED_CLEARANCE
                state.phase_started_at = current_time
                state_changed = True

        # 3. Handling ALL_RED_CLEARANCE expiration (2 seconds)
        elif state.transition_step == TransitionStep.ALL_RED_CLEARANCE:
            if elapsed >= cls.ALL_RED_DURATION_SECONDS:
                next_phase = state.target_phase or TrafficPhase.NORTH_SOUTH
                new_green_signals = cls._apply_phase_signals(next_phase, SignalColor.GREEN, state.config)
                SafetyPolicy.validate_transition(state.signals, new_green_signals, state.config)

                state.signals = new_green_signals
                state.current_phase = next_phase
                state.transition_step = TransitionStep.STABLE_GREEN
                state.target_phase = None
                state.phase_started_at = current_time
                state_changed = True

        return state, state_changed