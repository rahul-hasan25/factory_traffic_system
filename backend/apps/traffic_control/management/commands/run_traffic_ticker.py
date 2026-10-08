import logging
import signal
import sys
import time
from typing import List

from django.core.management.base import BaseCommand
from django.db import DatabaseError, InterfaceError, OperationalError, connection

from apps.traffic_control.models import Junction
from apps.traffic_control.services.state_service import StateService

logger = logging.getLogger("traffic_control.ticker")


class Command(BaseCommand):
    help = "Runs continuous background tick evaluations for traffic junctions."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=float,
            default=1.0,
            help="Tick interval in seconds (default: 1.0s).",
        )
        parser.add_argument(
            "--junctions",
            nargs="*",
            type=str,
            help="Specific junction IDs to monitor (e.g. --junctions A B). If omitted, monitors all.",
        )

    def handle(self, *args, **options):
        interval: float = options["interval"]
        junction_targets: List[str] = [j.upper() for j in (options.get("junctions") or [])]

        # Register graceful termination handlers (OS safe)
        signal.signal(signal.SIGINT, self._handle_termination)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._handle_termination)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting Factory Traffic Ticker [Interval: {interval}s]..."
            )
        )

        # 1. Startup Crash Recovery Routine (Section 12 Compliance)
        self._run_startup_recovery(junction_targets)

        # 2. Main Non-blocking Execution Loop
        while self._running:
            start_time = time.monotonic()

            try:
                # Close stale or idle connections before tick evaluation
                connection.close_if_unusable_or_obsolete()

                active_junctions = self._resolve_junction_ids(junction_targets)
                for junction_id in active_junctions:
                    if not self._running:
                        break

                    transitioned = StateService.evaluate_junction_tick(junction_id)
                    if transitioned:
                        self.stdout.write(
                            self.style.NOTICE(f"[{junction_id}] State transition triggered.")
                        )

            except (OperationalError, InterfaceError, DatabaseError) as db_err:
                logger.error("Database connection error during ticker loop: %s", db_err)
                self.stderr.write(self.style.ERROR(f"Database error: {db_err}"))
                time.sleep(2.0)  # Cool down before retrying connection
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Unexpected error in traffic ticker loop: %s", exc)
                self.stderr.write(self.style.ERROR(f"Ticker error: {exc}"))

            # Drift-corrected non-blocking sleep interval
            elapsed = time.monotonic() - start_time
            sleep_time = max(0.0, interval - elapsed)
            time.sleep(sleep_time)

        self.stdout.write(self.style.WARNING("Traffic Ticker stopped gracefully."))
        sys.exit(0)

    def _run_startup_recovery(self, junction_targets: List[str]) -> None:
        """Executes startup recovery to clear unconfirmed transition states safely."""
        self.stdout.write("Running startup crash recovery checks...")
        try:
            active_ids = self._resolve_junction_ids(junction_targets)
            if not active_ids and not junction_targets:
                # Seed default Junction A if completely empty (without invalid 'name' field)
                Junction.objects.get_or_create(
                    junction_id="A",
                    defaults={
                        "mode": "AUTOMATIC",
                        "current_phase": "NORTH_SOUTH",
                        "transition_step": "STABLE_GREEN",
                        "controller_status": "ONLINE",
                        "desired_signals": {
                            "NORTH": "GREEN",
                            "SOUTH": "GREEN",
                            "EAST": "RED",
                            "WEST": "RED",
                        },
                        "actual_signals": {
                            "NORTH": "GREEN",
                            "SOUTH": "GREEN",
                            "EAST": "RED",
                            "WEST": "RED",
                        },
                    },
                )
                active_ids = ["A"]

            for junction_id in active_ids:
                StateService.recover_junction_on_startup(junction_id)
                self.stdout.write(
                    self.style.SUCCESS(f"Junction '{junction_id}' recovered and verified.")
                )
        except Exception as exc:
            logger.error("Startup crash recovery encountered an error: %s", exc)
            self.stderr.write(self.style.ERROR(f"Recovery error: {exc}"))

    def _resolve_junction_ids(self, filter_ids: List[str]) -> List[str]:
        """Resolves target junction IDs from database."""
        if filter_ids:
            return list(
                Junction.objects.filter(junction_id__in=filter_ids)
                .values_list("junction_id", flat=True)
            )
        return list(Junction.objects.values_list("junction_id", flat=True).order_by("junction_id"))

    def _handle_termination(self, signum, frame):
        """Intercepts termination signals and triggers a graceful shutdown."""
        self.stdout.write(
            self.style.WARNING(f"\nReceived signal {signum}. Shutting down ticker loop safely...")
        )
        self._running = False