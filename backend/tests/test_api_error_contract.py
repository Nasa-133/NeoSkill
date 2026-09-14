from django.db import IntegrityError
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path
from rest_framework.views import APIView

from neoskill.identity.access import IsGuest


class ConstraintProbe(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        raise IntegrityError("private SQL constraint detail")


class UnknownProbe(APIView):
    permission_classes = [IsGuest]

    def get(self, request):
        raise RuntimeError("private runtime detail")


class ValidationProbe(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        from rest_framework.exceptions import ValidationError

        raise ValidationError({"phone": "Verified phone is required."})


urlpatterns = [
    path("constraint", ConstraintProbe.as_view()),
    path("unknown", UnknownProbe.as_view()),
    path("validation", ValidationProbe.as_view()),
]


@override_settings(ROOT_URLCONF=__name__)
class APIErrorContractTests(SimpleTestCase):
    def test_database_constraint_error_is_safe_json_conflict(self):
        response = Client(raise_request_exception=False).post(
            "/constraint", {}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json(), {"detail": "Request conflicts with existing data."})
        self.assertNotContains(response, "private SQL", status_code=409)

    def test_unknown_api_error_is_safe_json(self):
        response = Client(raise_request_exception=False).get("/unknown")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal server error."})
        self.assertNotContains(response, "private runtime", status_code=500)

    def test_actionable_field_validation_is_preserved(self):
        response = self.client.post("/validation", {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"phone": "Verified phone is required."})


def test_csrf_rejection_answers_in_json():
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        "/api/v1/auth/login",
        data={"email": "a@example.com", "password": "Str0ng-Passw0rd!"},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response["Content-Type"].startswith("application/json")
    assert response.json()["code"] == "csrf_failed"
