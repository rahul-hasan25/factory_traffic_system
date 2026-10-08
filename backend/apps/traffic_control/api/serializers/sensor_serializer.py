from rest_framework import serializers

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import VehicleType
from apps.traffic_control.models import SensorEventType


class SensorEventSerializer(serializers.Serializer):
    event_id = serializers.CharField(
        max_length=100,
        required=True,
        allow_blank=False,
        help_text="Unique event identifier for idempotency guarantee",
    )
    junction_id = serializers.CharField(
        max_length=20,
        required=True,
        allow_blank=False,
        help_text="Target junction intersection",
    )
    direction = serializers.ChoiceField(
        choices=[(d.value, d.value) for d in Direction],
        required=True,
        help_text="Approach lane direction (NORTH, SOUTH, EAST, WEST)",
    )
    event_type = serializers.ChoiceField(
        choices=SensorEventType.choices,
        required=True,
        help_text="Lifecycle event: VEHICLE_ARRIVED or VEHICLE_CLEARED",
    )
    vehicle_id = serializers.CharField(
        max_length=50,
        required=True,
        allow_blank=False,
        help_text="Unique physical registration or vehicle identifier",
    )
    vehicle_type = serializers.ChoiceField(
        choices=[(v.value, v.value) for v in VehicleType],
        required=False,
        allow_null=True,
        default=VehicleType.EMPLOYEE_VEHICLE.value,
        help_text="Classification for priority weighting: EMERGENCY, TRUCK, FORKLIFT, EMPLOYEE_VEHICLE",
    )
    sequence_no = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Monotonically increasing sensor sequence counter",
    )
    timestamp = serializers.DateTimeField(
        required=True,
        help_text="ISO 8601 timestamp emitted by the physical sensor device",
    )

    def validate_event_id(self, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise serializers.ValidationError("event_id cannot be blank or whitespace.")
        return clean_value

    def validate_junction_id(self, value: str) -> str:
        clean_value = value.strip().upper()
        if not clean_value:
            raise serializers.ValidationError("junction_id cannot be blank.")
        return clean_value

    def validate_vehicle_id(self, value: str) -> str:
        clean_value = value.strip().upper()
        if not clean_value:
            raise serializers.ValidationError("vehicle_id cannot be blank.")
        return clean_value

    def validate(self, attrs):
        if not attrs.get("vehicle_type"):
            attrs["vehicle_type"] = VehicleType.EMPLOYEE_VEHICLE.value
        return attrs