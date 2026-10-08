from django.db import models
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction
from apps.traffic_control.domain.scheduler import VehicleType
from .junction import Junction


class VehicleQueue(models.Model):
    junction = models.ForeignKey(
        Junction,
        on_delete=models.CASCADE,
        related_name="waiting_vehicles",
        help_text="Junction where the vehicle is queued",
    )

    # Road direction where the vehicle is waiting: NORTH, SOUTH, EAST, WEST
    direction = models.CharField(
        max_length=10,
        choices=[(d.value, d.value) for d in Direction],
        db_index=True,
        help_text="Direction lane of the queue",
    )

    # Physical vehicle registration tag (e.g., 'VH-501')
    vehicle_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Unique vehicle identification tag",
    )

    # Vehicle type classification for priority scoring
    vehicle_type = models.CharField(
        max_length=30,
        choices=[(v.value, v.value) for v in VehicleType],
        default=VehicleType.EMPLOYEE_VEHICLE.value,
        help_text="Vehicle category determining scheduling weight",
    )

    # Timestamp when vehicle arrived (from sensor event or ingestion)
    arrival_time = models.DateTimeField(
        help_text="Timestamp when vehicle entered the queue",
    )

    # Clearance state
    is_cleared = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True when VEHICLE_CLEARED event is received",
    )

    # Cleared timestamp for audit and delay metrics
    cleared_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the vehicle left the intersection",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "traffic_vehicle_queues"
        verbose_name = "Vehicle Queue Item"
        verbose_name_plural = "Vehicle Queue Items"
        ordering = ["arrival_time"]
        indexes = [
            # Composite index for ultra-fast active queue lookups and starvation checks
            models.Index(fields=["junction", "direction", "is_cleared", "arrival_time"]),
            models.Index(fields=["vehicle_id", "is_cleared"]),
        ]

    def __str__(self) -> str:
        status = "CLEARED" if self.is_cleared else "WAITING"
        return f"{self.vehicle_id} ({self.vehicle_type}) [{self.direction}] - {status}"

    @property
    def waiting_seconds(self) -> float:
        """Calculates current wait time in seconds for active vehicles."""
        if self.is_cleared and self.cleared_at:
            return (self.cleared_at - self.arrival_time).total_seconds()
        return max(0.0, (timezone.now() - self.arrival_time).total_seconds())