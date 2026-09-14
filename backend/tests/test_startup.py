import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def test_production_server_starts_without_frontend_or_database():
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]

    with tempfile.TemporaryFile() as output:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "neoskill.config.wsgi:application",
                "--bind",
                f"127.0.0.1:{port}",
                "--workers",
                "1",
            ],
            cwd=Path(__file__).parents[1],
            env={
                "PATH": os.environ["PATH"],
                # Exercise the explicit deployment environment, independent of a
                # developer's local .env (which may configure a running database).
                "PYTHON_DOTENV_DISABLED": "1",
                "APP_ENV": "production",
                "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
                "DJANGO_DEBUG": "false",
                "DJANGO_ALLOWED_HOSTS": "127.0.0.1",
                "DJANGO_SSL_REDIRECT": "false",
                "CORS_ALLOWED_ORIGINS": "",
            },
            stdout=output,
            stderr=output,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    output.seek(0)
                    raise AssertionError(output.read().decode())
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=1) as response:
                        assert response.status == 200
                        assert json.load(response) == {
                            "status": "ok",
                            "service": "neoskill-backend",
                        }
                        try:
                            urlopen(f"http://127.0.0.1:{port}/api/v1/readiness", timeout=1)
                        except HTTPError as error:
                            assert error.code == 503
                            assert json.load(error) == {
                                "status": "unavailable",
                                "service": "neoskill-backend",
                            }
                        else:
                            raise AssertionError("Readiness must fail closed without PostgreSQL")
                        return
                except (URLError, TimeoutError, ConnectionResetError):
                    time.sleep(0.1)
            output.seek(0)
            raise AssertionError(
                "Gunicorn did not become healthy in 15 seconds:\n" + output.read().decode()
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
