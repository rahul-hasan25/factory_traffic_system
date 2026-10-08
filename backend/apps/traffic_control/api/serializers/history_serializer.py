from rest_framework import serializers
from apps.traffic_control.models import TrafficAuditLog


class TrafficHistorySerializer(serializers.ModelSerializer):
    junction_id = serializers.CharField(source="junction.junction_id", read_only=True)
    timestamp = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ", read_only=True)

    class Meta:
        model = TrafficAuditLog
        fields = [
            "id",
            "junction_id",
            "event_type",
            "direction",
            "previous_state",
            "new_state",
            "command_id",
            "details",
            "timestamp",
        ]
        read_only_fields = fields