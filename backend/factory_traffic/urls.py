from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({"status": "healthy", "service": "factory-traffic-backend"})

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Root health check endpoint
    path("health/", health_check, name="health-check"),
    
    # Central traffic management REST API endpoints mounted at /api/
    path("api/", include("apps.traffic_control.api.urls")),
]
