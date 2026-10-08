from django.db import models

from apps.traffic_control.domain.safety import Direction, SignalColor
from .junction import Junction


class AuditEventType(models.TextChoices):
    VEHICLE_DETECTED = "VEHICLE_DETECTED", "VEHICLE_DETECTED"
    VEHICLE_CLEARED = "VEHICLE_CLEARED", "VEHICLE_CLEARED"
    SENSOR_EVENT_DUPLICATE = "SENSOR_EVENT_DUPLICATE", "SENSOR_EVENT_DUPLICATE"
    SENSOR_EVENT_REJECTED = "SENSOR_EVENT_REJECTED", "SENSOR_EVENT_REJECTED"
    SIGNAL_TRANSITION_STARTED = "SIGNAL_TRANSITION_STARTED", "SIGNAL_TRANSITION_STARTED"
    SIGNAL_STATE_REQUESTED = "SIGNAL_STATE_REQUESTED", "SIGNAL_STATE_REQUESTED"
    SIGNAL_STATE_CONFIRMED = "SIGNAL_STATE_CONFIRMED", "SIGNAL_STATE_CONFIRMED"
    SIGNAL_CHANGED = "SIGNAL_CHANGED", "SIGNAL_CHANGED"
    EMERGENCY_DETECTED = "EMERGENCY_DETECTED", "EMERGENCY_DETECTED"
    EMERGENCY_CLEARED = "EMERGENCY_CLEARED", "EMERGENCY_CLEARED"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE", "MANUAL_OVERRIDE"
    RETURN_TO_AUTOMATIC = "RETURN_TO_AUTOMATIC", "RETURN_TO_AUTOMATIC"
    MODE_CHANGED = "MODE_CHANGED", "MODE_CHANGED"
    CONTROLLER_ACKNOWLEDGED = "CONTROLLER_ACKNOWLEDGED", "CONTROLLER_ACKNOWLEDGED"
    CONTROLLER_TIMEOUT = "CONTROLLER_TIMEOUT", "CONTROLLER_TIMEOUT"
    DEVICE_FAILURE = "DEVICE_FAILURE", "DEVICE_FAILURE"
    DEVICE_RECONNECTED = "DEVICE_RECONNECTED", "DEVICE_RECONNECTED"


class TrafficAuditLog(models.Model):
    junction = models.ForeignKey(Junction,on_delete=models.CASCADE,related_name="audit_logs")
    event_type = models.CharField(max_length=60,choices=AuditEventType.choices,db_index=True)
    direction = models.CharField(max_length=15,null=True,blank=True)
    previous_state = models.CharField(max_length=40,null=True,blank=True)
    new_state = models.CharField(max_length=40,null=True,blank=True)
    command_id = models.CharField(max_length=100,null=True,blank=True,db_index=True)
    details = models.JSONField(default=dict,blank=True)
    timestamp = models.DateTimeField(auto_now_add=True,db_index=True)

    class Meta:
        db_table = "traffic_audit_logs"
        verbose_name = "Traffic Audit Log"
        verbose_name_plural = "Traffic Audit Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["junction", "-timestamp"]),
            models.Index(fields=["event_type", "-timestamp"]),
        ]

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.junction_id} | {self.event_type} | {self.direction or 'ALL'}"