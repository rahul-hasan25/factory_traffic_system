from datetime import datetime
from typing import Any, Dict, Tuple

from django.db import transaction
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import VehicleType
from apps.traffic_control.domain.state_machine import JunctionMode
from apps.traffic_control.models import (
    AuditEventType,
    Junction,
    SensorEvent,
    SensorEventType,
    TrafficAuditLog,
    VehicleQueue,
)


class EventProcessorError(Exception):
    """Raised when an invalid sensor event cannot be processed."""
    pass


class EventProcessor:
    """
    Ingests and reconciles sensor telemetry.
    Ensures safe, thread-safe, and idempotent state progression.
    """

    @classmethod
    def process_sensor_event(cls, data: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Main entry point for POST /api/sensor-events.
        Returns: (response_data, http_status_code)
        """
        event_id = data.get("event_id")
        junction_id = data.get("junction_id")
        direction_str = data.get("direction")
        event_type_str = data.get("event_type")
        vehicle_id = data.get("vehicle_id")
        vehicle_type_str = data.get("vehicle_type", VehicleType.EMPLOYEE_VEHICLE.value)
        sequence_no = data.get("sequence_no")
        sensor_timestamp_raw = data.get("timestamp")

        # 1. Basic Payload Validation
        if not all([event_id, junction_id, direction_str, event_type_str, vehicle_id]):
            return {
                "status": "REJECTED",
                "message": "Missing mandatory sensor event fields.",
            }, 400

        try:
            direction = Direction(direction_str)
        except ValueError:
            return {"status": "REJECTED", "message": f"Unknown direction '{direction_str}'."}, 400

        try:
            event_type = SensorEventType(event_type_str)
        except ValueError:
            return {"status": "REJECTED", "message": f"Unknown event_type '{event_type_str}'."}, 400

        try:
            vehicle_type = VehicleType(vehicle_type_str)
        except ValueError:
            return {"status": "REJECTED", "message": f"Unknown vehicle_type '{vehicle_type_str}'."}, 400

        # Parse sensor timestamp
        if isinstance(sensor_timestamp_raw, datetime):
            sensor_timestamp = sensor_timestamp_raw
        elif isinstance(sensor_timestamp_raw, str):
            try:
                sensor_timestamp = datetime.fromisoformat(sensor_timestamp_raw.replace("Z", "+00:00"))
            except ValueError:
                sensor_timestamp = timezone.now()
        else:
            sensor_timestamp = timezone.now()

        # 2. Concurrency Lock & Transaction Boundary
        with transaction.atomic():
            # Lock the junction row to serialize all simultaneous operations on this intersection
            try:
                junction = Junction.objects.select_for_update().get(junction_id=junction_id)
            except Junction.DoesNotExist:
                return {
                    "status": "REJECTED",
                    "message": f"Junction '{junction_id}' does not exist.",
                }, 404

            # 3. Idempotency Check: Verify if event_id has already been processed
            if SensorEvent.objects.filter(event_id=event_id).exists():
                TrafficAuditLog.objects.create(
                    junction=junction,
                    event_type=AuditEventType.SENSOR_EVENT_DUPLICATE.value,
                    direction=direction.value,
                    details={
                        "event_id": event_id,
                        "vehicle_id": vehicle_id,
                        "message": "Duplicate sensor event ignored. Traffic queue unchanged.",
                    },
                )
                return {
                    "status": "IGNORED",
                    "message": f"Event '{event_id}' has already been processed.",
                    "event_id": event_id,
                    "queues": cls.get_active_queue_counts(junction),
                }, 200

            # 4. Out-of-order & Sequence validation check
            processing_notes = None
            last_event = (
                SensorEvent.objects.filter(junction=junction, direction=direction.value)
                .order_by("-sequence_no")
                .first()
            )
            if last_event and sequence_no is not None and last_event.sequence_no is not None:
                if sequence_no < last_event.sequence_no:
                    processing_notes = f"Out-of-order event: received seq {sequence_no} after {last_event.sequence_no}."

            # Save the raw event to ensure DB-level deduplication
            sensor_event = SensorEvent.objects.create(
                event_id=event_id,
                junction=junction,
                direction=direction.value,
                event_type=event_type.value,
                vehicle_id=vehicle_id,
                vehicle_type=vehicle_type.value,
                sequence_no=sequence_no,
                sensor_timestamp=sensor_timestamp,
                is_processed=False,
                processing_notes=processing_notes,
            )

            # 5. Queue Mutation
            if event_type == SensorEventType.VEHICLE_ARRIVED:
                cls._handle_vehicle_arrived(
                    junction=junction,
                    direction=direction,
                    vehicle_id=vehicle_id,
                    vehicle_type=vehicle_type,
                    arrival_time=sensor_timestamp,
                    event_id=event_id,
                )
            elif event_type == SensorEventType.VEHICLE_CLEARED:
                cls._handle_vehicle_cleared(
                    junction=junction,
                    direction=direction,
                    vehicle_id=vehicle_id,
                    event_id=event_id,
                )

            sensor_event.is_processed = True
            sensor_event.save(update_fields=["is_processed"])

            # Return latest junction queue snapshot
            current_queues = cls.get_active_queue_counts(junction)
            return {
                "status": "PROCESSED",
                "event_id": event_id,
                "junction_id": junction.junction_id,
                "direction": direction.value,
                "event_type": event_type.value,
                "queues": current_queues,
            }, 201

    @classmethod
    def _handle_vehicle_arrived(
        cls,
        junction: Junction,
        direction: Direction,
        vehicle_id: str,
        vehicle_type: VehicleType,
        arrival_time: datetime,
        event_id: str,
    ) -> None:
        """Adds vehicle to the active waiting queue and handles emergency triggers."""
        VehicleQueue.objects.create(
            junction=junction,
            direction=direction.value,
            vehicle_id=vehicle_id,
            vehicle_type=vehicle_type.value,
            arrival_time=arrival_time,
            is_cleared=False,
        )

        TrafficAuditLog.objects.create(
            junction=junction,
            event_type=AuditEventType.VEHICLE_DETECTED.value,
            direction=direction.value,
            details={
                "event_id": event_id,
                "vehicle_id": vehicle_id,
                "vehicle_type": vehicle_type.value,
            },
        )

        # If incoming vehicle is EMERGENCY, initiate safe preemption immediately
        if vehicle_type == VehicleType.EMERGENCY:
            junction.mode = JunctionMode.EMERGENCY.value
            junction.emergency_direction = direction.value
            junction.save(update_fields=["mode", "emergency_direction", "updated_at"])

            TrafficAuditLog.objects.create(
                junction=junction,
                event_type=AuditEventType.EMERGENCY_DETECTED.value,
                direction=direction.value,
                details={
                    "event_id": event_id,
                    "vehicle_id": vehicle_id,
                    "action": "Safe emergency preemption initiated.",
                },
            )

    @classmethod
    def _handle_vehicle_cleared(
        cls,
        junction: Junction,
        direction: Direction,
        vehicle_id: str,
        event_id: str,
    ) -> None:
        """
        Clears the vehicle from the active queue.
        Safely guarantees queue never drops below 0 even if no matching arrival exists.
        """
        now = timezone.now()

        # Find active vehicle matching ID in this direction
        vehicle = (
            VehicleQueue.objects.filter(
                junction=junction,
                direction=direction.value,
                vehicle_id=vehicle_id,
                is_cleared=False,
            )
            .order_by("arrival_time")
            .first()
        )

        # If matching vehicle not found by vehicle_id, clear oldest vehicle in this lane
        if not vehicle:
            vehicle = (
                VehicleQueue.objects.filter(
                    junction=junction,
                    direction=direction.value,
                    is_cleared=False,
                )
                .order_by("arrival_time")
                .first()
            )

        if vehicle:
            vehicle.is_cleared = True
            vehicle.cleared_at = now
            vehicle.save(update_fields=["is_cleared", "cleared_at", "updated_at"])

            # Check if cleared vehicle was an active emergency vehicle
            if vehicle.vehicle_type == VehicleType.EMERGENCY.value:
                remaining_emergencies = VehicleQueue.objects.filter(
                    junction=junction,
                    vehicle_type=VehicleType.EMERGENCY.value,
                    is_cleared=False,
                ).exists()

                if not remaining_emergencies:
                    junction.mode = JunctionMode.AUTOMATIC.value
                    junction.emergency_direction = None
                    junction.save(update_fields=["mode", "emergency_direction", "updated_at"])

                    TrafficAuditLog.objects.create(
                        junction=junction,
                        event_type=AuditEventType.EMERGENCY_CLEARED.value,
                        direction=direction.value,
                        details={"vehicle_id": vehicle_id, "message": "Emergency cleared."},
                    )
        else:
            TrafficAuditLog.objects.create(
                junction=junction,
                event_type=AuditEventType.SENSOR_EVENT_REJECTED.value,
                direction=direction.value,
                details={
                    "event_id": event_id,
                    "vehicle_id": vehicle_id,
                    "reason": "VEHICLE_CLEARED received but queue was already 0. Invariant queue >= 0 preserved.",
                },
            )

        TrafficAuditLog.objects.create(
            junction=junction,
            event_type=AuditEventType.VEHICLE_CLEARED.value,
            direction=direction.value,
            details={"event_id": event_id, "vehicle_id": vehicle_id},
        )

    @classmethod
    def get_active_queue_counts(cls, junction: Junction) -> Dict[str, int]:
        """Returns the current waiting queue count for all four directions."""
        counts = {
            Direction.NORTH.value: 0,
            Direction.SOUTH.value: 0,
            Direction.EAST.value: 0,
            Direction.WEST.value: 0,
        }
        for direction_choice in Direction:
            cnt = VehicleQueue.objects.filter(
                junction=junction,
                direction=direction_choice.value,
                is_cleared=False,
            ).count()
            counts[direction_choice.value] = max(0, cnt)
        return counts