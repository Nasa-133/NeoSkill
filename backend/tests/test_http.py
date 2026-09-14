import json
from pathlib import Path

from django.http import HttpResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path
from jsonschema import validate
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.config import http_errors


class PrivateProbe(APIView):
    def get(self, request):
        return Response({"protected": True})


def explode(request):
    raise RuntimeError("private-database-password-must-not-leak")


def forbidden(request):
    from django.core.exceptions import PermissionDenied

    raise PermissionDenied("private-permission-detail")


urlpatterns = [
    path("private", PrivateProbe.as_view()),
    path("explode", explode),
    path("forbidden", forbidden),
]
handler403 = http_errors.permission_denied
handler500 = http_errors.server_error


class HttpTests(SimpleTestCase):
    # SimpleTestCase rejects accidental database queries.
    def test_liveness_matches_the_public_contract_without_database(self):
        contract = json.loads((Path(__file__).parents[1] / "openapi.json").read_text())
        url = "/api/v1/health"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        schema = contract["paths"][url]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]
        validate(response.json(), schema)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertNotIn("Set-Cookie", response)

    def test_missing_route_and_disallowed_method_are_json(self):
        response = self.client.get("/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not found."})
        response = self.client.post("/api/v1/health", {}, content_type="application/json")
        self.assertEqual(response.status_code, 405)
        self.assertIn("detail", response.json())

    def test_invalid_host_is_rejected_without_leaking_details(self):
        response = self.client.get("/api/v1/health", HTTP_HOST="attacker.example")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Bad request."})

    def test_cors_allows_only_configured_origins_with_session_credentials(self):
        response = self.client.get("/api/v1/health", HTTP_ORIGIN="http://localhost:3000")
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:3000")
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")
        response = self.client.get("/api/v1/health", HTTP_ORIGIN="https://attacker.example")
        self.assertNotIn("Access-Control-Allow-Origin", response)

    @override_settings(ROOT_URLCONF=__name__)
    def test_new_api_views_are_private_by_default(self):
        response = self.client.get("/private")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("protected", response.json())

    @override_settings(ROOT_URLCONF=__name__)
    def test_unhandled_errors_and_permission_errors_have_safe_json(self):
        response = Client(raise_request_exception=False).get("/explode")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error."})
        response = self.client.get("/forbidden")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Permission denied."})

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_liveness_remains_available_behind_tls_termination(self):
        response: HttpResponse = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
