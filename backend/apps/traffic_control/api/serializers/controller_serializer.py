from rest_framework import serializers

from apps.traffic_control.domain.safety import SignalColor
from apps.traffic_control.models import CommandStatus


class ControllerEventSerializer(serializers.Serializer):
    """
    Validates physical-controller simulation events and acknowledgements.
    Example 1 (Command ACK):
    {
      "command_id": "cmd-8001",
      "junction_id": "A",
      "status": "ACK",
      "actual_state": "GREEN"
    }

    Example 2 (Device Status/Heartbeat):
    {
      "junction_id": "A",
      "device_status": "OFFLINE"
    }
    """

    command_id = serializers.CharField(
        max_length=100,
        required=False,
        allow_null=True,
        help_text="Unique correlation identifier of the command being acknowledged",
    )
    junction_id = serializers.CharField(
        max_length=20,
        required=True,
        allow_blank=False,
        help_text="Target junction intersection identifier",
    )
    status = serializers.ChoiceField(
        choices=CommandStatus.choices,
        required=False,
        allow_null=True,
        help_text="Execution acknowledgement status: ACK, FAILED, TIMEOUT",
    )
    actual_state = serializers.ChoiceField(
        choices=[(c.value, c.value) for c in SignalColor],
        required=False,
        allow_null=True,
        help_text="Physical signal color confirmed by the edge hardware",
    )
    device_status = serializers.ChoiceField(
        choices=["ONLINE", "OFFLINE", "DEGRADED"],
        required=False,
        allow_null=True,
        help_text="Physical controller connectivity health status",
    )

    def validate_junction_id(self, value: str) -> str:
        clean_value = value.strip().upper()
        if not clean_value:
            raise serializers.ValidationError("junction_id cannot be blank.")
        return clean_value

    def validate(self, attrs):
        command_id = attrs.get("command_id")
        device_status = attrs.get("device_status")
        status = attrs.get("status")

        # Invariant: Payload must either acknowledge a command OR report device connectivity health
        if not command_id and not device_status:
            raise serializers.ValidationError(
                "Either 'command_id' (with 'status') or 'device_status' must be provided."
            )

        if command_id and not status:
            raise serializers.ValidationError(
                {"status": "Field 'status' (e.g., 'ACK') is required when 'command_id' is supplied."}
            )

        return attrs