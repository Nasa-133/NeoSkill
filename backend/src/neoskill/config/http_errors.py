from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.http import HttpRequest, JsonResponse
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exception: Exception, context: dict[str, object]) -> Response:
    response = exception_handler(exception, context)
    if response is not None:
        return response
    if isinstance(exception, ProtectedError):
        return Response(
            {"detail": "Resource is in use and cannot be deleted."},
            status=409,
        )
    if isinstance(exception, IntegrityError):
        return Response(
            {"detail": "Request conflicts with existing data."},
            status=409,
        )
    return Response({"detail": "Internal server error."}, status=500)


def bad_request(request: HttpRequest, exception: Exception) -> JsonResponse:
    return JsonResponse({"detail": "Bad request."}, status=400)


def permission_denied(request: HttpRequest, exception: Exception) -> JsonResponse:
    return JsonResponse({"detail": "Permission denied."}, status=403)


def not_found(request: HttpRequest, exception: Exception) -> JsonResponse:
    return JsonResponse({"detail": "Not found."}, status=404)


def server_error(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"detail": "Internal server error."}, status=500)


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    """The API answers in JSON everywhere, including CSRF rejections."""
    return JsonResponse(
        {
            "detail": (
                "So‘rov xavfsizlik tekshiruvidan o‘tmadi. Sahifani yangilab qayta urinib ko‘ring. "
                "Muammo davom etsa, saytga kirayotgan manzilingiz CORS_ALLOWED_ORIGINS ro‘yxatida "
                "borligini tekshiring."
            ),
            "code": "csrf_failed",
        },
        status=403,
    )
