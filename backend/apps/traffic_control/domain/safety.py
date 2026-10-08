from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Optional, Set


class Direction(str, Enum):
    NORTH = "NORTH"
    SOUTH = "SOUTH"
    EAST = "EAST"
    WEST = "WEST"


class SignalColor(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class TrafficPhase(str, Enum):
    NORTH_SOUTH = "NORTH_SOUTH"
    EAST_WEST = "EAST_WEST"
    ALL_RED = "ALL_RED"


class SafetyViolationError(Exception):
    """Raised when an operation would violate safety invariants."""
    pass


@dataclass(frozen=True)
class JunctionConfiguration:
    """
    Encapsulates junction-specific geometry and conflict rules.
    Allows Junction B, C, D to have unique phase groupings without altering domain code.
    """
    phase_directions: Dict[TrafficPhase, Set[Direction]] = field(
        default_factory=lambda: {
            TrafficPhase.NORTH_SOUTH: {Direction.NORTH, Direction.SOUTH},
            TrafficPhase.EAST_WEST: {Direction.EAST, Direction.WEST},
            TrafficPhase.ALL_RED: set(),
        }
    )
    conflict_pairs: FrozenSet[FrozenSet[Direction]] = field(
        default_factory=lambda: frozenset({
            frozenset({Direction.NORTH, Direction.EAST}),
            frozenset({Direction.NORTH, Direction.WEST}),
            frozenset({Direction.SOUTH, Direction.EAST}),
            frozenset({Direction.SOUTH, Direction.WEST}),
        })
    )


# Standard default configuration representing Junction A
DEFAULT_JUNCTION_CONFIG = JunctionConfiguration()


class SafetyPolicy:
    """
    Centrally manages safety invariants:
    1. Conflicting traffic phases must never simultaneously receive GREEN.
    2. A GREEN phase must never transition directly into a conflicting GREEN phase.
    3. Manual or emergency priority must not bypass the safe signal-transition sequence.
    4. Invalid or unexpected commands must not place the junction into an unsafe state.
    """

    # Backward compatibility mappings for legacy references
    PHASE_DIRECTIONS: Dict[TrafficPhase, Set[Direction]] = DEFAULT_JUNCTION_CONFIG.phase_directions
    CONFLICT_PAIRS: FrozenSet[FrozenSet[Direction]] = DEFAULT_JUNCTION_CONFIG.conflict_pairs

    @classmethod
    def get_phase_for_direction(
        cls, direction: Direction, config: Optional[JunctionConfiguration] = None
    ) -> TrafficPhase:
        """Determines which operational phase serves the given direction under current config."""
        active_config = config or DEFAULT_JUNCTION_CONFIG
        for phase, directions in active_config.phase_directions.items():
            if direction in directions:
                return phase
        raise SafetyViolationError(f"Direction {direction} does not map to any valid phase.")

    @classmethod
    def are_conflicting(
        cls, dir_a: Direction, dir_b: Direction, config: Optional[JunctionConfiguration] = None
    ) -> bool:
        """Checks if two distinct directions have crossing trajectories under current topology."""
        if dir_a == dir_b:
            return False
        active_config = config or DEFAULT_JUNCTION_CONFIG
        return frozenset({dir_a, dir_b}) in active_config.conflict_pairs

    @classmethod
    def validate_signal_state(
        cls, signals: Dict[Direction, SignalColor], config: Optional[JunctionConfiguration] = None
    ) -> None:
        """
        Validates signal states across all monitored directions.
        Raises SafetyViolationError if conflicting directions are simultaneously non-RED.
        """
        active_config = config or DEFAULT_JUNCTION_CONFIG

        # 1. Conflicting directions must never both be GREEN
        green_directions = [d for d, color in signals.items() if color == SignalColor.GREEN]
        for i in range(len(green_directions)):
            for j in range(i + 1, len(green_directions)):
                if cls.are_conflicting(green_directions[i], green_directions[j], active_config):
                    raise SafetyViolationError(
                        f"CRITICAL SAFETY VIOLATION: Conflicting directions "
                        f"{green_directions[i]} and {green_directions[j]} are both GREEN."
                    )

        # 2. Conflicting movements must never both be active (GREEN or YELLOW)
        active_directions = [
            d for d, color in signals.items()
            if color in (SignalColor.GREEN, SignalColor.YELLOW)
        ]
        for i in range(len(active_directions)):
            for j in range(i + 1, len(active_directions)):
                if cls.are_conflicting(active_directions[i], active_directions[j], active_config):
                    raise SafetyViolationError(
                        f"CRITICAL SAFETY VIOLATION: Active movements conflict between "
                        f"{active_directions[i]} and {active_directions[j]}."
                    )

    @classmethod
    def validate_transition(
        cls,
        current_signals: Dict[Direction, SignalColor],
        target_signals: Dict[Direction, SignalColor],
        config: Optional[JunctionConfiguration] = None,
    ) -> None:
        """Ensures a transition does not bypass YELLOW or ALL_RED clearance."""
        active_config = config or DEFAULT_JUNCTION_CONFIG
        cls.validate_signal_state(target_signals, active_config)

        for direction, target_color in target_signals.items():
            curr_color = current_signals.get(direction, SignalColor.RED)
            # GREEN cannot drop directly to RED without YELLOW clearance
            if curr_color == SignalColor.GREEN and target_color == SignalColor.RED:
                raise SafetyViolationError(
                    f"UNSAFE TRANSITION: Direction {direction} cannot change directly "
                    f"from GREEN to RED without a YELLOW clearance period."
                )
            # Cannot become GREEN if any conflicting lane is not fully RED
            if target_color == SignalColor.GREEN:
                for other_dir, other_curr_color in current_signals.items():
                    if cls.are_conflicting(direction, other_dir, active_config):
                        if other_curr_color != SignalColor.RED:
                            raise SafetyViolationError(
                                f"UNSAFE TRANSITION: Direction {direction} cannot become GREEN "
                                f"while conflicting direction {other_dir} is {other_curr_color}."
                            )

    @classmethod
    def get_safe_all_red_state(
        cls, config: Optional[JunctionConfiguration] = None
    ) -> Dict[Direction, SignalColor]:
        """Provides fail-safe default state where every configured signal is RED."""
        active_config = config or DEFAULT_JUNCTION_CONFIG
        all_directions: Set[Direction] = set()
        for dirs in active_config.phase_directions.values():
            all_directions.update(dirs)

        if not all_directions:
            all_directions = {Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST}

        return {d: SignalColor.RED for d in all_directions}