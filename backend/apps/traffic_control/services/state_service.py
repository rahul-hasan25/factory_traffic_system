from typing import Dict, List

from django.db import transaction
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction, SafetyPolicy, SignalColor, TrafficPhase
from apps.traffic_control.domain.scheduler import (
    DirectionQueue,
    TrafficScheduler,
    VehicleType,
    WaitingVehicle,
)
from apps.traffic_control.domain.state_machine import (
    JunctionMode,
    JunctionState,
    TrafficStateMachine,
    TransitionStep,
)
from apps.traffic_control.gateways.controller_port import controller_gateway
from apps.traffic_control.models import (
    AuditEventType,
    CommandStatus,
    ControllerCommand,
    Junction,
    TrafficAuditLog,
    VehicleQueue,
)


class StateService:
    """
    Manages runtime synchronization, scheduled phase ticks, and system recovery.
    """

    STALE_EMERGENCY_TIMEOUT_SECONDS: float = 180.0
    MANUAL_OVERRIDE_TIMEOUT_SECONDS: float = 120.0

    @classmethod
    def evaluate_junction_tick(cls, junction_id: str) -> bool:
        """
        Executes one non-blocking tick cycle for a junction.
        Called periodically (e.g. every 1 second) by the background ticker command.
        Returns True if a state transition occurred.
        """
        now = timezone.now()

        with transaction.atomic():
            try:
                junction = Junction.objects.select_for_update().get(junction_id=junction_id)
            except Junction.DoesNotExist:
                return False

            # Check for controller timeouts (commands pending > 5 seconds)
            cls._check_command_timeouts(junction, now)

            if junction.mode == JunctionMode.DEGRADED.value:
                return False

            domain_state = cls._reconstruct_domain_state(junction)
            active_queues = cls._build_direction_queues(junction)

            # Check for active emergency vehicles in queue
            has_active_emergency = any(
                any(v.vehicle_type == VehicleType.EMERGENCY for v in q.vehicles)
                for q in active_queues.values()
            )

            # 1. Guard: Recover from stale emergency if clearance event was lost
            if not has_active_emergency and domain_state.mode == JunctionMode.EMERGENCY:
                domain_state.mode = JunctionMode.AUTOMATIC
                domain_state.emergency_direction = None
                cls._persist_domain_state(junction, domain_state)
                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.EMERGENCY_CLEARED.value,
                    details={"action": "RECOVER_STALE_EMERGENCY", "message": "No active emergency vehicle found."},
                )

            # 2. Guard: Manual Override Inactivity / Expiration Guard (Section 8)
            if domain_state.mode == JunctionMode.MANUAL:
                manual_elapsed = (now - junction.updated_at).total_seconds()
                if manual_elapsed >= cls.MANUAL_OVERRIDE_TIMEOUT_SECONDS:
                    domain_state = TrafficStateMachine.return_to_automatic(domain_state)
                    cls._persist_domain_state(junction, domain_state)
                    TrafficAuditLog.objects.create(
                        junction=junction,
                        event_type=AuditEventType.RETURN_TO_AUTOMATIC.value,
                        details={
                            "action": "MANUAL_OVERRIDE_EXPIRED",
                            "elapsed_seconds": manual_elapsed,
                            "message": f"Manual override exceeded {cls.MANUAL_OVERRIDE_TIMEOUT_SECONDS}s; restored AUTOMATIC mode.",
                        },
                    )

            # 3. If STABLE_GREEN, evaluate scheduler (in AUTOMATIC or when EMERGENCY overrides MANUAL)
            if domain_state.transition_step == TransitionStep.STABLE_GREEN:
                can_evaluate_scheduler = (
                    domain_state.mode == JunctionMode.AUTOMATIC
                    or has_active_emergency  # Emergency strictly overrides MANUAL
                )

                if can_evaluate_scheduler:
                    selected_phase = TrafficScheduler.select_next_phase(
                        queues=active_queues,
                        current_phase=domain_state.current_phase,
                        now=now,
                        config=domain_state.config,
                    )

                    # If an emergency overrides an active manual mode
                    if has_active_emergency and domain_state.mode == JunctionMode.MANUAL:
                        domain_state.mode = JunctionMode.EMERGENCY
                        TrafficAuditLog.objects.create(
                            junction=junction,
                            event_type=AuditEventType.EMERGENCY_DETECTED.value,
                            details={"action": "EMERGENCY_PREEMPTED_MANUAL_OVERRIDE"},
                        )

                    if selected_phase != domain_state.current_phase:
                        domain_state.target_phase = selected_phase

            # Progress the state machine tick non-blockingly
            previous_step = domain_state.transition_step.value
            previous_signals = dict(domain_state.signals)

            updated_state, changed = TrafficStateMachine.tick(domain_state, now=now)

            if changed:
                cls._persist_domain_state(junction, updated_state)
                cls._on_signal_transition(
                    junction=junction,
                    state=updated_state,
                    previous_step=previous_step,
                    previous_signals=previous_signals,
                )
                return True

            return False

    @classmethod
    def recover_junction_on_startup(cls, junction_id: str) -> None:
        """
        Startup crash-recovery routine (Section 12 Compliance).
        Ensures the application does not blindly trust unconfirmed physical states:
        1. Invalidates any pending controller commands that were interrupted by crash.
        2. If restarted mid-transition or if signal mismatch exists, forces fail-safe ALL_RED.
        """
        now = timezone.now()

        with transaction.atomic():
            junction, _ = Junction.objects.select_for_update().get_or_create(
                junction_id=junction_id,
                defaults={"mode": JunctionMode.AUTOMATIC.value},
            )

            # 1. Invalidate stale commands left PENDING prior to restart
            stale_commands = ControllerCommand.objects.filter(
                junction=junction,
                status=CommandStatus.PENDING.value,
            )
            for stale_cmd in stale_commands:
                stale_cmd.status = CommandStatus.TIMEOUT.value
                stale_cmd.save(update_fields=["status"])
                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.CONTROLLER_TIMEOUT.value,
                    command_id=stale_cmd.command_id,
                    direction=stale_cmd.direction,
                    details={
                        "action": "STARTUP_PURGE",
                        "reason": "Command invalidated due to server crash/restart.",
                    },
                )

            # 2. Recover to safe ALL_RED state if crashed mid-clearance or if mismatch exists
            mid_transition = junction.transition_step in (
                TransitionStep.CLEARING_YELLOW.value,
                TransitionStep.ALL_RED_CLEARANCE.value,
            )

            if mid_transition or junction.has_signal_mismatch:
                safe_state = TrafficStateMachine.create_initial_state(
                    junction_id=junction_id,
                    now=now,
                    config=junction.get_domain_config(),
                )
                cls._persist_domain_state(junction, safe_state)

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.SIGNAL_CHANGED.value,
                    previous_state=junction.transition_step,
                    new_state=TransitionStep.ALL_RED_CLEARANCE.value,
                    direction="ALL",
                    details={
                        "action": "STARTUP_RECOVERY",
                        "mid_transition": mid_transition,
                        "had_mismatch": junction.has_signal_mismatch,
                        "message": "Crash detected mid-transition or signal mismatch. Restored fail-safe ALL_RED.",
                    },
                )
            else:
                junction.phase_started_at = now
                junction.save(update_fields=["phase_started_at", "updated_at"])

    @classmethod
    def _check_command_timeouts(cls, junction: Junction, now: timezone.datetime) -> None:
        """
        Detects pending hardware commands exceeding 5.0 seconds.
        Transitions junction into DEGRADED safe mode if hardware fails to ACK.
        """
        pending_commands = ControllerCommand.objects.filter(
            junction=junction,
            status=CommandStatus.PENDING.value,
        )

        for cmd in pending_commands:
            elapsed = (now - cmd.created_at).total_seconds()
            if elapsed > 5.0:
                cmd.status = CommandStatus.TIMEOUT.value
                cmd.save(update_fields=["status"])

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.CONTROLLER_TIMEOUT.value,
                    command_id=cmd.command_id,
                    direction=cmd.direction,
                    details={"elapsed_seconds": elapsed, "action": "Command timed out."},
                )

                # Controller communication failed: degrade junction safely
                junction.controller_status = "DEGRADED"
                junction.mode = JunctionMode.DEGRADED.value
                safe_signals = SafetyPolicy.get_safe_all_red_state(junction.get_domain_config())
                junction.desired_signals = {d.value: c.value for d, c in safe_signals.items()}
                junction.save(update_fields=["controller_status", "mode", "desired_signals", "updated_at"])

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.DEVICE_FAILURE.value,
                    direction="ALL",
                    previous_state=junction.transition_step,
                    new_state="DEGRADED_ALL_RED",
                    details={"reason": f"Controller ACK timeout on command {cmd.command_id}."},
                )

    @classmethod
    def _on_signal_transition(
        cls,
        junction: Junction,
        state: JunctionState,
        previous_step: str,
        previous_signals: Dict[Direction, SignalColor],
    ) -> None:
        """Dispatches controller command via ControllerPort gateway and logs Section 11 compliant audit history."""
        # Detect primary direction of movement change for top-level audit fields
        changed_directions = [
            d for d, col in state.signals.items()
            if previous_signals.get(d) != col
        ]
        primary_dir = changed_directions[0].value if changed_directions else "ALL"
        prev_color = previous_signals.get(changed_directions[0]).value if changed_directions else previous_step
        new_color = state.signals.get(changed_directions[0]).value if changed_directions else state.transition_step.value

        # Dispatch intent through decoupled IoT ControllerPort gateway
        cmd_obj = controller_gateway.dispatch_command(
            junction=junction,
            desired_signals=state.signals,
            direction=changed_directions[0] if changed_directions else None,
            requested_state=state.signals.get(changed_directions[0]) if changed_directions else None,
        )

        TrafficAuditLog.objects.create(
            junction=junction,
            event_type=AuditEventType.SIGNAL_CHANGED.value,
            command_id=cmd_obj.command_id,
            direction=primary_dir,
            previous_state=prev_color,
            new_state=new_color,
            details={
                "transition_step": state.transition_step.value,
                "previous_step": previous_step,
                "current_phase": str(state.current_phase),
                "desired_signals": {d.value: c.value for d, c in state.signals.items()},
            },
        )

    @classmethod
    def _build_direction_queues(cls, junction: Junction) -> Dict[Direction, DirectionQueue]:
        """Loads waiting vehicles from DB into domain DirectionQueue data structures."""
        result: Dict[Direction, DirectionQueue] = {}

        for direction in Direction:
            db_vehicles = VehicleQueue.objects.filter(
                junction=junction,
                direction=direction.value,
                is_cleared=False,
            ).order_by("arrival_time")

            domain_vehicles: List[WaitingVehicle] = [
                WaitingVehicle(
                    vehicle_id=v.vehicle_id,
                    vehicle_type=VehicleType(v.vehicle_type),
                    arrival_time=v.arrival_time,
                )
                for v in db_vehicles
            ]
            result[direction] = DirectionQueue(direction=direction, vehicles=domain_vehicles)

        return result

    @classmethod
    def _reconstruct_domain_state(cls, junction: Junction) -> JunctionState:
        """Reconstructs pure Python JunctionState object from DB row with dynamic config."""
        signals_dict = {
            Direction(d): SignalColor(c)
            for d, c in junction.desired_signals.items()
        }
        return JunctionState(
            junction_id=junction.junction_id,
            mode=JunctionMode(junction.mode),
            current_phase=TrafficPhase(junction.current_phase),
            transition_step=TransitionStep(junction.transition_step),
            signals=signals_dict,
            target_phase=TrafficPhase(junction.target_phase) if junction.target_phase else None,
            phase_started_at=junction.phase_started_at,
            manual_requested_direction=Direction(junction.manual_direction) if junction.manual_direction else None,
            emergency_direction=Direction(junction.emergency_direction) if junction.emergency_direction else None,
            config=junction.get_domain_config(),
        )

    @classmethod
    def _persist_domain_state(cls, junction: Junction, state: JunctionState) -> None:
        """Persists updated domain state back into DB."""
        junction.mode = state.mode.value
        junction.current_phase = state.current_phase.value
        junction.transition_step = state.transition_step.value
        junction.desired_signals = {d.value: c.value for d, c in state.signals.items()}
        junction.target_phase = state.target_phase.value if state.target_phase else None
        junction.manual_direction = (
            state.manual_requested_direction.value if state.manual_requested_direction else None
        )
        junction.emergency_direction = (
            state.emergency_direction.value if state.emergency_direction else None
        )
        junction.phase_started_at = state.phase_started_at
        junction.save(
            update_fields=[
                "mode",
                "current_phase",
                "transition_step",
                "desired_signals",
                "target_phase",
                "manual_direction",
                "emergency_direction",
                "phase_started_at",
                "updated_at",
            ]
        )