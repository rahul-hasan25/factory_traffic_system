from django.urls import path

from apps.traffic_control.api.views import (
    ControllerEventAPIView,
    JunctionCommandAPIView,
    JunctionDetailAPIView,
    JunctionHistoryAPIView,
    JunctionListCreateAPIView,
    JunctionStatusAPIView,
    SensorEventAPIView,
)

urlpatterns = [
    # 10.1 Junctions: List & Create
    path("junctions", JunctionListCreateAPIView.as_view(), name="junction-list-create"),
    path("junctions/", JunctionListCreateAPIView.as_view(), name="junction-list-create-slash"),

    # 10.1 Junctions: Individual Detail (GET /api/junctions/:id)
    path("junctions/<str:junction_id>", JunctionDetailAPIView.as_view(), name="junction-detail"),
    path("junctions/<str:junction_id>/", JunctionDetailAPIView.as_view(), name="junction-detail-slash"),

    # 10.3 Junction Status (GET /api/junctions/:id/status)
    path("junctions/<str:junction_id>/status", JunctionStatusAPIView.as_view(), name="junction-status"),
    path("junctions/<str:junction_id>/status/", JunctionStatusAPIView.as_view(), name="junction-status-slash"),

    # 10.4 Administrative Control Commands (POST /api/junctions/:id/commands)
    path("junctions/<str:junction_id>/commands", JunctionCommandAPIView.as_view(), name="junction-command"),
    path("junctions/<str:junction_id>/commands/", JunctionCommandAPIView.as_view(), name="junction-command-slash"),

    # 10.6 History (GET /api/junctions/:id/history)
    path("junctions/<str:junction_id>/history", JunctionHistoryAPIView.as_view(), name="junction-history"),
    path("junctions/<str:junction_id>/history/", JunctionHistoryAPIView.as_view(), name="junction-history-slash"),

    # 10.2 Inbound IoT Edge Sensor Telemetry (POST /api/sensor-events)
    path("sensor-events", SensorEventAPIView.as_view(), name="sensor-events"),
    path("sensor-events/", SensorEventAPIView.as_view(), name="sensor-events-slash"),

    # 10.5 Controller Events & ACKs (POST /api/controller-events)
    path("controller-events", ControllerEventAPIView.as_view(), name="controller-events"),
    path("controller-events/", ControllerEventAPIView.as_view(), name="controller-events-slash"),
]