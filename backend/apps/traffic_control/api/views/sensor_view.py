from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.traffic_control.api.serializers import SensorEventSerializer
from apps.traffic_control.services import EventProcessor


class SensorEventAPIView(APIView):
    """
    Endpoint: POST /api/sensor-events
    Ingests vehicle sensor events emitted by physical or simulated edge sensors.
    Guarantees idempotency and safe transactional state mutations.
    """

    def post(self, request: Request) -> Response:
        serializer = SensorEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "REJECTED",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delegate business logic and concurrency locking to EventProcessor service
        result_data, http_status = EventProcessor.process_sensor_event(
            serializer.validated_data
        )

        return Response(result_data, status=http_status)