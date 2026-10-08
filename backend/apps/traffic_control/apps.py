from django.apps import AppConfig


class TrafficControlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.traffic_control"
    verbose_name = "Factory Traffic Control"

    def ready(self) -> None:
        pass