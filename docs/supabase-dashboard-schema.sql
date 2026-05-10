-- Supabase schema for the Nattome FastAPI dashboard.
-- Run once in Supabase Dashboard -> SQL Editor.

insert into storage.buckets (id, name, public)
values ('dashboard-artifacts', 'dashboard-artifacts', false)
on conflict (id) do nothing;

create table if not exists public.runs (
  run_id text primary key,
  status text not null default 'queued',
  run_type text not null default '',
  mode text not null default '',
  started_at text not null default '',
  finished_at text not null default '',
  duration_seconds integer,
  triggered_by text not null default '',
  created_by text not null default '',
  error_summary text not null default '',
  raw_candidate_count integer not null default 0,
  eligible_candidate_count integer not null default 0,
  selected_count integer not null default 0,
  report_date text,
  summary text not null default '',
  created_at text not null default '',
  updated_at text not null default ''
);

create table if not exists public.run_outputs (
  run_id text not null references public.runs(run_id) on delete cascade,
  artifact_type text not null default '',
  bucket text not null default 'dashboard-artifacts',
  object_path text not null,
  filename text not null default '',
  content_type text not null default '',
  size_bytes bigint,
  checksum text,
  created_at text,
  primary key (run_id, object_path)
);

create table if not exists public.raw_videos (
  video_id text not null,
  run_id text not null references public.runs(run_id) on delete cascade,
  tiktok_url text not null default '',
  author_handle text not null default '',
  caption text not null default '',
  hashtags jsonb not null default '[]'::jsonb,
  source_input text not null default '',
  play_count bigint not null default 0,
  like_count bigint not null default 0,
  comment_count bigint not null default 0,
  share_count bigint not null default 0,
  created_at text not null default '',
  updated_at text not null default '',
  primary key (run_id, video_id)
);

create table if not exists public.selected_videos (
  run_id text not null references public.runs(run_id) on delete cascade,
  video_id text not null,
  selection_rank integer,
  selection_reason text not null default '',
  evidence_status text not null default '',
  created_at text not null default '',
  updated_at text not null default '',
  primary key (run_id, video_id)
);

create table if not exists public.scrape_settings_versions (
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

create table if not exists public.manual_runs (
  id text primary key,
  run_id text not null references public.runs(run_id) on delete cascade,
  status text not null default 'queued',
  run_type text not null default '',
  triggered_by text not null default '',
  requested_at text not null default '',
  claimed_at text,
  claimed_by text,
  finished_at text,
  expected_output_metadata jsonb not null default '[]'::jsonb,
  error_summary text not null default '',
  created_at text not null default '',
  updated_at text not null default ''
);

create index if not exists idx_runs_started_at on public.runs(started_at);
create index if not exists idx_run_outputs_run_id on public.run_outputs(run_id);
create index if not exists idx_manual_runs_status_requested_at
  on public.manual_runs(status, requested_at);
create index if not exists idx_raw_videos_play_count on public.raw_videos(play_count);
create unique index if not exists idx_scrape_settings_one_active
  on public.scrape_settings_versions(is_active)
  where is_active;
create unique index if not exists idx_agent_settings_one_active
  on public.agent_settings_versions(is_active)
  where is_active;

create or replace function public.save_scrape_settings_version(
  p_settings jsonb,
  p_reason text,
  p_created_by text,
  p_rollback_of_version integer default null
)
returns public.scrape_settings_versions
language plpgsql
as $$
declare
  next_version integer;
  now_text text;
  inserted public.scrape_settings_versions;
begin
  select coalesce(max(version), 0) + 1
    into next_version
    from public.scrape_settings_versions;

  now_text := now()::text;

  update public.scrape_settings_versions
     set is_active = false,
         updated_at = now_text
   where is_active = true;

  insert into public.scrape_settings_versions (
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
