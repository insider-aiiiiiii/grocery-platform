# Docker Development Setup

This document describes the local Docker development environment for the Django grocery-platform backend. It provides Django, PostgreSQL, DBeaver connectivity, and Postman setup only. It does not implement business domains, authentication, tenant enforcement, or application APIs.

## Prerequisites

Install:

- Docker Desktop with Docker Compose
- Git
- DBeaver, if database inspection is needed
- Postman, if API testing is needed

## Environment Configuration

Copy the example environment file from the repository root.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Git Bash or macOS/Linux:

```bash
cp .env.example .env
```

Review the local values before starting. The real `.env` file is ignored by Git and must not be committed.

Important variables:

```text
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-me-for-local-development
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=grocery_platform
POSTGRES_USER=grocery_user
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_PORT=8000
```

Inside Compose, Django always connects to `db:5432`. The `POSTGRES_PORT` value controls the host port published for DBeaver. If the host port is changed to `5433`, DBeaver uses `localhost:5433`, while Django still uses `db:5432` inside the Compose network.

## Start the Environment

From the repository root:

```bash
docker compose up -d --build
```

Check the services:

```bash
docker compose ps
```

Follow all logs:

```bash
docker compose logs -f
```

Follow only Django logs:

```bash
docker compose logs -f web
```

Follow only PostgreSQL logs:

```bash
docker compose logs -f db
```

Follow only Frontend logs:

```bash
docker compose logs -f frontend
```

The Django development server is available at the host port configured by `DJANGO_PORT`:

```text
http://localhost:<DJANGO_PORT>
```

With the example value, this is `http://localhost:8000`. The Django process still listens on container port `8000`.

The Next.js frontend development server is available at the host port configured by `FRONTEND_PORT`:

```text
http://localhost:<FRONTEND_PORT>
```

With the example value, this is `http://localhost:3000`. The Next.js process listens on container port `3000`.

The current scaffold routes Django Admin only. No application API endpoints are implemented yet. The documented future API base is:

```text
http://localhost:8000/api/v1/
```

Do not invent or test endpoints that have not been implemented.

## Container Connectivity

The two connection paths are different:

```text
Django container → db:5432
Host machine / DBeaver → localhost:<POSTGRES_PORT>
```

The Compose service name `db` is resolvable only inside the Compose network. `localhost` from the Django container refers to the Django container itself, not PostgreSQL.

## Django Commands

Run management commands inside the Django container:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py shell
docker compose exec web python manage.py createsuperuser
```

`migrate` applies only migrations that already exist. Do not create business migrations as part of environment setup. Django migrations remain the source of truth for application schema.

The current project has only scaffolded domain apps and no business models or domain migrations. Django's built-in migrations may still create framework tables when `migrate` runs.

## DBeaver PostgreSQL Connection

1. Start the environment:

   ```bash
   docker compose up -d
   ```

2. Open DBeaver.

3. Create a new PostgreSQL connection.

4. Use these values:

   | Setting | Value |
   |---|---|
   | Database type | PostgreSQL |
   | Host | `localhost` |
   | Port | `5432`, or the host value from `POSTGRES_PORT` |
   | Database | `grocery_platform` or `POSTGRES_DB` from `.env` |
   | Username | `grocery_user` or `POSTGRES_USER` from `.env` |
   | Password | The `POSTGRES_PASSWORD` value from local `.env` |
   | SSL | Disable/default for local development |

5. Test the connection and save it.

Once connected, inspect the `public` schema. It may contain only Django framework tables or very few tables because business models and migrations have not been implemented.

```text
Schemas
  └── public
      ├── Tables
      ├── Views
      ├── Indexes
      └── Sequences
```

Do not create business tables manually in DBeaver. Use reviewed Django models and migrations when application schema is implemented.

## Postman Setup

Create a Postman environment with:

```text
base_url = http://localhost:<DJANGO_PORT>
api_base_url = {{base_url}}/api/v1
```

Replace `<DJANGO_PORT>` with the value from your local `.env` file, such as `http://localhost:8001`.

Use `{{api_base_url}}` for future application requests after endpoints are implemented. The current scaffold has no implemented `/api/v1/` endpoint and this setup does not add one.

Do not add authentication variables yet. The authentication mechanism is not finalized by the project architecture.

## Stop the Environment

Normal shutdown, preserving the local PostgreSQL volume:

```bash
docker compose down
```

Start again without rebuilding:

```bash
docker compose up -d
```

Rebuild the Django image after dependency or Dockerfile changes:

```bash
docker compose up -d --build
```

The following command is destructive for local database data and should not be used as normal shutdown:

```bash
docker compose down -v
```

`docker compose down -v` removes the named `postgres_data` volume and destroys the local PostgreSQL database stored in it.

## Verification Checklist

Run:

```bash
docker compose config
docker compose ps
docker compose exec web python manage.py check
docker compose exec web python manage.py migrate
```

Expected checks:

- Compose configuration is valid.
- `web` is running.
- `db` is running and healthy.
- Django system checks pass.
- Existing migrations apply successfully.
- DBeaver can connect to the same PostgreSQL instance through the published host port.
- `http://localhost:<DJANGO_PORT>` responds from the host.

Run the existing test suite when tests are present:

```bash
docker compose exec web python manage.py test
```

Do not add fake tests for this infrastructure task.

## Troubleshooting

### Port 5432 is already in use

Change only the host port in `.env`:

```text
POSTGRES_PORT=5433
```

Then recreate the services:

```bash
docker compose down
docker compose up -d
```

Use `localhost:5433` in DBeaver. Django inside Docker continues to use `db:5432`; do not set the web container's `POSTGRES_PORT` to the host port.

### Port 8000 is already in use

Change the Django host port in `.env` without changing the container port:

```text
DJANGO_PORT=8001
```

Then recreate the web service:

```bash
docker compose up -d
```

Open `http://localhost:8001`. Django still listens on port `8000` inside the container.

### PostgreSQL is not ready

Check the database logs and service health:

```bash
docker compose logs db
docker compose ps
```

The web service waits for the PostgreSQL healthcheck before starting.

### Django cannot connect to PostgreSQL

Confirm that:

- `.env` exists at the repository root.
- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` match the database service.
- `POSTGRES_HOST` is `db` inside Compose.
- The web container's `POSTGRES_PORT` is `5432`.
- The `db` service is healthy.

### Database data must be reset

Only when intentionally discarding local data:

```bash
docker compose down -v
docker compose up -d --build
docker compose exec web python manage.py migrate
```

This permanently removes the local PostgreSQL volume. Never use it to solve an unknown application problem without confirming that local data can be discarded.

## Scope Boundary

This setup does not add or modify:

- Domain models or business migrations
- Serializers, views, URLs, or API endpoints
- Authentication or authorization
- Tenant enforcement
- Merchant permissions or customer identity logic
- Orders, catalog, inventory, campaigns, notifications, or analytics behavior
- Production deployment infrastructure
