from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.utils import DatabaseError
from django.utils.connection import ConnectionDoesNotExist
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        return Response(
            {"status": "ok", "service": "neoskill-backend"},
            headers={"Cache-Control": "no-store"},
        )


class ReadinessView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request) -> Response:
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except (ConnectionDoesNotExist, DatabaseError, ImproperlyConfigured):
            return Response(
                {"status": "unavailable", "service": "neoskill-backend"},
                status=503,
                headers={"Cache-Control": "no-store"},
            )
        return Response(
            {"status": "ready", "service": "neoskill-backend"},
            headers={"Cache-Control": "no-store"},
        )
