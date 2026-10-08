from django.test import TestCase

from apps.traffic_control.domain.safety import Direction, SignalColor, TrafficPhase
from apps.traffic_control.domain.state_machine import SafetyViolationError, TrafficSafetyValidator


class DomainSafetyUnitTestCase(TestCase):
    def test_conflicting_green_safety_violation(self):
        """Conflicting green signals (e.g. NORTH and EAST) must trigger an immediate safety error."""
        invalid_signals = {
            Direction.NORTH.value: SignalColor.GREEN.value,
            Direction.SOUTH.value: SignalColor.RED.value,
            Direction.EAST.value: SignalColor.GREEN.value,
            Direction.WEST.value: SignalColor.RED.value,
        }

        with self.assertRaises(SafetyViolationError):
            TrafficSafetyValidator.validate_signal_state(invalid_signals)

    def test_permissible_safe_signals(self):
        """North-South Green while East-West Red must be fully valid."""
        valid_signals = {
            Direction.NORTH.value: SignalColor.GREEN.value,
            Direction.SOUTH.value: SignalColor.GREEN.value,
            Direction.EAST.value: SignalColor.RED.value,
            Direction.WEST.value: SignalColor.RED.value,
        }
        # Should not raise exception
        self.assertTrue(TrafficSafetyValidator.is_safe_state(valid_signals))

    def test_all_red_fail_safe_validity(self):
        """All directions RED is the baseline safe state."""
        all_red = {
            Direction.NORTH.value: SignalColor.RED.value,
            Direction.SOUTH.value: SignalColor.RED.value,
            Direction.EAST.value: SignalColor.RED.value,
            Direction.WEST.value: SignalColor.RED.value,
        }
        self.assertTrue(TrafficSafetyValidator.is_safe_state(all_red))

    def test_illegal_transition_green_directly_to_red(self):
        """A direct GREEN -> RED transition without YELLOW violates safety policy."""
        is_legal = TrafficSafetyValidator.validate_color_transition(
            current_color=SignalColor.GREEN.value,
            next_color=SignalColor.RED.value,
        )
        self.assertFalse(is_legal)

    def test_legal_transition_green_to_yellow_to_red(self):
        """GREEN -> YELLOW and YELLOW -> RED transitions are permitted."""
        self.assertTrue(
            TrafficSafetyValidator.validate_color_transition(
                current_color=SignalColor.GREEN.value,
                next_color=SignalColor.YELLOW.value,
            )
        )
        self.assertTrue(
            TrafficSafetyValidator.validate_color_transition(
                current_color=SignalColor.YELLOW.value,
                next_color=SignalColor.RED.value,
            )
        )