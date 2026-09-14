"""Image uploads for course covers and instructor photos."""

import mimetypes
import secrets
from datetime import date
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from neoskill.identity.access import IsAdmin

# Leading bytes of the formats we accept, so a renamed file cannot slip through.
SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"RIFF", "image/webp"),
)


def _detect(head: bytes) -> str | None:
    for prefix, content_type in SIGNATURES:
        if head.startswith(prefix):
            if content_type == "image/webp" and head[8:12] != b"WEBP":
                continue
            return content_type
    return None


def media_path(name: str) -> Path:
    """Resolves a stored name inside MEDIA_ROOT, refusing anything that escapes it."""
    root = Path(settings.MEDIA_ROOT).resolve()
    target = (root / name).resolve()
    if root != target and root not in target.parents:
        raise Http404
    return target


class AdminImageUploadView(APIView):
    permission_classes = [IsAdmin]
    # The rest of the API is JSON only; multipart is enabled just for this endpoint.
    parser_classes = [MultiPartParser]
    http_method_names = ["post", "options"]

    def post(self, request: Request) -> Response:
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Rasm fayli yuborilmadi."}, status=400)
        if upload.size > settings.UPLOAD_MAX_BYTES:
            limit = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
            return Response(
                {"detail": f"Fayl juda katta. Ruxsat etilgan eng katta hajm — {limit} MB."},
                status=400,
            )

        head = upload.read(16)
        upload.seek(0)
        content_type = _detect(head)
        if content_type is None:
            return Response(
                {"detail": "Faqat JPG, PNG yoki WebP rasm yuklash mumkin."},
                status=400,
            )

        folder = Path(settings.MEDIA_ROOT) / date.today().strftime("%Y/%m")
        name = f"{secrets.token_urlsafe(16)}{settings.UPLOAD_ALLOWED_TYPES[content_type]}"
        destination = folder / name
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as target:
                for chunk in upload.chunks():
                    target.write(chunk)
        except OSError:
            # A misconfigured or unwritable MEDIA_ROOT is an operator problem, not a bad request.
            return Response(
                {
                    "detail": (
                        "Serverda rasm saqlash papkasiga yozib bo‘lmadi. "
                        "MEDIA_ROOT sozlamasini tekshiring."
                    )
                },
                status=503,
            )

        relative = destination.relative_to(Path(settings.MEDIA_ROOT)).as_posix()
        return Response(
            {"url": f"{settings.MEDIA_URL}{relative}", "content_type": content_type},
            status=201,
        )


class MediaFileView(APIView):
    """
    Serves uploaded images.

    Django is not an efficient file server: put a CDN or nginx in front of
    /api/v1/media/ before real traffic. Keeping it here means uploads work with
    no extra infrastructure and stay same-origin behind the frontend proxy.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []
    http_method_names = ["get", "head", "options"]

    def get(self, request: Request, path: str) -> FileResponse:
        target = media_path(path)
        if not target.is_file():
            raise Http404
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        response = FileResponse(target.open("rb"), content_type=content_type)
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
