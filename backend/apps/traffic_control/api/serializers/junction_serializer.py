from typing import Dict
from rest_framework import serializers

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.models import Junction, VehicleQueue


class JunctionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Junction
        fields = [
            "junction_id",
            "mode",
            "current_phase",
            "transition_step",
            "controller_status",
            "topology_config",
            "updated_at",
        ]
        read_only_fields = fields


class JunctionCreateSerializer(serializers.ModelSerializer):
    """Serializer for POST /api/junctions to register new intersections (e.g. Junction B, C)."""

    class Meta:
        model = Junction
        fields = ["junction_id", "mode", "controller_status", "topology_config"]

    def validate_junction_id(self, value: str) -> str:
        clean_value = value.strip().upper()
        if not clean_value:
            raise serializers.ValidationError("Junction ID cannot be empty.")
        if Junction.objects.filter(junction_id=clean_value).exists():
            raise serializers.ValidationError(f"Junction '{clean_value}' already exists.")
        return clean_value


class JunctionStatusSerializer(serializers.ModelSerializer):
    """
    Serializer strictly complying with Section 10.3 specification:
    {
      "junction_id": "A",
      "mode": "AUTOMATIC",
      "phase": "NORTH_SOUTH",
      "controller_status": "ONLINE",
      "desired_signals": {"NORTH":"GREEN","SOUTH":"GREEN","EAST":"RED","WEST":"RED"},
      "actual_signals": {"NORTH":"GREEN","SOUTH":"GREEN","EAST":"RED","WEST":"RED"},
      "queues": {"NORTH":3,"SOUTH":1,"EAST":7,"WEST":2}
    }
    """

    phase = serializers.CharField(source="current_phase", read_only=True)
    queues = serializers.SerializerMethodField()
    has_mismatch = serializers.BooleanField(source="has_signal_mismatch", read_only=True)

    class Meta:
        model = Junction
        fields = [
            "junction_id",
            "mode",
            "phase",
            "transition_step",
            "controller_status",
            "desired_signals",
            "actual_signals",
            "queues",
            "has_mismatch",
            "manual_direction",
            "emergency_direction",
            "phase_started_at",
        ]
        read_only_fields = fields

    def get_queues(self, obj: Junction) -> Dict[str, int]:
        """Calculates real-time active waiting vehicle counts per direction."""
        counts = {
            Direction.NORTH.value: 0,
            Direction.SOUTH.value: 0,
            Direction.EAST.value: 0,
            Direction.WEST.value: 0,
        }
        for direction_choice in Direction:
            cnt = VehicleQueue.objects.filter(
                junction=obj,
                direction=direction_choice.value,
                is_cleared=False,
            ).count()
            counts[direction_choice.value] = max(0, cnt)
        return counts