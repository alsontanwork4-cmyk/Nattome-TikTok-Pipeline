-- Idempotent migration for existing Supabase dashboard projects.
-- Adds versioned Gemini agent settings with active-version semantics.

create table if not exists public.agent_settings_versions (
  version integer primary key,
  settings jsonb not null default '{}'::jsonb,
  reason text not null default '',
  is_active boolean not null default false,
  rollback_of_version integer,
  created_by text not null default '',
  updated_by text not null default '',
  created_at text not null default '',
  updated_at text not null default ''
);

create unique index if not exists idx_agent_settings_one_active
  on public.agent_settings_versions(is_active)
  where is_active;

create or replace function public.save_agent_settings_version(
  p_settings jsonb,
  p_reason text,
  p_created_by text,
  p_rollback_of_version integer default null
)
returns public.agent_settings_versions
language plpgsql
as $$
declare
  next_version integer;
  now_text text;
  inserted public.agent_settings_versions;
begin
  select coalesce(max(version), 0) + 1
    into next_version
    from public.agent_settings_versions;

  now_text := now()::text;

  update public.agent_settings_versions
     set is_active = false,
         updated_at = now_text
   where is_active = true;

  insert into public.agent_settings_versions (
    version,
    settings,
    reason,
    is_active,
    rollback_of_version,
    created_by,
    updated_by,
    created_at,
    updated_at
  )
  values (
    next_version,
    coalesce(p_settings, '{}'::jsonb),
    coalesce(p_reason, ''),
    true,
    p_rollback_of_version,
    coalesce(p_created_by, ''),
    coalesce(p_created_by, ''),
    now_text,
    now_text
  )
  returning * into inserted;

  return inserted;
end;
$$;

notify pgrst, 'reload schema';
