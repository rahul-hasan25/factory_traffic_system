from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from apps.traffic_control.domain.safety import TrafficPhase
from apps.traffic_control.domain.state_machine import JunctionMode, TrafficFSM, TransitionStep
from apps.traffic_control.models import Junction


class StateMachineUnitTestCase(TestCase):
    def setUp(self):
        self.junction = Junction.objects.create(
            junction_id="J-TEST",
            mode=JunctionMode.AUTOMATIC.value,
            current_phase=TrafficPhase.NORTH_SOUTH.value,
            transition_step=TransitionStep.STEADY_GREEN.value,
            phase_started_at=timezone.now(),
        )

    def test_minimum_green_time_guard(self):
        """FSM must reject phase termination before min_green (10 seconds) expires."""
        fsm = TrafficFSM(self.junction)
        # Only 5 seconds elapsed
        self.junction.phase_started_at = timezone.now() - timedelta(seconds=5)
        
        can_change = fsm.can_terminate_current_phase()
        self.assertFalse(can_change)

    def test_phase_can_terminate_after_min_green(self):
        """FSM allows phase transition after min_green (10 seconds) expires."""
        fsm = TrafficFSM(self.junction)
        # 12 seconds elapsed
        self.junction.phase_started_at = timezone.now() - timedelta(seconds=12)
        
        can_change = fsm.can_terminate_current_phase()
        self.assertTrue(can_change)

    def test_step_progression_from_green_to_yellow(self):
        """Steady green progresses through yellow clearance during phase shift."""
        fsm = TrafficFSM(self.junction)
        next_step, signals = fsm.compute_transition_step(
            target_phase=TrafficPhase.EAST_WEST.value
        )
        self.assertEqual(next_step, TransitionStep.YELLOW_CLEARANCE.value)
        self.assertEqual(signals["NORTH"], "YELLOW")
        self.assertEqual(signals["SOUTH"], "YELLOW")