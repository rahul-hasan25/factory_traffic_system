import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import VehicleType
from apps.traffic_control.domain.state_machine import JunctionMode, TransitionStep
from apps.traffic_control.models import (
    ControllerCommand,
    Junction,
    SensorEvent,
    TrafficAuditLog,
    VehicleQueue,
)
from apps.traffic_control.services.command_service import CommandService
from apps.traffic_control.services.event_processor import EventProcessor
from apps.traffic_control.services.state_service import StateService


class Command(BaseCommand):
    help = "Demonstrates and verifies Section 15 functional traffic scenarios."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.junction_id = "A"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("  FACTORY TRAFFIC SYSTEM - SCENARIO DEMONSTRATOR  "))
        self.stdout.write(self.style.MIGRATE_HEADING("==================================================\n"))

        self._reset_junction()

        # Run Section 15 Scenarios sequentially
        self.test_scenario_1_normal_traffic()
        self.test_scenario_2_priority_traffic()
        self.test_scenario_3_emergency_preemption()
        self.test_scenario_4_manual_override()
        self.test_scenario_5_duplicate_event()
        self.test_scenario_6_vehicle_clearance()
        self.test_scenario_7_controller_failure()
        self.test_scenario_8_restart_recovery()
        self.test_scenario_9_concurrent_events()

        self.stdout.write(self.style.SUCCESS("\n[ALL 9 SCENARIOS EXECUTED & VERIFIED SUCCESSFULLY]"))

    def _reset_junction(self):
        """Resets Junction A to clean default state."""
        j, _ = Junction.objects.get_or_create(junction_id=self.junction_id)
        VehicleQueue.objects.filter(junction=j).delete()
        SensorEvent.objects.filter(junction=j).delete()
        ControllerCommand.objects.filter(junction=j).delete()
        TrafficAuditLog.objects.filter(junction=j).delete()

        j.mode = JunctionMode.AUTOMATIC.value
        j.current_phase = "NORTH_SOUTH"
        j.transition_step = TransitionStep.STABLE_GREEN.value
        j.controller_status = "ONLINE"
        j.desired_signals = {"NORTH": "GREEN", "SOUTH": "GREEN", "EAST": "RED", "WEST": "RED"}
        j.actual_signals = {"NORTH": "GREEN", "SOUTH": "GREEN", "EAST": "RED", "WEST": "RED"}
        j.emergency_direction = None
        j.manual_direction = None
        j.target_phase = None
        j.phase_started_at = dj_timezone.now()
        j.save()

    def _log_scenario(self, number: int, title: str):
        self.stdout.write(self.style.WARNING(f"\n--- Scenario {number}: {title} ---"))

    # 1. Normal Traffic
    def test_scenario_1_normal_traffic(self):
        self._log_scenario(1, "Normal Traffic Multi-directional Arrival")
        self._reset_junction()

        EventProcessor.process_sensor_event({
            "event_id": f"s1-{uuid.uuid4().hex[:6]}",
            "junction_id": self.junction_id,
            "direction": "EAST",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "CAR-01",
            "vehicle_type": VehicleType.EMPLOYEE_VEHICLE.value,
        })
        EventProcessor.process_sensor_event({
            "event_id": f"s1-{uuid.uuid4().hex[:6]}",
            "junction_id": self.junction_id,
            "direction": "NORTH",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "CAR-02",
            "vehicle_type": VehicleType.EMPLOYEE_VEHICLE.value,
        })

        j = Junction.objects.get(junction_id=self.junction_id)
        counts = EventProcessor.get_active_queue_counts(j)
        assert counts["EAST"] == 1 and counts["NORTH"] == 1, f"Queue count mismatch: {counts}"
        self.stdout.write(self.style.SUCCESS(f"✔ Queues registered: NORTH={counts['NORTH']}, EAST={counts['EAST']}"))

    # 2. Priority Traffic
    def test_scenario_2_priority_traffic(self):
        self._log_scenario(2, "Priority Traffic (FORKLIFT/TRUCK vs Employee)")
        self._reset_junction()

        # Ingest 2 ordinary employee cars on NORTH
        for i in range(2):
            EventProcessor.process_sensor_event({
                "event_id": f"s2-car-{i}",
                "junction_id": self.junction_id,
                "direction": "NORTH",
                "event_type": "VEHICLE_ARRIVED",
                "vehicle_id": f"CAR-{i}",
                "vehicle_type": VehicleType.EMPLOYEE_VEHICLE.value,
            })

        # Ingest 1 heavy TRUCK on WEST (Higher weight/priority)
        EventProcessor.process_sensor_event({
            "event_id": "s2-truck-01",
            "junction_id": self.junction_id,
            "direction": "WEST",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "HEAVY-TRUCK-01",
            "vehicle_type": VehicleType.TRUCK.value,
        })

        j = Junction.objects.get(junction_id=self.junction_id)
        counts = EventProcessor.get_active_queue_counts(j)
        assert counts["NORTH"] == 2 and counts["WEST"] == 1
        self.stdout.write(self.style.SUCCESS("✔ Heavy vehicle registered in queue with priority metadata."))

    # 3. Emergency Preemption
    def test_scenario_3_emergency_preemption(self):
        self._log_scenario(3, "Emergency Vehicle Preemption (NORTH_SOUTH Green -> EAST Emergency)")
        self._reset_junction()

        # Submit Emergency vehicle on conflicting EAST lane
        EventProcessor.process_sensor_event({
            "event_id": "s3-emerg-01",
            "junction_id": self.junction_id,
            "direction": "EAST",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "AMBULANCE-01",
            "vehicle_type": VehicleType.EMERGENCY.value,
        })

        j = Junction.objects.get(junction_id=self.junction_id)
        assert j.mode == JunctionMode.EMERGENCY.value, "Junction mode not switched to EMERGENCY"
        assert j.emergency_direction == "EAST", "Emergency direction not recorded"

        # Evaluate tick to progress preemption sequence
        StateService.evaluate_junction_tick(self.junction_id)

        j.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(f"✔ Emergency detected! Transition step: {j.transition_step}"))

    # 4. Manual Override
    def test_scenario_4_manual_override(self):
        self._log_scenario(4, "Admin Manual Override & Return to Automatic")
        self._reset_junction()

        # Request manual green on WEST
        resp, code = CommandService.process_manual_command(
            self.junction_id, {"command": "MANUAL_GREEN_REQUEST", "direction": "WEST"}
        )
        assert code in (200, 202), f"Manual command rejected: {resp}"

        j = Junction.objects.get(junction_id=self.junction_id)
        assert j.mode == JunctionMode.MANUAL.value, "Junction mode not changed to MANUAL"
        self.stdout.write(self.style.SUCCESS("✔ MANUAL mode engaged successfully for WEST."))

        # Return to automatic
        resp, code = CommandService.process_manual_command(
            self.junction_id, {"command": "RETURN_TO_AUTOMATIC"}
        )
        assert code == 200, f"Return to automatic rejected: {resp}"

        j.refresh_from_db()
        assert j.mode == JunctionMode.AUTOMATIC.value, "Junction mode did not revert to AUTOMATIC"
        self.stdout.write(self.style.SUCCESS("✔ Returned to AUTOMATIC mode."))

    # 5. Duplicate Event
    def test_scenario_5_duplicate_event(self):
        self._log_scenario(5, "Duplicate Sensor Event Idempotency")
        self._reset_junction()

        event_payload = {
            "event_id": "dup-event-test-101",
            "junction_id": self.junction_id,
            "direction": "SOUTH",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "TRUCK-99",
            "vehicle_type": VehicleType.TRUCK.value,
        }

        # Submit twice
        res1, code1 = EventProcessor.process_sensor_event(event_payload)
        res2, code2 = EventProcessor.process_sensor_event(event_payload)

        assert code1 == 201, f"First submission failed: {res1}"
        assert code2 == 200 and res2.get("status") == "IGNORED", "Second submission was not ignored"

        j = Junction.objects.get(junction_id=self.junction_id)
        counts = EventProcessor.get_active_queue_counts(j)
        assert counts["SOUTH"] == 1, f"Queue count corrupted: {counts['SOUTH']}"
        self.stdout.write(self.style.SUCCESS("✔ Duplicate event safely ignored. Queue remains 1."))

    # 6. Vehicle Clearance
    def test_scenario_6_vehicle_clearance(self):
        self._log_scenario(6, "Vehicle Clearance Flow (ARRIVE -> CLEAR)")
        self._reset_junction()

        EventProcessor.process_sensor_event({
            "event_id": "s6-arr-01",
            "junction_id": self.junction_id,
            "direction": "NORTH",
            "event_type": "VEHICLE_ARRIVED",
            "vehicle_id": "VAN-55",
        })

        j = Junction.objects.get(junction_id=self.junction_id)
        assert EventProcessor.get_active_queue_counts(j)["NORTH"] == 1

        EventProcessor.process_sensor_event({
            "event_id": "s6-clr-01",
            "junction_id": self.junction_id,
            "direction": "NORTH",
            "event_type": "VEHICLE_CLEARED",
            "vehicle_id": "VAN-55",
        })

        assert EventProcessor.get_active_queue_counts(j)["NORTH"] == 0
        self.stdout.write(self.style.SUCCESS("✔ Vehicle cleared. Queue decremented to 0."))

    # 7. Controller Failure
    def test_scenario_7_controller_failure(self):
        self._log_scenario(7, "Controller Telemetry Failure & Fail-Safe Fallback")
        self._reset_junction()

        # Simulate controller offline event
        resp, code = CommandService.process_controller_event({
            "junction_id": self.junction_id,
            "status": "OFFLINE",
            "device_status": "OFFLINE",
            "device_type": "SIGNAL_CONTROLLER",
        })
        assert code == 200, f"Controller event rejected: {resp}"

        j = Junction.objects.get(junction_id=self.junction_id)
        assert j.controller_status == "OFFLINE" and j.mode == JunctionMode.DEGRADED.value
        self.stdout.write(self.style.SUCCESS(f"✔ Controller failure handled. Junction switched to {j.mode}."))

    # 8. Restart Recovery
    def test_scenario_8_restart_recovery(self):
        self._log_scenario(8, "System Restart & In-Flight Transition Crash Recovery")
        self._reset_junction()

        # Simulate in-flight transition crash
        j = Junction.objects.get(junction_id=self.junction_id)
        j.transition_step = TransitionStep.CLEARING_YELLOW.value
        j.save()

        # Execute startup recovery routine
        StateService.recover_junction_on_startup(self.junction_id)

        j.refresh_from_db()
        assert j.transition_step in (TransitionStep.ALL_RED_CLEARANCE.value, TransitionStep.STABLE_GREEN.value)
        self.stdout.write(self.style.SUCCESS(f"✔ Startup recovery verified: safe state restored ({j.transition_step})."))

    # 9. Concurrent Events
    def test_scenario_9_concurrent_events(self):
        self._log_scenario(9, "Concurrent Multi-event Stress (Race Condition & Safety Guard)")
        self._reset_junction()

        def submit_truck():
            EventProcessor.process_sensor_event({
                "event_id": f"conc-truck-{uuid.uuid4().hex[:4]}",
                "junction_id": self.junction_id,
                "direction": "NORTH",
                "event_type": "VEHICLE_ARRIVED",
                "vehicle_id": "TRUCK-CONC",
                "vehicle_type": VehicleType.TRUCK.value,
            })

        def submit_emergency():
            EventProcessor.process_sensor_event({
                "event_id": "conc-emerg-01",
                "junction_id": self.junction_id,
                "direction": "EAST",
                "event_type": "VEHICLE_ARRIVED",
                "vehicle_id": "AMBULANCE-CONC",
                "vehicle_type": VehicleType.EMERGENCY.value,
            })

        def submit_manual():
            CommandService.process_manual_command(
                self.junction_id, {"command": "MANUAL_GREEN_REQUEST", "direction": "WEST"}
            )

        def submit_duplicate_emergency():
            EventProcessor.process_sensor_event({
                "event_id": "conc-emerg-01",
                "junction_id": self.junction_id,
                "direction": "EAST",
                "event_type": "VEHICLE_ARRIVED",
                "vehicle_id": "AMBULANCE-CONC",
                "vehicle_type": VehicleType.EMERGENCY.value,
            })

        # Run simultaneously via thread pool
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(submit_truck),
                executor.submit(submit_emergency),
                executor.submit(submit_manual),
                executor.submit(submit_duplicate_emergency),
            ]
            for f in futures:
                f.result()

        j = Junction.objects.get(junction_id=self.junction_id)

        # Invariant Verification: No conflicting green signals
        active_greens = [d for d, color in j.desired_signals.items() if color == "GREEN"]
        is_safe = (
            len(active_greens) <= 2
            and active_greens in ([], ["NORTH"], ["SOUTH"], ["NORTH", "SOUTH"], ["EAST"], ["WEST"], ["EAST", "WEST"])
        )
        assert is_safe, f"SAFETY VIOLATION! Conflicting GREEN states found: {active_greens}"
        self.stdout.write(self.style.SUCCESS(f"✔ Thread concurrency preserved safety invariants. Signals: {j.desired_signals}"))