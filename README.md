# Ermes - Lean Ticketing MVP

## Quick Start

1. Create a virtual environment and install dependencies.
2. Copy `.env.example` to `.env` and fill Supabase + secrets.
3. Run SQL in `docs/supabase-schema.sql` in your Supabase project.
4. Start app:

```bash
python run.py
```

`run.py` is for local development only.

## Deploy On Vercel

This project is now configured for Vercel using:

- `api/index.py` as the Python serverless entrypoint.
- `vercel.json` to route all requests through the Flask app.

### 1) Required environment variables in Vercel

Copy the same values used in `.env` (or `.env.example`) into your Vercel Project Settings > Environment Variables:

- `APP_ENV`
- `DEBUG`
- `FLASK_SECRET_KEY`
- `JWT_SECRET`
- `JWT_ACCESS_MINUTES`
- `JWT_REFRESH_DAYS`
- `FACTS_TOKEN_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `MAX_UPLOAD_SIZE_MB`
- `ALLOWED_UPLOAD_MIME_TYPES`
- `ALLOWED_UPLOAD_EXTENSIONS`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

Important:

- Keep `FACTS_TOKEN_URL` pointing to your FACTS token endpoint so login verification keeps working.
- Use a stable `FLASK_SECRET_KEY` in Vercel. Changing it invalidates existing signed sessions.

### 2) Deploy

From Vercel dashboard:

1. Import this repository.
2. Keep Root Directory as project root.
3. Add the environment variables above.
4. Deploy.

Or with Vercel CLI:

```bash
vercel
```

### 3) Behavior notes on Vercel

- `run.py` is not used by Vercel runtime.
- Flask routes, templates and `/static/*` assets are served through the serverless Python function.
- FACTS validation flow remains unchanged.

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
