from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction, SafetyPolicy, SignalColor
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
)


class CommandService:
    """
    Orchestrates manual commands, controller events, hardware synchronization,
    and fail-safe device status telemetry.
    """

    @classmethod
    def process_manual_command(
        cls, junction_id: str, payload: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handles POST /api/junctions/:id/commands.
        Supports: MANUAL_GREEN_REQUEST and RETURN_TO_AUTOMATIC.
        """
        command = payload.get("command")
        direction_str = payload.get("direction")

        if not command:
            return {"status": "REJECTED", "message": "Field 'command' is mandatory."}, 400

        with transaction.atomic():
            try:
                junction = Junction.objects.select_for_update().get(junction_id=junction_id)
            except Junction.DoesNotExist:
                return {
                    "status": "REJECTED",
                    "message": f"Junction '{junction_id}' not found.",
                }, 404

            # Invariant: Prevent manual commands if junction is in critical DEGRADED state
            if junction.mode == JunctionMode.DEGRADED.value:
                return {
                    "status": "REJECTED",
                    "message": "Cannot apply manual control while junction is in DEGRADED mode.",
                }, 400

            # Reconstruct domain state from DB snapshot with injected config
            domain_state = cls._reconstruct_domain_state(junction)

            if command == "MANUAL_GREEN_REQUEST":
                if not direction_str:
                    return {
                        "status": "REJECTED",
                        "message": "Field 'direction' is required for MANUAL_GREEN_REQUEST.",
                    }, 400

                try:
                    direction = Direction(direction_str)
                except ValueError:
                    return {
                        "status": "REJECTED",
                        "message": f"Invalid direction '{direction_str}'.",
                    }, 400

                # Execute transition request safely through domain state machine
                updated_state = TrafficStateMachine.request_manual(
                    domain_state, direction, now=timezone.now()
                )
                cls._persist_domain_state(junction, updated_state)

                # Issue correlated hardware command via decoupled ControllerPort gateway
                cmd_obj = controller_gateway.dispatch_command(
                    junction=junction,
                    desired_signals=updated_state.signals,
                    direction=direction,
                    requested_state=SignalColor(updated_state.signals[direction]),
                )

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.MANUAL_OVERRIDE.value,
                    direction=direction.value,
                    command_id=cmd_obj.command_id,
                    details={
                        "command": command,
                        "target_phase": str(updated_state.target_phase),
                    },
                )

                return {
                    "status": "ACCEPTED",
                    "command_id": cmd_obj.command_id,
                    "junction_id": junction.junction_id,
                    "mode": junction.mode,
                    "transition_step": junction.transition_step,
                    "desired_signals": junction.desired_signals,
                }, 202

            elif command == "RETURN_TO_AUTOMATIC":
                updated_state = TrafficStateMachine.return_to_automatic(domain_state)
                cls._persist_domain_state(junction, updated_state)

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.RETURN_TO_AUTOMATIC.value,
                    details={"action": "Junction returned to AUTOMATIC scheduling."},
                )

                return {
                    "status": "ACCEPTED",
                    "junction_id": junction.junction_id,
                    "mode": junction.mode,
                    "message": "Junction successfully returned to AUTOMATIC mode.",
                }, 200

            else:
                return {
                    "status": "REJECTED",
                    "message": f"Unknown command '{command}'.",
                }, 400

    @classmethod
    def process_controller_event(cls, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Handles POST /api/controller-events.
        Processes device status events (OFFLINE/ONLINE), correlated hardware ACKs,
        failed execution states, and telemetry heartbeats.
        """
        command_id = payload.get("command_id")
        junction_id = payload.get("junction_id")
        status = payload.get("status")
        actual_state = payload.get("actual_state")
        device_status = payload.get("device_status") or status
        device_type = payload.get("device_type", "SIGNAL_CONTROLLER")
        direction_str = payload.get("direction")

        if not junction_id:
            return {"status": "REJECTED", "message": "Missing 'junction_id'."}, 400

        with transaction.atomic():
            try:
                junction = Junction.objects.select_for_update().get(junction_id=junction_id)
            except Junction.DoesNotExist:
                return {
                    "status": "REJECTED",
                    "message": f"Junction '{junction_id}' not found.",
                }, 404

            now = timezone.now()
            junction.last_controller_seen_at = now

            # 1. Device Failure / Telemetry Status (OFFLINE / ONLINE)
            if device_status in ("OFFLINE", "ONLINE"):
                if device_status == "OFFLINE":
                    junction.controller_status = "OFFLINE"
                    junction.mode = JunctionMode.DEGRADED.value

                    # Force safe ALL_RED fail-safe state when signal controller fails
                    safe_all_red = SafetyPolicy.get_safe_all_red_state(junction.get_domain_config())
                    junction.desired_signals = {d.value: c.value for d, c in safe_all_red.items()}
                    junction.save(
                        update_fields=[
                            "controller_status",
                            "mode",
                            "desired_signals",
                            "last_controller_seen_at",
                            "updated_at",
                        ]
                    )

                    TrafficAuditLog.objects.create(
                        junction=junction,
                        event_type=AuditEventType.DEVICE_FAILURE.value,
                        direction=direction_str,
                        details={
                            "device_type": device_type,
                            "status": "OFFLINE",
                            "action": "Junction forced into DEGRADED fail-safe mode.",
                        },
                    )
                    return {
                        "status": "PROCESSED",
                        "junction_id": junction.junction_id,
                        "controller_status": "OFFLINE",
                        "mode": junction.mode,
                    }, 200

                elif device_status == "ONLINE":
                    junction.controller_status = "ONLINE"
                    # If reconnecting from DEGRADED mode, restore AUTOMATIC scheduling
                    if junction.mode == JunctionMode.DEGRADED.value:
                        junction.mode = JunctionMode.AUTOMATIC.value

                    junction.save(
                        update_fields=[
                            "controller_status",
                            "mode",
                            "last_controller_seen_at",
                            "updated_at",
                        ]
                    )

                    TrafficAuditLog.objects.create(
                        junction=junction,
                        event_type=AuditEventType.CONTROLLER_ACKNOWLEDGED.value,
                        details={
                            "device_type": device_type,
                            "status": "ONLINE",
                            "action": "Device reconnected; telemetry synchronization restored.",
                        },
                    )
                    return {
                        "status": "PROCESSED",
                        "message": "Controller reconnected successfully.",
                    }, 200

            # 2. Correlated Controller ACK / FAILED Handling
            if command_id:
                try:
                    cmd_obj = ControllerCommand.objects.select_for_update().get(command_id=command_id)
                except ControllerCommand.DoesNotExist:
                    return {
                        "status": "REJECTED",
                        "message": f"Command '{command_id}' not found.",
                    }, 404

                # Idempotency: Ignore duplicate ACKs
                if cmd_obj.status == CommandStatus.ACK.value:
                    return {
                        "status": "IGNORED",
                        "message": f"Command '{command_id}' was already acknowledged.",
                    }, 200

                cmd_obj.status = CommandStatus.ACK.value if status == "ACK" else CommandStatus.FAILED.value
                cmd_obj.actual_state = actual_state
                cmd_obj.acked_at = now
                cmd_obj.save(update_fields=["status", "actual_state", "acked_at"])

                # Reconcile actual signals on physical confirmation
                if status == "ACK" and cmd_obj.desired_signals_snapshot:
                    junction.actual_signals = cmd_obj.desired_signals_snapshot
                    junction.controller_status = "ONLINE"
                    junction.save(
                        update_fields=[
                            "actual_signals",
                            "controller_status",
                            "last_controller_seen_at",
                            "updated_at",
                        ]
                    )
                elif status == "FAILED":
                    # Hardware rejected command: degrade junction immediately
                    junction.controller_status = "DEGRADED"
                    junction.mode = JunctionMode.DEGRADED.value
                    safe_all_red = SafetyPolicy.get_safe_all_red_state(junction.get_domain_config())
                    junction.desired_signals = {d.value: c.value for d, c in safe_all_red.items()}
                    junction.save(
                        update_fields=[
                            "controller_status",
                            "mode",
                            "desired_signals",
                            "last_controller_seen_at",
                            "updated_at",
                        ]
                    )

                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=(
                        AuditEventType.CONTROLLER_ACKNOWLEDGED.value
                        if status == "ACK"
                        else AuditEventType.DEVICE_FAILURE.value
                    ),
                    command_id=command_id,
                    details={
                        "status": status,
                        "actual_state": actual_state,
                    },
                )

                return {
                    "status": "PROCESSED",
                    "command_id": command_id,
                    "actual_signals": junction.actual_signals,
                }, 200

            # 3. Heartbeat telemetry update
            junction.controller_status = "ONLINE"
            junction.save(update_fields=["controller_status", "last_controller_seen_at", "updated_at"])
            return {"status": "PROCESSED", "message": "Telemetry heartbeat updated."}, 200

    @classmethod
    def _reconstruct_domain_state(cls, junction: Junction) -> JunctionState:
        """Reconstructs pure Python JunctionState object from database row with dynamic config."""
        signals_dict = {
            Direction(d): SignalColor(c)
            for d, c in junction.desired_signals.items()
        }
        return JunctionState(
            junction_id=junction.junction_id,
            mode=JunctionMode(junction.mode),
            current_phase=junction.current_phase,
            transition_step=TransitionStep(junction.transition_step),
            signals=signals_dict,
            target_phase=junction.target_phase,
            phase_started_at=junction.phase_started_at,
            manual_requested_direction=Direction(junction.manual_direction) if junction.manual_direction else None,
            emergency_direction=Direction(junction.emergency_direction) if junction.emergency_direction else None,
            config=junction.get_domain_config(),
        )

    @classmethod
    def _persist_domain_state(cls, junction: Junction, state: JunctionState) -> None:
        """Saves mutated domain state back into PostgreSQL Junction record."""
        junction.mode = state.mode.value
        junction.current_phase = (
            state.current_phase.value
            if hasattr(state.current_phase, "value")
            else state.current_phase
        )
        junction.transition_step = state.transition_step.value
        junction.desired_signals = {d.value: c.value for d, c in state.signals.items()}
        junction.target_phase = (
            state.target_phase.value
            if hasattr(state.target_phase, "value") and state.target_phase
            else state.target_phase
        )
        junction.manual_direction = (
            state.manual_requested_direction.value
            if state.manual_requested_direction
            else None
        )
        junction.emergency_direction = (
            state.emergency_direction.value
            if state.emergency_direction
            else None
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