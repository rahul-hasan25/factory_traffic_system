from rest_framework import serializers
from apps.traffic_control.domain.safety import Direction


class CommandType:
    MANUAL_GREEN_REQUEST = "MANUAL_GREEN_REQUEST"
    RETURN_TO_AUTOMATIC = "RETURN_TO_AUTOMATIC"
    CHOICES = [MANUAL_GREEN_REQUEST, RETURN_TO_AUTOMATIC]


class JunctionCommandSerializer(serializers.Serializer):
    """
    Validates manual control commands sent by operators/administrators.
    Example 1:
    {
      "command": "MANUAL_GREEN_REQUEST",
      "direction": "WEST"
    }

    Example 2:
    {
      "command": "RETURN_TO_AUTOMATIC"
    }
    """

    command = serializers.ChoiceField(
        choices=CommandType.CHOICES,
        required=True,
        help_text="Control action: MANUAL_GREEN_REQUEST or RETURN_TO_AUTOMATIC",
    )
    direction = serializers.ChoiceField(
        choices=[(d.value, d.value) for d in Direction],
        required=False,
        allow_null=True,
        help_text="Target direction approach to grant green (required for MANUAL_GREEN_REQUEST)",
    )

    def validate(self, attrs):
        command = attrs.get("command")
        direction = attrs.get("direction")

        # Invariant: If operator requests manual green, targeted direction is mandatory
        if command == CommandType.MANUAL_GREEN_REQUEST and not direction:
            raise serializers.ValidationError(
                {"direction": "Direction is required when issuing MANUAL_GREEN_REQUEST."}
            )

        return attrs