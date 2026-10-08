from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.traffic_control.api.serializers import ControllerEventSerializer
from apps.traffic_control.services import CommandService


class ControllerEventAPIView(APIView):
    """
    Endpoint: POST /api/controller-events
    Ingests execution acknowledgements (ACK) and telemetry emitted by edge controllers.
    Ensures distinction between desired state and confirmed physical state.
    """

    def post(self, request: Request) -> Response:
        serializer = ControllerEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "REJECTED",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delegate hardware reconciliation and status updates to CommandService
        result_data, http_status = CommandService.process_controller_event(
            payload=serializer.validated_data
        )

        return Response(result_data, status=http_status)