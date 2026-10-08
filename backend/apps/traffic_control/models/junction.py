from django.db import models
from django.utils import timezone
from apps.traffic_control.domain.safety import (DEFAULT_JUNCTION_CONFIG, Direction, JunctionConfiguration, SignalColor, TrafficPhase)
from apps.traffic_control.domain.state_machine import JunctionMode, TransitionStep


def default_signal_state() -> dict:
    return {
        Direction.NORTH.value: SignalColor.RED.value,
        Direction.SOUTH.value: SignalColor.RED.value,
        Direction.EAST.value: SignalColor.EAST.value if hasattr(SignalColor, "EAST") else SignalColor.RED.value,
        Direction.WEST.value: SignalColor.RED.value,
    }


def get_default_signals() -> dict:
    return {
        Direction.NORTH.value: SignalColor.RED.value,
        Direction.SOUTH.value: SignalColor.RED.value,
        Direction.EAST.value: SignalColor.RED.value,
        Direction.WEST.value: SignalColor.RED.value,
    }


class Junction(models.Model):
    class ControllerStatus(models.TextChoices):
        ONLINE = "ONLINE", "ONLINE"
        OFFLINE = "OFFLINE", "OFFLINE"
        DEGRADED = "DEGRADED", "DEGRADED"

    junction_id = models.CharField(max_length=20, primary_key=True)
    mode = models.CharField(max_length=20, choices=[(m.value, m.value) for m in JunctionMode], default=JunctionMode.AUTOMATIC.value, db_index=True)
    current_phase = models.CharField(max_length=30, choices=[(p.value, p.value) for p in TrafficPhase], default=TrafficPhase.ALL_RED.value)
    transition_step = models.CharField(max_length=30, choices=[(t.value, t.value) for t in TransitionStep], default=TransitionStep.ALL_RED_CLEARANCE.value)
    controller_status = models.CharField(max_length=20, choices=ControllerStatus.choices, default=ControllerStatus.ONLINE)
    desired_signals = models.JSONField(default=get_default_signals)
    actual_signals = models.JSONField(default=get_default_signals)
    topology_config = models.JSONField(null=True, blank=True)
    target_phase = models.CharField(max_length=30, choices=[(p.value, p.value) for p in TrafficPhase], null=True, blank=True)
    manual_direction = models.CharField(max_length=10, choices=[(d.value, d.value) for d in Direction], null=True, blank=True)
    emergency_direction = models.CharField(max_length=10, choices=[(d.value, d.value) for d in Direction], null=True, blank=True)
    phase_started_at = models.DateTimeField(default=timezone.now)
    last_controller_seen_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "traffic_junctions"
        verbose_name = "Traffic Junction"
        verbose_name_plural = "Traffic Junctions"

    def __str__(self) -> str:
        return f"Junction {self.junction_id} [{self.mode} | {self.current_phase} | {self.transition_step}]"

    @property
    def has_signal_mismatch(self) -> bool:
        return self.desired_signals != self.actual_signals

    def get_domain_config(self) -> JunctionConfiguration:
        if not self.topology_config:
            return DEFAULT_JUNCTION_CONFIG
        try:
            # Parse dynamic topology JSON if defined
            phase_dirs = {}
            for phase_name, dirs in self.topology_config.get("phase_directions", {}).items():
                phase_dirs[TrafficPhase(phase_name)] = {Direction(d) for d in dirs}

            conflict_pairs = frozenset({
                frozenset({Direction(p[0]), Direction(p[1])})
                for p in self.topology_config.get("conflict_pairs", [])
            })

            return JunctionConfiguration(
                phase_directions=phase_dirs or DEFAULT_JUNCTION_CONFIG.phase_directions,
                conflict_pairs=conflict_pairs or DEFAULT_JUNCTION_CONFIG.conflict_pairs,
            )
        except Exception:
            return DEFAULT_JUNCTION_CONFIG