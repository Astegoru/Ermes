# Ermes MVP Context v2

## Purpose of This Document

This file expands v1 with broader technical and product context so a second AI can propose concrete improvements without re-discovering core assumptions.

Use this as the source of truth for:
- What the project is and what is already implemented.
- Which security/business rules are non-negotiable for MVP.
- Where improvements are most valuable next.

## Project Summary

Ermes is a lean ticketing MVP with:
- Flask backend and server-rendered Bootstrap frontend.
- Auth-first access control for both views and APIs.
- FACTS credentials used only to verify first login.
- Local app JWT (and optional refresh strategy) used for all subsequent authorization.
- Supabase as data and file storage backend.
- Minimal admin access (separate env-based auth) only to assign/update a single superuser identity.

## Current Implementation Baseline

### Backend modules
- `backend/app.py`: app bootstrap, blueprint registration, middleware wiring.
- `backend/auth/`: login/refresh/me routes, FACTS verification service, JWT middleware.
- `backend/admin/`: admin auth and superuser assignment/read endpoints.
- `backend/categories/`: create/list/update/merge categories.
- `backend/tickets/`: create/list/get/edit/solve/soft-delete tickets.
- `backend/files/`: attachment upload validation and Supabase storage upload.
- `backend/db/`: schema-facing models and repository/query helpers.

### Frontend templates
- `frontend/templates/login.html`
- `frontend/templates/categories.html`
- `frontend/templates/ticket_form.html`
- `frontend/templates/tickets_list.html`
- `frontend/templates/ticket_detail.html`
- `frontend/templates/admin_login.html`
- `frontend/templates/admin_panel.html`

### Data model expected in Supabase
- `users`
- `categories`
- `tickets`
- `ticket_events`
- `app_meta`

Schema bootstrap reference: `docs/supabase-schema.sql`.

## Auth and Security Model (Critical)

### Auth-first policy (default deny)
- All web views require valid app auth context; unauthenticated users are redirected to login.
- All API routes require valid app JWT except explicitly public routes.
- Public routes are intentionally minimal (login/refresh/health and admin auth login).
- API auth failures should be consistent:
  - `401` for missing/invalid authentication.
  - `403` for authenticated but unauthorized actions.

### FACTS contract (verification only)
- Login verification request:
  - `POST https://apimoneda.facts.cl/api/auth/token/`
  - Payload: `{ "username": "...", "password": "..." }`
- If FACTS returns `{"detail":"No active account found with the given credentials"}`, access is denied.
- On FACTS success, the app upserts local user and issues local auth tokens.
- FACTS token is not used to authorize Ermes endpoints.

### Admin boundary
- Admin login does not use FACTS.
- Admin credentials are environment-based.
- Admin scope is intentionally narrow: assign/update a single superuser record.

## Authorization and Business Rules (MVP)

### General permissions
- All authenticated users can:
  - Create categories.
  - Merge categories.
  - Create tickets.
  - Solve tickets.
- Owner-only constraints for normal users:
  - Edit ticket: only owner and only while status is `open`.
  - Soft delete ticket: only owner and only while status is `open`.
- Superuser override:
  - Can edit/delete/solve any ticket.
  - Can manage categories regardless of ownership.

### Ticket lifecycle
- MVP states centered on `open` and `solved` (plus soft-delete semantics).
- Deletion is soft delete, not hard delete, for auditability.
- Events should be recorded in `ticket_events` for auditable actions.

### Category merge behavior
- Merge operation reassigns tickets from source categories to target category.
- Source categories become inactive and/or linked to target (`merged_into_category_id`).

### File upload constraints
- Allowed types: images, PDF, Excel.
- Validation must enforce both mime type and extension.
- Maximum upload size comes from environment variable.
- Storage target is Supabase Storage; API returns stored URL and metadata.

## Architecture and Runtime Context

### Stack and deployment intent
- Python Flask app, likely deployed as a single Render service for MVP speed.
- Supabase provides relational data and object storage.
- Frontend is template-based (Bootstrap) and API-consuming.

### Environment-driven configuration
At minimum, runtime config includes:
- JWT secret and expiry settings.
- FACTS endpoint URL.
- Supabase project URL/keys and storage bucket.
- Upload limits and allowed mime types/extensions.
- Admin username/password.

### Repository-level known context
- App factory + auth middleware pattern is already present.
- Supabase repository layer exists as integration boundary.
- Frontend uses token-based API calls (local storage usage noted in prior context).
- Soft-delete workflow exists; trash endpoints are also present in this repository (`/api/tickets/trash`, restore, purge).

## What Is Done vs What Is Still a Candidate for Improvement

### Already implemented (baseline)
- Core endpoints for auth, admin, categories, tickets, files.
- FACTS-first verification and local token usage.
- Auth-first model and ownership-based ticket restrictions.
- Supabase-backed persistence and storage integration.

### High-value improvement areas (next)
1. Security hardening
- Confirm strict default-deny route coverage (no accidental public routes).
- Add/verify CSRF strategy for any cookie/session-based admin forms.
- Strengthen token lifecycle (rotation/revocation/refresh handling).
- Improve audit logging and suspicious auth activity visibility.

2. API consistency and validation
- Enforce schema validation for every request body/query.
- Standardize error payload shape across all modules.
- Ensure pagination/filter/sort contracts are explicit and consistent.

3. Data integrity and transactional safety
- Ensure category merge and ticket state transitions are transaction-safe.
- Validate soft-delete filtering is consistently applied in all list/detail paths.
- Tighten DB constraints/indexes for expected query patterns.

4. Test coverage and quality gates
- Add focused tests for auth-first routing, permissions, superuser override, merge, and upload validation.
- Add integration/smoke tests close to deployment topology.
- Define minimal CI checks for lint/test/security scanning.

5. Frontend UX and resilience
- Improve validation/error presentation for login/forms/uploads.
- Improve category merge UX (impact preview before confirm).
- Improve ticket list usability (filters/sorting persistence, clear status actions).

6. Operations and observability
- Add structured logging and request correlation IDs.
- Add health/readiness diagnostics useful for Render.
- Document incident/debug playbooks for auth and storage failures.

## Constraints and Non-Negotiables

Any proposal from a second AI should preserve these MVP decisions unless explicitly challenged:
- FACTS remains verification-only at login.
- Ermes authorization must rely on local app auth token/session.
- Owner identity is server-derived from auth context, never client-provided.
- Edit/delete restrictions for normal users remain owner+open-ticket constrained.
- Ticket delete remains soft by default.
- Category creation and merge remain available to authenticated users.
- Admin path remains separate and minimal, dedicated to superuser assignment.

## Suggested Prompt Frame for a Second AI

Use this framing when asking for improvements:
- Goal: improve reliability, security, maintainability, and UX without overengineering beyond MVP.
- Keep: current architecture (Flask + Supabase + server-rendered templates), auth-first policy, FACTS verification-only model.
- Deliverables requested:
  - Prioritized improvement backlog (P0/P1/P2) with rationale.
  - Concrete code-level change map by file/module.
  - Risk analysis for each proposed change.
  - Minimal test plan tied to changed behavior.
  - Migration/deployment notes (if schema or env changes are needed).

## Verification Checklist Snapshot

Core checks expected to continue passing as improvements are made:
1. Invalid FACTS credentials are rejected.
2. Valid FACTS credentials issue local auth and allow protected access.
3. Unauthenticated views redirect to login; unauthenticated APIs return `401`.
4. Authenticated-but-forbidden actions return `403`.
5. Admin-only endpoints reject non-admin users.
6. Superuser assignment remains singular and updateable.
7. Ownership rules on edit/delete remain enforced.
8. Superuser override remains functional.
9. Solve flow transitions ticket correctly and blocks normal edits where required.
10. Soft delete hides tickets from default lists while preserving auditability.
11. Category merge reassigns tickets and deactivates merged categories.
12. Upload validation accepts only allowed types within configured size.
13. Default urgency-first sorting works and explicit sort overrides are honored.

## Source References

- `docs/project-context-v1.md`
- `docs/plan-ermes.prompt.md`
- `docs/supabase-schema.sql`
