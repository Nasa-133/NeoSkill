FROM python:3.12.14-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12.14-slim-bookworm AS production
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN groupadd --gid 10001 neoskill && useradd --uid 10001 --gid neoskill --no-create-home neoskill
# Created before the volume mount so a fresh named volume inherits this ownership.
RUN mkdir -p /var/lib/neoskill/media && chown -R neoskill:neoskill /var/lib/neoskill
COPY --from=build --chown=neoskill:neoskill /app/.venv /app/.venv
COPY --from=build --chown=neoskill:neoskill /app/manage.py /app/manage.py
USER neoskill
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python -c "import os,urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/api/v1/health',headers={'Host':os.environ['DJANGO_ALLOWED_HOSTS'].split(',')[0].strip()}); urllib.request.urlopen(r,timeout=3)"
CMD ["gunicorn", "neoskill.config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "--access-logfile", "-", "--error-logfile", "-"]
