# Message API

Church management backend — Flask, SQLite, JWT auth, 108 endpoints, 23 models.

## Quickstart

```bash
python3 -m venv venv && source venv/bin/activate
pip install -e .
flask db upgrade
flask seed
flask run
```

Default admin: `admin` / `changeme`

## Auth

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/users` | Register |
| `POST /api/v1/auth/sessions` | Login — returns `access_token` + `refresh_token` |
| `DELETE /api/v1/auth/sessions` | Logout (send `refresh_token` in body) |
| `POST /api/v1/auth/tokens` | Rotate refresh token |
| `GET /api/v1/auth/user` | Current user + capabilities |

Access tokens expire in **15 min**. Attach as `Authorization: Bearer <token>`.

## Core resources

| Resource | Endpoints | Description |
|----------|-----------|-------------|
| `/api/v1/persons` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Directory |
| `/api/v1/teams` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Teams with members |
| `/api/v1/groups` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Small groups |
| `/api/v1/flocks` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Flocks |
| `/api/v1/events` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Calendar events |
| `/api/v1/posts` | `GET`, `POST`, `GET /:id`, `PATCH /:id`, `DELETE /:id` | Announcements |
| `/api/v1/files` | `GET /:id`, `DELETE /:id`, `GET /:id/download` | File storage |
| `/api/v1/families` | `GET`, `GET /:family_id` | Family relationships |
| `/api/v1/relationships` | `GET`, `POST`, `GET /:id`, `DELETE /:id` | Person-person links |
| `/api/v1/users` | `GET`, `GET /:id`, `PATCH /:id` | User accounts |
| `/api/v1/organization` | `GET`, `PATCH` | Org settings |
| `/api/v1/admin/auth-attempts` | `GET` | Login audit log |

### Sub-resources

| Route | Methods | Description |
|-------|---------|-------------|
| `teams/:id/persons` | `GET`, `POST`, `DELETE /:person_id` | Team roster |
| `groups/:id/members` | `GET`, `POST`, `PATCH /:person_id`, `DELETE /:person_id` | Group members |
| `flocks/:id/members` | `GET`, `POST`, `PATCH /:person_id`, `DELETE /:person_id` | Flock members |
| `groups/:id/posts` | `GET`, `POST` | Group announcements |
| `groups/:id/meetings` | `GET`, `POST` | Group meetings |
| `groups/:id/files` | `GET`, `POST` | Group files |
| `teams/:id/posts` | `GET`, `POST` | Team announcements |
| `teams/:id/meetings` | `GET`, `POST` | Team meetings |
| `teams/:id/files` | `GET`, `POST` | Team files |
| `posts/:id/files` | `POST` | Post attachments |
| `events/:id/overrides` | `GET`, `POST` | Calendar exceptions |
| `duty-groups/:id/duties` | `GET`, `POST` | Roles in a duty group |
| `duty-groups/:id/memberships` | `GET`, `POST` | Available people |
| `duties/:id/assignments` | `GET`, `POST` | Scheduled duty roster |

### Container resources (no `:id`)

| Route | Methods | Description |
|-------|---------|-------------|
| `/api/v1/calendar` | `GET` | Query events by date range |
| `/api/v1/roster` | `GET` | Aggregate roster view |
| `/api/v1/meetings/:id` | `GET`, `PATCH`, `DELETE` | Meetings (created under groups/teams) |
| `/api/v1/overrides/:id` | `GET`, `PATCH`, `DELETE` | Calendar overrides |
| `/api/v1/assignments/:id` | `GET`, `DELETE` | Duty assignments |

### Mutations on container resources

| Path | Method | Action |
|------|--------|--------|
| `POST /auth/tokens` | Rotate refresh token |
| `POST /auth/sessions` | Login |
| `DELETE /auth/sessions` | Logout |
| `PATCH /organization` | Update org |
| `PATCH /users/:id` | Update user |

## Filtering & search

Query params apply to `GET` list endpoints:

| Param | Example | Effect |
|-------|---------|--------|
| `?q=` | `?q=john` | Full-text search |
| `?sort=` | `?sort=-created_at` | Sort field (`-` for desc) |
| `?field=value` | `?team_id=1` | Exact match |
| `?field[]=a,b` | `?status[]=active,pending` | IN filter |
| `?date_from=` / `?date_to=` | `?date_from=2026-01-01` | Date range |

## Error format

All errors return:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {"field": ["Required"]}
  }
}
```

HTTP codes: 400, 401, 403, 404, 409, 413, 415, 422, 429, 500

## Idempotency

Send `Idempotency-Key` header on `POST` requests. Duplicate keys within 1 hour return the original response.

## Authorization

Capabilities are flat `verb_noun` strings returned at `GET /api/v1/auth/user`:

- `manage_users`, `manage_groups`, `manage_teams`, `manage_rosters`
- `manage_flocks`, `manage_events`, `manage_organization`
- `manage_files`, `manage_announcements`, `edit_directory`

Super admins have all capabilities. Decorators: `@require_capability(...)`, `@require_group_admin`, `@require_group_member`.

## Project structure

```
src/message/
├── __init__.py           # App factory, blueprint registration
├── extensions.py         # db, jwt, cors, limiter, ma
├── config.py             # Dev / Test / Prod config
├── authz.py              # Authorization decorators
├── errors.py             # Error handlers (HTTP, Marshmallow, JWT)
├── logging.py            # JSON + structured logging, slow query detection
├── middleware.py         # Request ID, request logging
├── cli.py                # flask seed command
├── models/               # 23 SQLAlchemy models
├── schemas/              # Marshmallow schemas (request/response)
└── blueprints/           # 21 endpoint modules
tests/                    # 17 test files, 162 tests
deploy/lxc/               # systemd, nginx, .env, setup script
```

## Models (23)

User, UserPermission, Person, PersonTeam, FamilyRelationship, Organization, Team, Meeting, Group, GroupMember, Post, File, DutyGroup, Duty, DutyGroupMembership, DutyAssignment, Flock, FlockMember, CalendarEvent, CalendarOverride, AuthAttempt, IdempotencyRecord, RefreshToken

## Tests

```bash
pytest -v              # 162 tests
pytest tests/ -k auth  # Run auth tests only
```

## Deployment

Single LXC container, SQLite, Nginx + Gunicorn + Redis.

```bash
# Inside the container:
bash deploy/lxc/setup-container.sh
```

See `deploy/lxc/` for systemd unit, nginx config, and bootstrap script.
