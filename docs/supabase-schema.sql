create extension if not exists pgcrypto;

create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    external_username text not null unique,
    display_name text,
    created_at timestamptz not null default now(),
    last_login_at timestamptz,
    is_active boolean not null default true
);

create table if not exists categories (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    description text,
    is_active boolean not null default true,
    merged_into_category_id uuid references categories(id),
    created_by_user_id uuid not null references users(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists tickets (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    urgency int not null default 1,
    category_id uuid not null references categories(id),
    link text,
    file_url text,
    file_type text,
    description text,
    owner_user_id uuid not null references users(id),
    status text not null default 'open',
    solved_at timestamptz,
    deleted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    solved_by_user_id uuid references users(id),
    check (status in ('open', 'in_progress', 'solved', 'archived', 'deleted_soft'))
);

create table if not exists ticket_events (
    id bigserial primary key,
    ticket_id uuid references tickets(id),
    actor_user_id uuid not null references users(id),
    event_type text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table if not exists app_meta (
    key text primary key,
    value text,
    updated_by text,
    updated_at timestamptz not null default now()
);

create index if not exists idx_tickets_urgency on tickets (urgency desc);
create index if not exists idx_tickets_status on tickets (status);
create index if not exists idx_tickets_owner on tickets (owner_user_id);
create index if not exists idx_tickets_category on tickets (category_id);
create index if not exists idx_tickets_created_at on tickets (created_at desc);

-- ─────────────────────────────────────────────────────────────────────────────
-- Migration v2: in_progress status + solver tracking
-- Run these statements against an existing database.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Drop the old status check and recreate it with in_progress.
--    The auto-generated constraint name may differ; if the ALTER fails,
--    inspect with: \d tickets  and drop by actual name.
alter table tickets drop constraint if exists tickets_status_check;
alter table tickets
  add constraint tickets_status_check
  check (status in ('open', 'in_progress', 'solved', 'archived', 'deleted_soft'));

-- 2. Track who solved the ticket.
alter table tickets
  add column if not exists solved_by_user_id uuid references users(id);
