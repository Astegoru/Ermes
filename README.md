# Ermes - Lean Ticketing MVP

## Quick Start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill Supabase + secrets.
3. Run SQL in `docs/supabase-schema.sql` in your Supabase project.
4. Start app:

```bash
python run.py
```

## Auth Model

- FACTS is used only at login credential verification.
- App issues and uses local JWT for API auth.
- Session is used for protected server-rendered view navigation.
- Admin panel credentials come from environment variables `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

## Core Endpoints

- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`
- `POST /api/categories`
- `GET /api/categories`
- `POST /api/tickets`
- `GET /api/tickets`
- `GET /api/tickets/trash`
- `POST /api/tickets/<ticket_id>/restore`
- `DELETE /api/tickets/<ticket_id>/purge`
- `POST /api/files/upload`
- `POST /api/admin/auth/login`
- `POST /api/admin/superuser/assign`
