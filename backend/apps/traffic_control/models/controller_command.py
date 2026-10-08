from django.db import models
from django.utils import timezone

from apps.traffic_control.domain.safety import Direction, SignalColor
from .junction import Junction


class CommandStatus(models.TextChoices):
    PENDING = "PENDING", "PENDING"
    ACK = "ACK", "ACK"
    TIMEOUT = "TIMEOUT", "TIMEOUT"
    FAILED = "FAILED", "FAILED"
    REJECTED = "REJECTED", "REJECTED"


class ControllerCommand(models.Model):
    """
    Represents an operational signal change instruction issued to physical IoT hardware.
    Enforces separation between:
      Desired State (What backend commanded) vs Actual State (What controller confirmed).
    """

    # Unique correlation identifier (e.g. 'cmd-8001') as specified in Section 9 & 13
    command_id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique correlation ID for matching controller ACKs (e.g., 'cmd-8001')",
    )

    # Associated junction target
    junction = models.ForeignKey(
        Junction,
        on_delete=models.CASCADE,
        related_name="controller_commands",
        help_text="Junction receiving the hardware signal command",
    )

    # Specific targeted direction, if applicable (e.g. 'EAST')
    direction = models.CharField(
        max_length=10,
        choices=[(d.value, d.value) for d in Direction],
        null=True,
        blank=True,
        help_text="Targeted lane approach for the command",
    )

    # State requested by backend domain engine (e.g. 'GREEN', 'YELLOW', 'RED')
    requested_state = models.CharField(
        max_length=10,
        choices=[(c.value, c.value) for c in SignalColor],
        null=True,
        blank=True,
        help_text="Desired signal color requested by backend",
    )

    # Complete snapshot of desired signals across all 4 directions
    desired_signals_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Full signal state vector sent to the controller",
    )

    # Current execution status of the command
    status = models.CharField(
        max_length=20,
        choices=CommandStatus.choices,
        default=CommandStatus.PENDING,
        db_index=True,
        help_text="Execution state: PENDING, ACK, TIMEOUT, FAILED",
    )

    # Physical state confirmed by hardware in the ACK response
    actual_state = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Confirmed signal state acknowledged by the controller",
    )

    # Retry tracking for IoT resilience
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retry attempts sent to controller",
    )

    # Timestamp tracking
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Time when the backend issued the command",
    )
    acked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Time when the controller ACK was ingested",
    )

    class Meta:
        db_table = "traffic_controller_commands"
        verbose_name = "Controller Command"
        verbose_name_plural = "Controller Commands"
        ordering = ["-created_at"]
        indexes = [
            # Optimized for finding pending commands to detect timeouts
            models.Index(fields=["junction", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.command_id} [{self.junction_id}] -> {self.requested_state} ({self.status})"

    @property
    def is_timed_out(self) -> bool:
        """Helper to determine if a pending command has exceeded timeout threshold (e.g. 5 seconds)."""
        if self.status != CommandStatus.PENDING:
            return False
        return (timezone.now() - self.created_at).total_seconds() > 5.0