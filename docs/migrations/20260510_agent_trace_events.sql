-- Idempotent migration for live Gemini agent trace events.

create table if not exists public.agent_trace_events (
  event_id text primary key,
  run_id text not null default '',
  agent text not null default '',
  candidate_id text not null default '',
  candidate_prefix text not null default '',
  substep text not null default '',
  status text not null default '',
  started_at text not null default '',
  ended_at text,
  duration_ms integer,
  config_source text not null default '',
  config_version integer,
  artifact_references jsonb not null default '[]'::jsonb,
  uploaded_file jsonb not null default '{}'::jsonb,
  usage_metadata jsonb not null default '{}'::jsonb,
  error_summary text not null default '',
  created_at text not null default '',
  updated_at text not null default ''
);

create index if not exists idx_agent_trace_events_run_started
  on public.agent_trace_events(run_id, started_at desc);
create index if not exists idx_agent_trace_events_recent
  on public.agent_trace_events(started_at desc);

notify pgrst, 'reload schema';
