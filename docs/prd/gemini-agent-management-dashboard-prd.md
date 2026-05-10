# Gemini Agent Management Dashboard PRD

## Problem Statement

The Nattome TikTok Source Video Pipeline now depends on two Gemini-powered agents: the Gemini Video Evidence Agent and the Nattome Creative Strategist Agent. Their prompts and generation settings currently live in code, which makes tuning agent behavior slow, opaque, and difficult to audit.

When a batch run is executing, the dashboard also does not show live agent-level progress. A user cannot tell which Gemini agent is running, which candidate it is processing, how long it has been running, whether it is waiting on Gemini file activation, or which settings produced a particular report.

The dashboard needs a dedicated Agents section that lets authenticated users manage the two fixed Gemini agents, inspect their live state, and review compact trace history without turning the pipeline into a generic external agent framework.

## Solution

Add a new authenticated Agents dashboard section under Controls, above Scrape Settings. The section manages only the two fixed Gemini agents:

- Gemini Video Evidence Agent
- Nattome Creative Strategist Agent

The page provides three main views: Configuration, Live Runs, and Trace History. It also includes a small stateful CSS/SVG mascot at the top that reflects the overall agent system status.

Agent configuration is versioned in Supabase, with the same audit style as scrape settings. The local CLI path also supports agent config through a local JSON fallback and built-in defaults, normalized through the same validation layer. Future runs snapshot the resolved config and config version so old outputs can be understood against the exact prompts and Gemini SDK settings used.

Live tracing writes compact structured events directly to Supabase during execution. The dashboard polls these events and computes elapsed time for running agents from the event timestamps. Full Gemini response text remains in artifacts, while trace rows store compact metadata and artifact references.

## User Stories

1. As a dashboard user, I want an Agents navigation item above Scrape Settings, so that agent controls are easy to find.
2. As a dashboard user, I want the Agents page to manage only the two existing Gemini agents, so that the UI stays focused and understandable.
3. As a marketer tuning reports, I want to edit the Gemini Video Evidence Agent separately from the Creative Strategist Agent, so that evidence extraction and creative writing can be improved independently.
4. As a marketer tuning prompts, I want prompts split into structured sections, so that I can change one part without accidentally deleting safety rules or output contracts.
5. As a dashboard user, I want a compiled prompt preview, so that I can inspect the exact prompt Gemini will receive.
6. As an operator, I want each agent to have an enabled or disabled state, so that I can temporarily stop part of the Gemini pipeline.
7. As an operator, I want disabling the Video Evidence Agent to skip the full Gemini reporting chain, so that the dependent Creative Strategist does not run without evidence.
8. As an operator, I want disabling only the Creative Strategist Agent to still allow evidence extraction, so that I can collect evidence without generating Nattome POV reports.
9. As an agent tuner, I want polished controls for common Gemini SDK settings, so that routine edits do not require raw JSON.
10. As an advanced user, I want an advanced JSON field for less common Gemini SDK config, so that any supported Gemini generation option can still be configured.
11. As an operator, I want validation errors before saving, so that invalid configs do not reach production runs.
12. As an operator, I want advanced JSON conflicts with polished fields to be rejected, so that saved behavior is explicit.
13. As a security-conscious user, I want Gemini API keys to stay outside the dashboard, so that secret handling remains environment-based.
14. As an authenticated dashboard user, I want to save agent config with a reason, so that future users understand why prompts or settings changed.
15. As a dashboard user, I want agent config version history, so that I can see prior changes.
16. As a dashboard user, I want rollback for agent config, so that I can restore a previous known-good version.
17. As an auditor, I want each config version to record who created it and when, so that changes are traceable.
18. As a local CLI user, I want local batch runs to use a local agent config fallback, so that local runs do not require Supabase.
19. As a pipeline operator, I want missing config to use built-in defaults, so that runs can still proceed from a clean environment.
20. As a pipeline operator, I want invalid active config to fail before Gemini is called, so that bad configuration is visible and quota is not wasted.
21. As an auditor, I want every run to snapshot the resolved agent config, so that old runs remain explainable after future prompt changes.
22. As an auditor, I want the run manifest to record config source and version, so that I can connect outputs to the active settings at run time.
23. As a dashboard user, I want live agent status rows, so that I can see whether each agent is idle, queued, running, failed, disabled, or last succeeded.
24. As a dashboard user, I want to see the currently running candidate, so that I know which video is being processed.
25. As a dashboard user, I want elapsed running time, so that I can tell how long an agent has been active.
26. As a dashboard user, I want substep status such as uploading video, waiting for file activation, generating evidence, generating creative strategy, and writing artifacts, so that long waits are explainable.
27. As a dashboard user, I want the page to auto-refresh while agents are running, so that I do not need to manually reload constantly.
28. As a dashboard user, I want a manual refresh path, so that I can force a status update.
29. As an operator, I want live traces written directly to Supabase during execution, so that the dashboard can show progress before the run completes.
30. As an operator, I want trace rows to exclude API keys, raw environment values, and full local filesystem paths, so that traces do not leak sensitive data.
31. As an operator, I want compact trace rows with artifact references, so that database queries stay fast.
32. As an auditor, I want full Gemini responses to remain in artifacts, so that detailed debugging is still possible.
33. As a dashboard user, I want Trace History for recent agent events, so that I can inspect prior failures and completions.
34. As a dashboard user, I want each run detail page to include a compact Agent Trace tab, so that I can inspect traces in run context.
35. As a dashboard user, I want the Agents page to show cross-run live and historical traces, so that I can monitor the agent system globally.
36. As a dashboard user, I want the small mascot to reflect overall status, so that the page has a quick human-readable signal.
37. As a dashboard user, I want the mascot to prioritize failed, running, queued, disabled, then idle states, so that important states surface first.
38. As a dashboard user, I want failed state to clear when a newer event for the same agent starts or succeeds, so that stale failures do not permanently dominate the page.
39. As a dashboard user, I want latest error summaries to remain visible in rows and history, so that failures are still discoverable after the mascot clears.
40. As a product owner, I want the first build to avoid rerun controls, so that future-run configuration and live observability can ship first.
41. As a product owner, I want no dashboard Gemini smoke-test button, so that config editing does not spend Gemini quota.
42. As a deployment owner, I want both fresh schema docs and an idempotent migration, so that new and existing Supabase projects can adopt the feature.
43. As a maintainer, I want tests around validation, config persistence, prompt compilation, trace writes, and route rendering, so that the feature can evolve safely.

## Implementation Decisions

- Add a dedicated Agents dashboard section under Controls, ordered above Scrape Settings.
- Manage exactly two fixed agent definitions: Gemini Video Evidence Agent and Nattome Creative Strategist Agent.
- Keep the Nattome brand reference fixed. It may appear in metadata and compiled prompt preview, but is not editable from the Agents page.
- Store production agent configuration in a Supabase versioned table with active-version semantics, save reason, creator identity, rollback source, and timestamps.
- Provide built-in defaults and a local JSON fallback for local CLI runs when Supabase is unavailable.
- Normalize Supabase config, local JSON config, and built-in defaults into one resolved config shape before the Gemini pipeline uses it.
- Validate required prompt sections, model names, numeric ranges, advanced JSON object shape, and allowed Gemini generation config keys before saving.
- Reject conflicts between polished form fields and advanced JSON keys instead of applying silent precedence.
- Keep `GEMINI_API_KEY` environment-based and out of dashboard configuration.
- Snapshot resolved agent config into each run and record config source/version in the run manifest.
- Apply config changes only to future runs. Do not add rerun controls in the first build.
- Extend Gemini orchestration so the Evidence Agent and Creative Strategist Agent can be enabled, disabled, configured, and traced independently while preserving their dependency order.
- If the Evidence Agent is disabled, skip the full Gemini reporting chain. If the Creative Strategist Agent is disabled, run evidence extraction and skip report generation.
- Add direct Supabase trace writes from the worker/runtime during agent execution. Do not rely on post-run artifact upload for live visibility.
- Store trace events as compact structured rows containing run id, agent name, candidate reference, substep, status, timestamps, duration fields when complete, config version/source, artifact references, uploaded file metadata, response usage metadata when exposed, and sanitized error summaries.
- Do not store API keys, raw environment values, full local filesystem paths, or full Gemini response text in trace rows.
- Keep full Gemini responses and reports in existing JSON/Markdown artifacts.
- Use polling refresh for live UI. Do not add websockets or server-sent events in the first build.
- Add a compact Agent Trace tab to run detail pages, filtered to that run.
- Add a small CSS/SVG mascot at the top of the Agents page. It reflects overall system status using the priority order failed, running, queued, disabled, idle.
- Design trace retention for future cleanup around 30 days or 5000 events, but do not build cleanup in this first slice.
- Update the full Supabase schema documentation and add an idempotent migration for existing deployments.

## Testing Decisions

- Tests should verify external behavior: saved configuration shape, validation outcomes, route responses, trace records written, and manifest/artifact outputs. They should not lock tests to internal helper structure.
- Add focused unit tests for agent config normalization, default fallback, local JSON fallback, prompt compilation, advanced JSON validation, and polished-field conflict rejection.
- Add Gemini reporter tests with fake Gemini clients for enabled/disabled agent combinations, config snapshotting, invalid config failure before Gemini calls, and trace event sequencing.
- Add dashboard route tests for authenticated Agents page rendering, saving a new version, validation failure rendering, rollback behavior, live status rows, trace history, and run-detail Agent Trace tab.
- Add Supabase client boundary tests using fakes for agent settings version methods and trace event upserts.
- Add schema contract tests so new Supabase tables and expected fields remain aligned with the documented dashboard contract.
- Reuse existing testing style from dashboard settings, worker, run publication, FastAPI route, and Gemini reporter tests.

## Out of Scope

- Adding or removing arbitrary future agents.
- Building a generic external agent framework.
- Editing the Nattome brand reference from the Agents page.
- Storing Gemini API keys or other secrets in dashboard-managed config.
- Running a Gemini smoke test from the dashboard.
- Rerunning past runs or candidates with new agent settings.
- Websocket or server-sent event streaming.
- Trace retention cleanup jobs.
- Storing full Gemini response text directly in Supabase trace rows.
- Role-based admin permissions beyond the current authenticated-user model.

## Further Notes

- The feature should preserve the existing Supabase-first FastAPI architecture: authenticated Jinja dashboard pages, Supabase Postgres metadata, Supabase Storage artifacts, and a separate worker for long-running pipeline execution.
- The dashboard visual treatment should follow the existing operational style. The mascot should be small and useful, not a redesign of the page.
- Python remains the orchestration and storage layer. Gemini remains responsible for evidence interpretation, creative framing, and marketer-facing Nattome POV wording.
- Missing config is safe to default. Invalid active config is not safe to ignore and should fail visibly before a Gemini call.
