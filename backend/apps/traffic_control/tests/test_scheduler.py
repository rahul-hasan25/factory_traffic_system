from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import PriorityScheduler, VehicleType
from apps.traffic_control.models import Junction, VehicleQueue


class SchedulerPriorityTestCase(TestCase):
    def setUp(self):
        self.junction = Junction.objects.create(junction_id="J-SCHED")

    def test_emergency_vehicle_highest_priority(self):
        """An emergency vehicle on WEST overrides high volume on NORTH."""
        # 5 Employee vehicles waiting on NORTH
        for i in range(5):
            VehicleQueue.objects.create(
                junction=self.junction,
                direction=Direction.NORTH.value,
                vehicle_id=f"EMP-{i}",
                vehicle_type=VehicleType.EMPLOYEE_VEHICLE.value,
                arrival_time=timezone.now(),
            )

        # 1 Emergency vehicle arriving on WEST
        VehicleQueue.objects.create(
            junction=self.junction,
            direction=Direction.WEST.value,
            vehicle_id="EMG-999",
            vehicle_type=VehicleType.EMERGENCY.value,
            arrival_time=timezone.now(),
        )

        chosen_phase = PriorityScheduler.select_next_phase(self.junction)
        self.assertIn("WEST", chosen_phase)

    def test_starvation_prevention_boost(self):
        """A vehicle waiting longer than 60s receives starvation priority boost."""
        # 1 Employee vehicle on EAST waiting for 65 seconds
        VehicleQueue.objects.create(
            junction=self.junction,
            direction=Direction.EAST.value,
            vehicle_id="STARVED-1",
            vehicle_type=VehicleType.EMPLOYEE_VEHICLE.value,
            arrival_time=timezone.now() - timedelta(seconds=65),
        )

        # 2 Trucks just arrived on NORTH
        for i in range(2):
            VehicleQueue.objects.create(
                junction=self.junction,
                direction=Direction.NORTH.value,
                vehicle_id=f"TRK-{i}",
                vehicle_type=VehicleType.TRUCK.value,
                arrival_time=timezone.now() - timedelta(seconds=5),
            )

        chosen_phase = PriorityScheduler.select_next_phase(self.junction)
        self.assertIn("EAST", chosen_phase)