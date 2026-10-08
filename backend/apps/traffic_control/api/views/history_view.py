from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.traffic_control.api.serializers import TrafficHistorySerializer
from apps.traffic_control.models import Junction, TrafficAuditLog


class JunctionHistoryAPIView(APIView):
    """
    Endpoint: GET /api/junctions/:id/history
    Returns chronological audit history and signal state transitions for a junction.
    Supports optional query parameters:
      - limit: Maximum number of records to return (default: 50, max: 200).
      - event_type: Filter by specific audit event classification.
    """

    def get(self, request: Request, junction_id: str) -> Response:
        normalized_id = junction_id.strip().upper()

        try:
            junction = Junction.objects.get(junction_id=normalized_id)
        except Junction.DoesNotExist:
            return Response(
                {
                    "error": "NOT_FOUND",
                    "message": f"Junction '{normalized_id}' not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = TrafficAuditLog.objects.filter(junction=junction).order_by("-timestamp")

        # Optional filter by event_type
        event_type = request.query_params.get("event_type")
        if event_type:
            queryset = queryset.filter(event_type=event_type.strip().upper())

        # Pagination / limit slicing
        try:
            limit = int(request.query_params.get("limit", 50))
            limit = max(1, min(limit, 200))
        except ValueError:
            limit = 50

        logs = queryset[:limit]
        serializer = TrafficHistorySerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)