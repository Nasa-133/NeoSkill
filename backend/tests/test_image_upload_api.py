import io

import pytest
from rest_framework.test import APIClient

from neoskill.identity.models import User

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64


def upload(client: APIClient, data: bytes, name: str = "cover.png") -> object:
    return client.post(
        "/api/v1/admin/uploads/image",
        {"file": io.BytesIO(data)},
        format="multipart",
        HTTP_CONTENT_DISPOSITION=f'attachment; filename="{name}"',
    )


def admin_client(tmp_media) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=User.objects.create_superuser("upload@example.com"))
    return client


@pytest.fixture
def tmp_media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def test_only_admins_can_upload(tmp_media):
    assert upload(APIClient(), PNG).status_code in {401, 403}
    student = APIClient()
    student.force_authenticate(user=User.objects.create_user(email="s@example.com"))
    assert upload(student, PNG).status_code == 403


@pytest.mark.parametrize(("data", "extension"), [(PNG, ".png"), (JPEG, ".jpg"), (WEBP, ".webp")])
def test_supported_formats_are_stored_and_served(tmp_media, data, extension):
    client = admin_client(tmp_media)
    response = upload(client, data)

    assert response.status_code == 201, response.json()
    url = response.json()["url"]
    assert url.startswith("/api/v1/media/")
    assert url.endswith(extension)

    served = client.get(url)
    assert served.status_code == 200
    assert b"".join(served.streaming_content) == data


def test_a_renamed_non_image_is_rejected(tmp_media):
    client = admin_client(tmp_media)
    response = upload(client, b"#!/bin/sh\nrm -rf /\n", name="evil.png")
    assert response.status_code == 400
    assert "JPG" in response.json()["detail"]


def test_an_oversized_file_is_rejected(tmp_media, settings):
    settings.UPLOAD_MAX_BYTES = 128
    client = admin_client(tmp_media)
    response = upload(client, PNG + b"\x00" * 512)
    assert response.status_code == 400
    assert "katta" in response.json()["detail"]


def test_a_missing_file_is_rejected(tmp_media):
    client = admin_client(tmp_media)
    response = client.post("/api/v1/admin/uploads/image", {}, format="multipart")
    assert response.status_code == 400


def test_media_path_cannot_escape_the_upload_root(tmp_media):
    client = admin_client(tmp_media)
    assert client.get("/api/v1/media/../../etc/passwd").status_code == 404
    assert client.get("/api/v1/media/missing.png").status_code == 404


def test_an_unwritable_upload_root_reports_a_service_error(tmp_media, settings):
    settings.MEDIA_ROOT = "/proc/neoskill-cannot-write-here"
    client = admin_client(tmp_media)
    response = upload(client, PNG)
    assert response.status_code == 503
    assert "MEDIA_ROOT" in response.json()["detail"]


def test_a_relative_upload_path_can_be_saved_on_a_course(tmp_media):
    from neoskill.catalog.models import Category, Course, Instructor

    client = admin_client(tmp_media)
    uploaded = upload(client, PNG).json()["url"]
    assert uploaded.startswith("/api/v1/media/")

    category = Category.objects.create(name="C", slug="c")
    instructor = Instructor.objects.create(name="I", slug="i")
    course = Course.objects.create(
        category=category,
        instructor=instructor,
        title="T",
        slug="t",
        short_description="s",
        description="d",
        level=Course.Level.BEGINNER,
        language="uz",
    )

    saved = client.patch(
        f"/api/v1/admin/courses/{course.pk}", {"image_url": uploaded}, format="json"
    )
    assert saved.status_code == 200, saved.json()
    assert saved.json()["image_url"] == uploaded

    absolute = client.patch(
        f"/api/v1/admin/courses/{course.pk}",
        {"image_url": "https://cdn.example.com/cover.jpg"},
        format="json",
    )
    assert absolute.status_code == 200

    rejected = client.patch(
        f"/api/v1/admin/courses/{course.pk}", {"image_url": "javascript:alert(1)"}, format="json"
    )
    assert rejected.status_code == 400
