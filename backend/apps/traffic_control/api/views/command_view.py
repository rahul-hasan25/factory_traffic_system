from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.traffic_control.api.serializers import JunctionCommandSerializer
from apps.traffic_control.services import CommandService


class JunctionCommandAPIView(APIView):
    def post(self, request: Request, junction_id: str) -> Response:
        normalized_id = junction_id.strip().upper()

        serializer = JunctionCommandSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "status": "REJECTED",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delegate execution safely to CommandService
        result_data, http_status = CommandService.process_manual_command(
            junction_id=normalized_id,
            payload=serializer.validated_data,
        )

        return Response(result_data, status=http_status)