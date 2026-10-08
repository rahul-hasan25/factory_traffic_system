from django.contrib import admin
from django.utils.html import format_html

from apps.traffic_control.models import (
    ControllerCommand,
    Junction,
    SensorEvent,
    TrafficAuditLog,
    VehicleQueue,
)


@admin.register(Junction)
class JunctionAdmin(admin.ModelAdmin):
    list_display = (
        "junction_id",
        "mode_badge",
        "current_phase",
        "transition_step",
        "controller_status_badge",
        "signal_mismatch_badge",
        "last_controller_seen_at",
        "updated_at",
    )
    list_filter = ("mode", "current_phase", "transition_step", "controller_status")
    search_fields = ("junction_id",)
    readonly_fields = (
        "junction_id",
        "has_signal_mismatch",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Core Identity & Modes",
            {
                "fields": (
                    "junction_id",
                    "mode",
                    "controller_status",
                    "has_signal_mismatch",
                    "topology_config",
                )
            },
        ),
        (
            "State Machine Progress",
            {
                "fields": (
                    "current_phase",
                    "transition_step",
                    "target_phase",
                    "phase_started_at",
                )
            },
        ),
        (
            "Active Overrides",
            {
                "fields": (
                    "manual_direction",
                    "emergency_direction",
                )
            },
        ),
        (
            "Signal States (Desired vs Actual)",
            {
                "fields": (
                    "desired_signals",
                    "actual_signals",
                    "last_controller_seen_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Mode")
    def mode_badge(self, obj: Junction):
        colors = {
            "AUTOMATIC": "#28a745",
            "MANUAL": "#fd7e14",
            "EMERGENCY": "#dc3545",
            "DEGRADED": "#6c757d",
        }
        color = colors.get(obj.mode, "#17a2b8")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.mode,
        )

    @admin.display(description="Controller")
    def controller_status_badge(self, obj: Junction):
        color = "#28a745" if obj.controller_status == "ONLINE" else "#dc3545"
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color,
            obj.controller_status,
        )

    @admin.display(description="Signal Alignment")
    def signal_mismatch_badge(self, obj: Junction):
        if obj.has_signal_mismatch:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠️ MISMATCH</span>'
            )
        return format_html(
            '<span style="color: #28a745; font-weight: bold;">✓ SYNCED</span>'
        )


@admin.register(SensorEvent)
class SensorEventAdmin(admin.ModelAdmin):
    list_display = (
        "event_id",
        "junction",
        "direction",
        "event_type_badge",
        "vehicle_id",
        "vehicle_type",
        "sequence_no",
        "is_processed",
        "sensor_timestamp",
        "received_at",
    )
    list_filter = (
        "junction",
        "direction",
        "event_type",
        "vehicle_type",
        "is_processed",
    )
    search_fields = ("event_id", "vehicle_id", "junction__junction_id")
    readonly_fields = [f.name for f in SensorEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Event Type")
    def event_type_badge(self, obj: SensorEvent):
        color = "#007bff" if obj.event_type == "VEHICLE_ARRIVED" else "#6c757d"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.event_type,
        )


@admin.register(VehicleQueue)
class VehicleQueueAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle_id",
        "junction",
        "direction",
        "vehicle_type",
        "status_badge",
        "wait_duration",
        "arrival_time",
        "cleared_at",
    )
    list_filter = ("junction", "direction", "vehicle_type", "is_cleared")
    search_fields = ("vehicle_id", "junction__junction_id")
    readonly_fields = ("arrival_time", "cleared_at", "created_at", "updated_at")

    @admin.display(description="Queue State")
    def status_badge(self, obj: VehicleQueue):
        if obj.is_cleared:
            return format_html('<span style="color: #6c757d;">CLEARED</span>')
        return format_html(
            '<span style="background-color: #ffc107; color: black; padding: 2px 6px; border-radius: 3px; font-weight: bold;">WAITING</span>'
        )

    @admin.display(description="Wait (Seconds)")
    def wait_duration(self, obj: VehicleQueue):
        return f"{obj.waiting_seconds:.1f}s"


@admin.register(ControllerCommand)
class ControllerCommandAdmin(admin.ModelAdmin):
    list_display = (
        "command_id",
        "junction",
        "direction",
        "requested_state",
        "status_badge",
        "actual_state",
        "retry_count",
        "created_at",
        "acked_at",
    )
    list_filter = ("junction", "status", "requested_state", "direction")
    search_fields = ("command_id", "junction__junction_id")
    readonly_fields = [f.name for f in ControllerCommand._meta.fields]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Execution Status")
    def status_badge(self, obj: ControllerCommand):
        colors = {
            "ACK": "#28a745",
            "PENDING": "#ffc107",
            "TIMEOUT": "#dc3545",
            "FAILED": "#6c757d",
            "REJECTED": "#343a40",
        }
        color = colors.get(obj.status, "#17a2b8")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status,
        )


@admin.register(TrafficAuditLog)
class TrafficAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "timestamp",
        "junction",
        "event_type",
        "direction",
        "previous_state",
        "new_state",
        "command_id",
    )
    list_filter = ("junction", "event_type", "direction")
    search_fields = ("command_id", "junction__junction_id", "event_type")
    readonly_fields = [f.name for f in TrafficAuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False