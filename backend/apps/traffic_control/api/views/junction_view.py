from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.traffic_control.api.serializers import (
    JunctionCreateSerializer,
    JunctionListSerializer,
    JunctionStatusSerializer,
)
from apps.traffic_control.models import Junction


class JunctionListCreateAPIView(APIView):
    def get(self, request: Request) -> Response:
        junctions = Junction.objects.all().order_by("junction_id")
        serializer = JunctionListSerializer(junctions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = JunctionCreateSerializer(data=request.data)
        if serializer.is_valid():
            junction = serializer.save()
            # Return standard representation for newly created junction
            status_serializer = JunctionStatusSerializer(junction)
            return Response(status_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JunctionDetailAPIView(APIView):
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

        serializer = JunctionListSerializer(junction)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JunctionStatusAPIView(APIView):
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

        serializer = JunctionStatusSerializer(junction)
        return Response(serializer.data, status=status.HTTP_200_OK)