from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import VehicleType
from apps.traffic_control.models import (
    CommandStatus,
    ControllerCommand,
    Junction,
    SensorEvent,
    SensorEventType,
    VehicleQueue,
)
from apps.traffic_control.services import CommandService, EventProcessor


class ServiceLayerTestCase(TestCase):
    def setUp(self):
        self.junction = Junction.objects.create(junction_id="J-SERVICE")

    def test_event_processor_idempotency(self):
        """Submitting the identical event_id twice must be accepted with 200 OK and not duplicate queue."""
        payload = {
            "event_id": "evt-unique-101",
            "junction_id": "J-SERVICE",
            "direction": Direction.NORTH.value,
            "event_type": SensorEventType.VEHICLE_ARRIVED.value,
            "vehicle_id": "VH-TEST-1",
            "vehicle_type": VehicleType.TRUCK.value,
            "sequence_no": 1,
            "timestamp": timezone.now(),
        }

        # First ingestion -> 201 CREATED
        res_first, code_first = EventProcessor.process_sensor_event(payload)
        self.assertEqual(code_first, status.HTTP_201_CREATED)
        self.assertEqual(VehicleQueue.objects.filter(junction=self.junction).count(), 1)

        # Duplicate ingestion -> 200 OK (Ignored safely)
        res_second, code_second = EventProcessor.process_sensor_event(payload)
        self.assertEqual(code_second, status.HTTP_200_OK)
        self.assertEqual(res_second["status"], "IGNORED_DUPLICATE")
        self.assertEqual(VehicleQueue.objects.filter(junction=self.junction).count(), 1)

    def test_vehicle_cleared_event_marks_queue_item(self):
        """VEHICLE_CLEARED resolves active vehicle in the queue."""
        # Arrive
        EventProcessor.process_sensor_event({
            "event_id": "evt-arr-1",
            "junction_id": "J-SERVICE",
            "direction": Direction.NORTH.value,
            "event_type": SensorEventType.VEHICLE_ARRIVED.value,
            "vehicle_id": "VH-RESOLVE-1",
            "vehicle_type": VehicleType.EMPLOYEE_VEHICLE.value,
            "sequence_no": 10,
            "timestamp": timezone.now(),
        })

        # Clear
        _, code = EventProcessor.process_sensor_event({
            "event_id": "evt-clr-1",
            "junction_id": "J-SERVICE",
            "direction": Direction.NORTH.value,
            "event_type": SensorEventType.VEHICLE_CLEARED.value,
            "vehicle_id": "VH-RESOLVE-1",
            "vehicle_type": VehicleType.EMPLOYEE_VEHICLE.value,
            "sequence_no": 11,
            "timestamp": timezone.now(),
        })

        self.assertEqual(code, status.HTTP_201_CREATED)
        queue_item = VehicleQueue.objects.get(vehicle_id="VH-RESOLVE-1")
        self.assertTrue(queue_item.is_cleared)

    def test_controller_ack_updates_actual_signals(self):
        """Controller ACK reconciles command status and physical state."""
        cmd = ControllerCommand.objects.create(
            command_id="cmd-test-555",
            junction=self.junction,
            direction=Direction.NORTH.value,
            requested_state="GREEN",
            status=CommandStatus.PENDING,
        )

        res, code = CommandService.process_controller_event({
            "command_id": "cmd-test-555",
            "junction_id": "J-SERVICE",
            "status": "ACK",
            "actual_state": "GREEN",
        })

        self.assertEqual(code, status.HTTP_200_OK)
        cmd.refresh_from_db()
        self.assertEqual(cmd.status, CommandStatus.ACK)
        self.assertEqual(cmd.actual_state, "GREEN")