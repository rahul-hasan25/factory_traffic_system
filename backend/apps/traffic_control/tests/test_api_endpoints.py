from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.traffic_control.models import Junction, TrafficAuditLog


class TrafficApiEndpointIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.junction = Junction.objects.create(junction_id="A")

    def test_get_junction_status(self):
        """GET /api/junctions/A/status returns live status matching specification schema."""
        url = reverse("junction-status", kwargs={"junction_id": "A"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["junction_id"], "A")
        self.assertIn("desired_signals", data)
        self.assertIn("actual_signals", data)
        self.assertIn("queues", data)
        self.assertEqual(data["queues"]["NORTH"], 0)

    def test_post_sensor_events_valid(self):
        """POST /api/sensor-events ingests telemetry successfully."""
        url = reverse("sensor-events")
        payload = {
            "event_id": "evt-e2e-001",
            "junction_id": "A",
            "direction": "NORTH",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "VH-900",
            "vehicle_type": "TRUCK",
            "sequence_no": 100,
            "timestamp": "2026-10-08T05:00:00Z",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_post_manual_override_command(self):
        """POST /api/junctions/A/commands initiates manual override."""
        url = reverse("junction-command", kwargs={"junction_id": "A"})
        payload = {
            "command": "MANUAL_GREEN_REQUEST",
            "direction": "WEST",
        }
        response = self.client.post(url, data=payload, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_202_ACCEPTED],
        )

    def test_get_junction_history(self):
        """GET /api/junctions/A/history returns chronological audit records."""
        TrafficAuditLog.objects.create(
            junction=self.junction,
            event_type="SIGNAL_CHANGED",
            direction="NORTH",
            previous_state="RED",
            new_state="GREEN",
            command_id="cmd-init-1",
        )

        url = reverse("junction-history", kwargs={"junction_id": "A"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(len(data) >= 1)
        self.assertEqual(data[0]["event_type"], "SIGNAL_CHANGED")
        self.assertEqual(data[0]["new_state"], "GREEN")