-- SmartOps Agent - Supabase schema
-- Run this in the Supabase SQL editor (Dashboard > SQL Editor > New query)

-- 1. Profiles table (extends auth.users)
--    New users are assigned 'pending' until an admin promotes them.
--    The backend (auth.py) only allows roles in ALLOWED_ROLES = {commercial, delivery, admin};
--    'pending' is rejected, forcing explicit promotion before any API access.
create table if not exists public.profiles (
  id            uuid primary key references auth.users(id) on delete cascade,
  email         text not null default '',
  display_name  text not null default '',
  role          text not null default 'pending'
                check (role in ('pending', 'commercial', 'delivery', 'admin')),
  created_at    timestamptz not null default now()
);

-- crm_member_id links this Supabase user to a team member row in the CRM (tm_XXXXXXXX).
-- Set by an admin after creating the user. Used by the agent loop to enforce per-user
-- access control on commission calculations without asking "who are you?".
alter table public.profiles add column if not exists crm_member_id text;

-- 2. Row Level Security
alter table public.profiles enable row level security;

-- Users can read their own profile
drop policy if exists "users_read_own_profile" on public.profiles;
create policy "users_read_own_profile"
  on public.profiles for select
  using (auth.uid() = id);

-- Users can update their own display_name only (not role, not crm_member_id).
-- Column-level grants restrict the writable columns; the policy gates the row.
-- crm_member_id is intentionally excluded: only the service role (backend/admin) may set it.
drop policy if exists "users_update_own_display_name" on public.profiles;
create policy "users_update_own_display_name"
  on public.profiles for update
  using (auth.uid() = id)
  with check (
    role = (select role from public.profiles where id = auth.uid())
    and crm_member_id is not distinct from (select crm_member_id from public.profiles where id = auth.uid())
  );

-- Revoke broad UPDATE from authenticated users and grant only display_name.
-- This prevents any client from touching role or crm_member_id even if the policy above
-- were misconfigured. The backend uses service_role_key which bypasses these grants.
revoke update on public.profiles from authenticated;
grant update (display_name) on public.profiles to authenticated;

-- Admins can read all profiles (needed by backend service role, not enforced here)
-- The backend uses service_role_key which bypasses RLS.

-- 3. Auto-create profile on signup
-- Change this to your organisation's email domain (or remove the check to allow any domain)
-- and restart the function after editing.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer
set search_path = public
as $$
declare
  _allowed_domain text := '';  -- set to e.g. 'smartara.com' to restrict by domain, or leave empty to allow any email
begin
  -- Optional domain gate: reject sign-ups from outside the org.
  -- Comment out the two lines below if you want to allow any email and rely on admin promotion.
  if _allowed_domain <> '' and new.email not like ('%@' || _allowed_domain) then
    raise exception 'Registration restricted to % addresses.', _allowed_domain;
  end if;

  insert into public.profiles (id, email, display_name, role)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(
      new.raw_user_meta_data->>'display_name',
      split_part(coalesce(new.email, ''), '@', 1),
      ''
    ),
    'pending'
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 4. App-level settings (admin-writable key-value store, used for runtime overrides)
--    Currently stores: groq_api_key (overrides GROQ_API_KEY env var without redeploying)
create table if not exists public.app_settings (
  key         text primary key,
  value       text not null default '',
  updated_at  timestamptz not null default now()
);

alter table public.app_settings enable row level security;
-- No client-side policies; the backend uses service_role_key which bypasses RLS.

-- 5. To promote a user to admin, run:
--    update public.profiles set role = 'admin' where email = 'admin@example.com';
-- To promote to delivery:
--    update public.profiles set role = 'delivery' where email = 'user@example.com';
