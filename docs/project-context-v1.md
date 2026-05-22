# Ermes MVP Context v1

This workspace contains the initial implementation of a lean ticketing MVP with:

- Flask backend with auth-first route guarding.
- FACTS verification-only login workflow.
- Local app JWT access/refresh tokens after FACTS validation.
- Supabase integration for database and file storage.
- Bootstrap server-rendered views for login, categories, tickets, and admin panel.

## Current Scope Implemented

- Auth endpoints: login, refresh, me.
- Admin endpoints: admin auth login, assign superuser, get superuser.
- Categories endpoints: create, list, update, merge.
- Tickets endpoints: create, list, get, edit, solve, soft delete.
- Files endpoint: upload with mime/extension/size validation.

## Tables Expected in Supabase

- users
- categories
- tickets
- ticket_events
- app_meta

See docs/supabase-schema.sql for schema bootstrap SQL.
