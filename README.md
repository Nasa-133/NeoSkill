# NeoSkill

Independent frontend/backend architecture for the NeoSkill LMS MVP. Next.js frontend
and Python/Django REST Framework backend have separate dependencies, lockfiles,
builds, tests and Docker images. PostgreSQL owns backend persistence; the frontend
communicates with the backend through the versioned HTTP API.

## Repository structure

```text
frontend/              Independent Next.js app, lockfile, tests and Dockerfile
backend/               Independent Python/DRF API, uv.lock, tests and Dockerfile
docs/ARCHITECTURE.md    Ownership, module boundaries and deployment contract
.github/workflows/     Application-specific verification
compose.yaml           Local container orchestration
```

There is no shared npm workspace or root dependency installation. Each application
owns its dependencies and builds from its own directory. Frontend talks to the
backend only over the versioned HTTP API; it never imports backend implementation
or database entities. Each image can build independently.

## Run both independently

With Docker Desktop running:

```sh
docker compose build frontend backend
docker compose up -d --wait database
docker compose run --rm backend python manage.py migrate
docker compose up -d --wait frontend backend
curl http://localhost:3000/health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/readiness
```

Authentication uses email and password. Registration is available at `/register`;
password-reset links are sent through the SMTP settings saved in the admin panel or
the `EMAIL_*` environment fallback.

Start just one with `docker compose up -d frontend` or `docker compose up -d backend`.
Stop with `docker compose stop`. `FRONTEND_PORT` and `BACKEND_PORT` can override host
ports. Compose is for local development, using the example backend environment plus
optional `backend/.env` overrides; production must inject its own secret and hosts.

For Python development and checks, see [backend/README.md](backend/README.md):

```sh
cd backend
uv sync --locked
cp .env.example .env
make dev
```

## Run the frontend

With Docker Desktop running:

```sh
docker compose up --build -d frontend
curl http://localhost:3000/health
docker compose stop frontend
```

Or use Node 24.20.0 from `frontend/.nvmrc`:

```sh
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

The root URL serves the public landing page and `/health` reports frontend liveness.
The frontend needs neither backend nor PostgreSQL to start, build or pass its
liveness check; data-backed screens require the API.

## Verify

```sh
cd frontend
npm run check
```

This runs lint, typecheck, build and tests. Details and standalone Docker commands
are in [frontend/README.md](frontend/README.md). In `backend/`, start PostgreSQL and
run `make check` for Ruff, mypy, PostgreSQL-backed pytest, package build and Django
checks after `uv sync --locked`.
GitHub Actions verifies each application independently on relevant changes; it
requires a repository remote before it can run.

Architecture rationale and module ownership are in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Production deployment

Use the production-specific compose file; it refuses to start without required secrets:

```sh
cp .env.production.example .env.production
# Fill the real domain, a random 50+ character Django secret and PostgreSQL password.
docker compose --env-file .env.production -f compose.production.yaml build
docker compose --env-file .env.production -f compose.production.yaml up -d database
docker compose --env-file .env.production -f compose.production.yaml run --rm backend python manage.py migrate --noinput
docker compose --env-file .env.production -f compose.production.yaml up -d
```

Terminate HTTPS in a reverse proxy that forwards to the configured frontend bind/port. The
complete first-deploy, admin creation, SMTP, persistent media, verification and rollback steps are
in [docs/RELEASE_SETUP.md](docs/RELEASE_SETUP.md).

Product sources remain in `PRODUCT_CONTEXT.md`, `DECISIONS.md`, `DESIGN_SYSTEM.md` and `BACKLOG.md`.
# NeoSkill
# NeoSkill
