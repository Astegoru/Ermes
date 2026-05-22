## Plan: Lean Ticketing MVP with Auth-First Access and FACTS Login Verification

Build a simple, maintainable ticketing app where all views and API endpoints require authentication first. FACTS credentials are used only for first login verification, then the app runs on its own JWT/session for all subsequent API access. Keep ownership and permissions enforced in Flask, store data/files in Supabase, and ship an MVP optimized for fast deployment on Render.

**Steps**
1. Phase 1 - Foundation and Architecture
1. Confirm the project structure split: backend API (Flask) and frontend UI (Bootstrap templates or SPA-like pages consuming API) with a strict API boundary.
2. Define auth-first access policy globally:
	- Web views: if no valid app session/JWT, redirect to login view.
	- API routes: if no valid app JWT, return 401 JSON; if authenticated without permission, return 403 JSON.
	- Only login/refresh/health endpoints are public.
3. Define the FACTS first-authentication contract:
	- Request: POST https://apimoneda.facts.cl/api/auth/token/ with payload {"username": "...", "password": "..."}.
	- Failure: if response contains {"detail":"No active account found with the given credentials"}, deny access.
	- Success: consider credentials verified, upsert local user, issue app JWT/refresh token, and continue only with app JWT.
	- FACTS token is verification-only for login and not used to authorize app endpoints.
4. Define role/permission baseline for MVP: all authenticated users can create categories, create tickets, solve tickets, and merge categories; only owner can edit/delete_soft own tickets; edit allowed only while ticket is open.
5. Add minimal admin access model in Flask with separate authentication controlled by environment variables, used only to assign or update one superuser.

2. Phase 2 - Data Model (Supabase)
1. Create users table with immutable external_username (FACTS username), display_name optional, created_at, last_login_at, is_active.
2. Create categories table with id, name, description, is_active, merged_into_category_id nullable, created_by_user_id, timestamps.
3. Create tickets table with id, title, urgency, category_id, link nullable, file_url nullable, file_type nullable, description nullable, owner_user_id, status, solved_at nullable, deleted_at nullable, created_at, updated_at.
4. Create ticket_events table for auditable actions (created, edited, solved, deleted_soft, category_changed).
5. Add constraints and indexes: urgency/status indexes for list sorting/filtering; owner_user_id index; category foreign keys; soft-delete filtering conventions.

3. Phase 3 - API Design (Flask)
1. Auth endpoints
1. POST /api/auth/login: validate with FACTS, then issue local JWT.
2. POST /api/auth/refresh (optional for MVP if short-lived access + refresh token strategy is chosen).
3. GET /api/auth/me: return current user profile from local JWT.
4. POST /api/admin/auth/login: separate admin login using credentials from environment variables (not FACTS), only for superuser assignment access.
2. Category endpoints
1. POST /api/categories to create.
2. GET /api/categories for active list.
3. PATCH /api/categories/{id} for description/name updates.
4. POST /api/categories/merge to merge source categories into target category and mark merged categories inactive.
3. Ticket endpoints
1. POST /api/tickets create ticket (owner comes from JWT subject, never request body).
2. GET /api/tickets with default sort urgency desc then created_at desc; allow override via query params.
3. GET /api/tickets/{id} details (read-only view data).
4. PATCH /api/tickets/{id} edit fields only if owner and status=open.
5. POST /api/tickets/{id}/solve allowed for any authenticated user.
6. DELETE /api/tickets/{id} performs soft delete only if owner and status=open.
4. File upload endpoint
1. POST /api/files/upload accepts images, PDF, and Excel only.
2. Enforce mime-type and extension validation plus max file size from environment variable.
3. Upload to Supabase Storage and return stored URL + metadata for ticket attachment.
5. Admin endpoints (admin-only, minimal)
1. POST /api/admin/superuser/assign: assign one existing app user as superuser.
2. GET /api/admin/superuser: read current superuser identity.

4. Phase 4 - Frontend Views (Bootstrap)
1. Login view integrated with local backend login route (which internally calls FACTS).
2. Config view for category creation/list/edit and merge workflow.
3. Ticket form view for create/edit, with owner hidden and controlled by backend identity.
4. Ticket list view with urgency-first default ordering, user-selectable sort/filter controls, and actions by permission.
5. Ticket details view as read-only form plus action buttons at bottom.

5. Phase 5 - Security and Business Rules Hardening
1. Implement JWT auth middleware and route guards in Flask.
2. Enforce default-deny routing so all routes are protected unless explicitly public.
3. Centralize authorization checks (owner checks, open-ticket edit/delete checks, superuser override checks).
4. Add CSRF protection for server-rendered admin forms if session cookies are used.
5. Add input validation schemas for all request payloads.
6. Define consistent error responses for auth failures, validation failures, and forbidden operations.
7. Add soft-delete aware query helpers to avoid accidentally exposing deleted tickets/categories.

6. Phase 6 - Deployment and Runtime
1. Configure Render service for Flask app startup and health checks.
2. Configure Supabase connection and storage bucket settings via environment variables.
3. Define environment variables for JWT secret, token expiry, FACTS endpoint URL, max upload size, and allowed mime types.
4. Add minimal operational docs for local run and Render deployment.

**Relevant files**
- /backend/app.py - Flask app bootstrap, blueprint registration, middleware wiring.
- /backend/auth/routes.py - login/me/refresh endpoints and FACTS verification integration.
- /backend/auth/service.py - FACTS token validation call and local token issuance logic.
- /backend/auth/middleware.py - JWT verification and current-user context loader.
- /backend/admin/routes.py - admin login and superuser assignment endpoints.
- /backend/admin/service.py - superuser assignment logic and superuser identity retrieval.
- /backend/categories/routes.py - CRUD + merge endpoint behavior.
- /backend/categories/service.py - merge process (reassign tickets, deactivate merged categories, audit events).
- /backend/tickets/routes.py - ticket CRUD, solve, and soft-delete endpoints.
- /backend/tickets/service.py - ownership and open-status business rules.
- /backend/files/routes.py - upload endpoint validation and Supabase storage integration.
- /backend/db/models.py - users/categories/tickets/ticket_events schema definitions.
- /backend/db/repositories.py - query helpers, default sorting, soft-delete filters.
- /frontend/templates/login.html - login page.
- /frontend/templates/categories.html - category and merge UI.
- /frontend/templates/ticket_form.html - create/edit form.
- /frontend/templates/tickets_list.html - list with sortable columns and actions.
- /frontend/templates/ticket_detail.html - read-only details + bottom actions.
- /frontend/templates/admin_login.html - separate admin access form.
- /frontend/templates/admin_panel.html - superuser assignment view only.
- /docs/project-context-v1.md - cleaned functional spec and acceptance criteria.

**Verification**
1. Auth flow test: invalid FACTS creds are rejected; valid FACTS creds create session and return local JWT; protected endpoints reject missing/invalid local JWT.
2. Auth-first access test: unauthenticated view requests are redirected to login, and unauthenticated API requests return 401.
3. Admin access test: only env-based admin credentials can access admin panel and admin endpoints; non-admin users receive 403.
4. Superuser assignment test: admin can assign exactly one superuser identity, and reassignment updates the same record.
5. Ownership/permission test: non-owner cannot edit/delete another user ticket; owner cannot edit/delete when status is not open.
6. Superuser override test: superuser can edit/delete/solve any ticket and manage categories regardless of original owner.
7. Solve workflow test: any authenticated user can solve open tickets; solved ticket becomes non-editable for normal users.
8. Soft-delete test: delete action sets deleted_at/status flag; deleted tickets are hidden from default lists but recoverable for audit.
9. Category merge test: merging categories reassigns existing tickets to target category and deactivates source categories.
10. Upload validation test: accept images/PDF/Excel within size limit; reject disallowed types and oversized files.
11. Sorting/filter test: default urgency-first sort works and user-selected sorting overrides correctly.
12. End-to-end smoke test on Render using Supabase resources and environment variables.

**Decisions**
- Included: FACTS used only as login verifier; app uses its own JWT afterward.
- Included: all views and APIs are authentication-first with default deny.
- Included: owner identity sourced from JWT, never from client payload.
- Included: edit/delete limited to owner and only when ticket is open.
- Included: delete is soft delete only.
- Included: category creation and merge available to all authenticated users.
- Included: attachments limited to images, PDF, and Excel in Supabase Storage.
- Included: separate env-based admin access used only to assign or update superuser.
- Included: superuser acts as global owner with override permissions across the app.
- Excluded for MVP: complex role hierarchy, workflow states beyond open/solved/archived/deleted_soft, and scalability optimizations.

**Further Considerations**
1. JWT strategy recommendation: short-lived access token plus refresh token endpoint for better security on persistent sessions.
2. Category merge UX recommendation: preview impacted ticket count before confirming merge to prevent accidental taxonomy changes.
3. Archive process recommendation: run a simple scheduled job or manual action to move solved/soft-deleted tickets to archived status for cleaner lists.
