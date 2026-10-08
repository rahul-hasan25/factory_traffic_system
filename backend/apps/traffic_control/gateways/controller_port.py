from abc import ABC, abstractmethod
from typing import Dict, Optional
import uuid

from apps.traffic_control.domain.safety import Direction, SignalColor
from apps.traffic_control.models import (
    AuditEventType,
    CommandStatus,
    ControllerCommand,
    Junction,
    TrafficAuditLog,
)


class ControllerPort(ABC):
    """
    Port (Interface) for dispatching commands to physical junction controllers.
    Decouples the core engine from HTTP/REST simulators or MQTT brokers (Section 13).
    """

    @abstractmethod
    def dispatch_command(
        self,
        junction: Junction,
        desired_signals: Dict[Direction, SignalColor],
        direction: Optional[Direction] = None,
        requested_state: Optional[SignalColor] = None,
    ) -> ControllerCommand:
        """Dispatches an intent to the physical device or simulator."""
        pass


class RestSimulatorAdapter(ControllerPort):
    """
    Adapter implementation simulating physical controllers via database commands.
    In production, this adapter can be swapped with MqttControllerAdapter without
    altering core traffic management logic or state machines.
    """

    def dispatch_command(
        self,
        junction: Junction,
        desired_signals: Dict[Direction, SignalColor],
        direction: Optional[Direction] = None,
        requested_state: Optional[SignalColor] = None,
    ) -> ControllerCommand:
        command_id = f"cmd-{uuid.uuid4().hex[:8]}"
        serialized_signals = {d.value: c.value for d, c in desired_signals.items()}

        cmd = ControllerCommand.objects.create(
            command_id=command_id,
            junction=junction,
            direction=direction.value if direction else None,
            requested_state=requested_state.value if requested_state else None,
            desired_signals_snapshot=serialized_signals,
            status=CommandStatus.PENDING.value,
        )

        TrafficAuditLog.objects.create(
            junction=junction,
            event_type=AuditEventType.SIGNAL_STATE_REQUESTED.value,
            direction=direction.value if direction else "ALL",
            command_id=command_id,
            details={
                "requested_state": requested_state.value if requested_state else "PHASE_CYCLE",
                "desired_signals": serialized_signals,
            },
        )

        return cmd


# Global dependency injection gateway instance
controller_gateway: ControllerPort = RestSimulatorAdapter()