from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .evidence_io import (
    EvidenceBundleStore,
    prefixed_data_artifact_path,
    relative_path,
    write_json_object,
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_FILE_ACTIVE_TIMEOUT_SECONDS = 180
DEFAULT_FILE_ACTIVE_POLL_SECONDS = 2
COMPILED_REPORT_FILENAME = "nattome_batch_analysis_final_outputs.md"
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
NATTOME_BRAND_REFERENCE = (
    WORKSPACE_ROOT
    / "skills"
    / "nattome-tiktok-candidate-discovery"
    / "references"
    / "nattome_brand.md"
)
NATTOME_POV_REPORT_OUTLINE = """Preferred report outline:

## [Specific Nattome creative brief title for this video]

### Source Reference

- Creator: [creator handle when available]
- Source video: [TikTok URL]
- Views: [view count when available]
- Likes: [like count when available]
- Comments: [comment count when available]
- Shares: [share count when available]

### Inspiration Pattern

[Name the transferable creative pattern in one concise phrase.]

### Why This Works For Nattome Content

[Explain why the observed video pattern can become a claim-safe Nattome content idea.]

| Concept | Hook | Format | Why it works |
|---|---|---|---|
| [Concept name] | [Evidence-grounded hook rewrite] | [Shoot format] | [Why this works for Nattome] |

### Recommended Shoot

Recommended because: [why this is the best shoot to prioritize.]

Hook: [specific opening hook for the Nattome version.]

| Time | Scene | On-screen text | Exact line |
|---|---|---|---|
| 0-3s | [scene] | [overlay] | [spoken line] |
| 3-8s | [scene] | [overlay] | [spoken line] |
| 8-14s | [scene] | [overlay] | [spoken line] |
| 14-22s | [scene] | [overlay] | [spoken line] |
| 22-30s | [scene] | [overlay] | [spoken line] |

Adapt this outline when the evidence calls for a better marketer-facing structure, but keep the same level of specificity: source reference, why the pattern works, shootable concepts, and a practical shot-by-shot recommendation."""

GeminiClientFactory = Callable[[str], Any]


def create_official_gemini_client(api_key: str) -> Any:
    from google import genai

    return genai.Client(api_key=api_key)


def response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text
    if isinstance(response, dict) and isinstance(response.get("text"), str):
        return response["text"]
    return str(response)


def normalized_response(response: Any) -> dict[str, Any]:
    text = response_text(response)
    payload: dict[str, Any] = {"text": text}
    try:
        payload["json"] = json.loads(text)
    except json.JSONDecodeError:
        pass
    return payload


def build_video_evidence_prompt(candidate: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Video Evidence Analyst Agent",
            "",
            "Role:",
            "Watch one TikTok source video and extract observable evidence only.",
            "",
            "Input contract:",
            "- One uploaded source video.",
            "- Candidate metadata JSON below.",
            "",
            "Candidate metadata:",
            json.dumps(candidate, ensure_ascii=False, indent=2),
            "",
            "Output contract:",
            "Return JSON with these fields when available: timestamped_visual_observations, "
            "spoken_content_notes, visible_text, hook_evidence, pacing_editing_notes, "
            "emotional_triggers, creator_behavior, claim_evidence, uncertainty_notes.",
            "Use timestamps wherever possible. Distinguish observed visuals, spoken audio, "
            "visible text, pacing/editing, creator behavior, emotional triggers, hook "
            "structure, and claims. Do not infer unsupported clinical outcomes.",
        ]
    )


def build_creative_strategy_prompt(
    candidate: dict[str, Any],
    evidence: dict[str, Any],
    brand_reference: str,
) -> str:
    return "\n".join(
        [
            "Nattome Creative Strategist Agent",
            "",
            "Role:",
            "Write a marketer-facing Nattome POV inspiration report from the evidence.",
            "",
            "Input contract:",
            "- Evidence Analyst output JSON.",
            "- Candidate metadata JSON.",
            "- Full Nattome brand POV reference from skills/nattome-tiktok-candidate-discovery/references/nattome_brand.md.",
            "",
            "Mandatory Nattome context:",
            "Before writing the report, read and apply the full Nattome brand POV reference. "
            "Use it for product fit, audience avatar, voice, claim-safety boundaries, retail "
            "trust cues, and shoot-format judgment. Do not write generic digestive-health "
            "marketing advice that could belong to any brand.",
            "",
            "Creative direction:",
            "Use the preferred outline below as the default report shape, then adapt it only "
            "when the evidence calls for a better marketer-facing structure. Write the report "
            "specific, non-generic, useful to a marketer planning a shoot, grounded in "
            "observable video evidence or explicit Nattome brand guidance, and aligned with "
            "Nattome claim safety. Generate the final Markdown yourself; Python will not "
            "render these sections.",
            "",
            NATTOME_POV_REPORT_OUTLINE,
            "",
            "Claim safety:",
            "Do not invent clinical claims, product outcomes, doctor recommendations, "
            "guaranteed relief, cure language, or disease-prevention claims. If a "
            "recommendation cannot be grounded in evidence or the brand reference, leave it out.",
            "",
            "Evidence Analyst output:",
            json.dumps(evidence, ensure_ascii=False, indent=2),
            "",
            "Candidate metadata:",
            json.dumps(candidate, ensure_ascii=False, indent=2),
            "",
            "Nattome brand POV reference:",
            brand_reference,
        ]
    )


def phase_status(statuses: list[str]) -> str:
    if not statuses:
        return "skipped"
    if all(status == "disabled" for status in statuses):
        return "disabled"
    if all(status == "completed" for status in statuses):
        return "completed"
    if all(status == "skipped" for status in statuses):
        return "skipped"
    if any(status == "completed" for status in statuses):
        return "partial"
    if all(status == "missing_credentials" for status in statuses):
        return "missing_credentials"
    return "failed"


def phase_record(
    name: str,
    status: str,
    *,
    model_name: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    failure_details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "name": name,
        "status": status,
        "model_name": model_name,
        "inputs": inputs or {},
        "outputs": outputs or {},
    }
    if failure_details:
        record["failure_details"] = failure_details
    return record


class GeminiNattomePovReporter:
    def __init__(
        self,
        run_folder: Path,
        *,
        api_key: str | None = None,
        model_name: str = DEFAULT_GEMINI_MODEL,
        client_factory: GeminiClientFactory | None = None,
        brand_reference_path: Path = NATTOME_BRAND_REFERENCE,
        agent_settings: dict[str, Any] | None = None,
        trace_writer: Callable[[dict[str, Any]], Any] | None = None,
        trace_run_id: str = "",
        config_source: str = "defaults",
        config_version: int | None = None,
    ):
        self.run_folder = run_folder
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.client_factory = client_factory or create_official_gemini_client
        self.brand_reference_path = brand_reference_path
        self.store = EvidenceBundleStore(run_folder)
        self.agent_settings = self._validated_agent_settings(agent_settings)
        self.evidence_agent = self.agent_settings["agents"]["gemini_video_evidence"]
        self.creative_agent = self.agent_settings["agents"]["nattome_creative_strategy"]
        self.trace_writer = trace_writer
        self.trace_run_id = trace_run_id
        self.config_source = config_source
        self.config_version = config_version

    def run(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return self._result([], [], [], [])
        if not self.evidence_agent["enabled"]:
            disabled = []
            skipped = []
            for candidate in candidates:
                prefix = self.store.load_snapshot(candidate)["prefix"]
                self._instant_trace("gemini_video_evidence", candidate, prefix, "skipped", "disabled")
                self._instant_trace("gemini_creative_strategy", candidate, prefix, "skipped", "skipped")
                disabled.append(self._disabled_record(candidate, prefix))
                skipped.append(
                    self._skipped_record(
                        candidate,
                        prefix,
                        "Gemini Video Evidence Agent is disabled.",
                    )
                )
            return self._result(disabled, skipped, skipped, [])
        if not self.api_key:
            missing = []
            for candidate in candidates:
                prefix = self.store.load_snapshot(candidate)["prefix"]
                self._instant_trace(
                    "gemini_video_evidence",
                    candidate,
                    prefix,
                    "preflight",
                    "failed",
                    error_summary="GEMINI_API_KEY is not configured",
                )
                missing.append(
                    {
                    "candidate_id": candidate.get("id"),
                    "prefix": prefix,
                    "status": "missing_credentials",
                    "reason": "GEMINI_API_KEY is not configured",
                }
                )
            return self._result(missing, missing, missing, [])

        try:
            client = self.client_factory(self.api_key)
            brand_reference = (
                self.brand_reference_path.read_text(encoding="utf-8")
                if self.creative_agent["enabled"]
                else ""
            )
        except Exception as exc:
            failed = [
                self._failure_record(
                    candidate,
                    self.store.load_snapshot(candidate)["prefix"],
                    str(exc),
                )
                for candidate in candidates
            ]
            return self._result(failed, failed, failed, [])

        evidence_records: list[dict[str, Any]] = []
        creative_records: list[dict[str, Any]] = []
        report_records: list[dict[str, Any]] = []

        for candidate in candidates:
            per_video = self._run_video(client, candidate, brand_reference)
            evidence_records.append(per_video["evidence"])
            creative_records.append(per_video["creative"])
            report_records.append(per_video["report"])

        final_outputs = self._compile_final_report(report_records)
        return self._result(evidence_records, creative_records, report_records, final_outputs)

    def _run_video(
        self,
        client: Any,
        candidate: dict[str, Any],
        brand_reference: str,
    ) -> dict[str, dict[str, Any]]:
        snapshot = self.store.load_snapshot(candidate)
        prefix = snapshot["prefix"]
        evidence_path = prefixed_data_artifact_path(self.run_folder, snapshot, "gemini_evidence")
        creative_path = prefixed_data_artifact_path(self.run_folder, snapshot, "gemini_creative_response")
        report_path = self.run_folder / "reports" / f"{prefix}_nattome_pov_report.md"
        report_relative = relative_path(report_path, self.run_folder)

        if evidence_path.exists() and creative_path.exists() and report_path.exists():
            self._instant_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "skipped",
                "skipped",
                artifact_references=[relative_path(evidence_path, self.run_folder)],
            )
            self._instant_trace(
                "gemini_creative_strategy",
                candidate,
                prefix,
                "skipped",
                "skipped",
                artifact_references=[
                    relative_path(creative_path, self.run_folder),
                    relative_path(report_path, self.run_folder),
                ],
            )
            return {
                "evidence": self._artifact_record(candidate, prefix, "skipped", evidence_path),
                "creative": self._artifact_record(candidate, prefix, "skipped", creative_path),
                "report": self._artifact_record(candidate, prefix, "skipped", report_path),
            }
        if evidence_path.exists() and not self.creative_agent["enabled"]:
            self._instant_trace(
                "gemini_creative_strategy",
                candidate,
                prefix,
                "skipped",
                "disabled",
                error_summary="Nattome Creative Strategist Agent is disabled.",
            )
            return {
                "evidence": self._artifact_record(candidate, prefix, "skipped", evidence_path),
                "creative": self._disabled_record(candidate, prefix),
                "report": self._skipped_record(
                    candidate,
                    prefix,
                    "Nattome Creative Strategist Agent is disabled.",
                ),
            }

        source_video = snapshot.get("source_video", {})
        if source_video.get("state") != "available" or not source_video.get("path"):
            reason = source_video.get("reason") or "source video is not available"
            self._instant_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "uploading_video",
                "failed",
                error_summary=reason,
            )
            failed = self._failure_record(candidate, prefix, reason)
            return {"evidence": failed, "creative": failed, "report": failed}

        try:
            video_path = self.run_folder / source_video["path"]
            upload_trace = self._start_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "uploading_video",
            )
            uploaded_file = client.files.upload(file=str(video_path))
            self._finish_trace(
                upload_trace,
                "completed",
                uploaded_file=self._uploaded_file_record(uploaded_file),
            )
            wait_trace = self._start_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "waiting_for_file_active",
            )
            uploaded_file = self._wait_for_uploaded_file_active(client, uploaded_file)
            self._finish_trace(
                wait_trace,
                "completed",
                uploaded_file=self._uploaded_file_record(uploaded_file),
            )
            evidence_trace = self._start_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "generating_evidence",
            )
            evidence_response = client.models.generate_content(
                model=self.evidence_agent["model"],
                contents=[build_video_evidence_prompt(candidate), uploaded_file],
                config=self._generation_config(self.evidence_agent),
            )
            self._finish_trace(
                evidence_trace,
                "completed",
                usage_metadata=self._usage_metadata(evidence_response),
            )
            evidence_payload = {
                "agent": "gemini_video_evidence",
                "model_name": self.evidence_agent["model"],
                "candidate_id": candidate.get("id"),
                "prefix": prefix,
                "source_video": source_video["path"],
                "uploaded_file": self._uploaded_file_record(uploaded_file),
                "response": normalized_response(evidence_response),
            }
            evidence_artifact = relative_path(evidence_path, self.run_folder)
            write_trace = self._start_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "writing_artifacts",
            )
            write_json_object(evidence_path, evidence_payload)
            self._finish_trace(
                write_trace,
                "completed",
                artifact_references=[evidence_artifact],
            )

            if not self.creative_agent["enabled"]:
                self._instant_trace(
                    "gemini_creative_strategy",
                    candidate,
                    prefix,
                    "skipped",
                    "disabled",
                    error_summary="Nattome Creative Strategist Agent is disabled.",
                )
                return {
                    "evidence": self._artifact_record(candidate, prefix, "completed", evidence_path),
                    "creative": self._disabled_record(candidate, prefix),
                    "report": self._skipped_record(
                        candidate,
                        prefix,
                        "Nattome Creative Strategist Agent is disabled.",
                    ),
                }

            creative_trace = self._start_trace(
                "gemini_creative_strategy",
                candidate,
                prefix,
                "generating_creative_strategy",
            )
            creative_response = client.models.generate_content(
                model=self.creative_agent["model"],
                contents=[
                    build_creative_strategy_prompt(
                        candidate,
                        evidence_payload["response"],
                        brand_reference,
                    )
                ],
                config=self._generation_config(self.creative_agent),
            )
            self._finish_trace(
                creative_trace,
                "completed",
                usage_metadata=self._usage_metadata(creative_response),
            )
            creative_payload = {
                "agent": "gemini_creative_strategy",
                "model_name": self.creative_agent["model"],
                "candidate_id": candidate.get("id"),
                "prefix": prefix,
                "inputs": {
                    "evidence": relative_path(evidence_path, self.run_folder),
                    "source_metadata": snapshot["source_metadata"]["path"],
                    "brand_reference": str(self.brand_reference_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                },
                "response": normalized_response(creative_response),
            }
            creative_artifact = relative_path(creative_path, self.run_folder)
            report_artifact = report_relative
            write_creative_trace = self._start_trace(
                "gemini_creative_strategy",
                candidate,
                prefix,
                "writing_artifacts",
            )
            write_json_object(creative_path, creative_payload)

            report_text = response_text(creative_response).rstrip() + "\n"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")
            self._finish_trace(
                write_creative_trace,
                "completed",
                artifact_references=[creative_artifact, report_artifact],
            )
            completed_trace = self._start_trace(
                "gemini_creative_strategy",
                candidate,
                prefix,
                "completed",
            )
            self._finish_trace(
                completed_trace,
                "completed",
                artifact_references=[evidence_artifact, creative_artifact, report_artifact],
            )

            return {
                "evidence": self._artifact_record(candidate, prefix, "completed", evidence_path),
                "creative": self._artifact_record(candidate, prefix, "completed", creative_path),
                "report": {
                    **self._artifact_record(candidate, prefix, "completed", report_path),
                    "path": report_relative,
                },
            }
        except Exception as exc:
            self._instant_trace(
                "gemini_video_evidence",
                candidate,
                prefix,
                "failed",
                "failed",
                error_summary=str(exc),
            )
            failed = self._failure_record(candidate, prefix, str(exc))
            return {"evidence": failed, "creative": failed, "report": failed}

    def _result(
        self,
        evidence_records: list[dict[str, Any]],
        creative_records: list[dict[str, Any]],
        report_records: list[dict[str, Any]],
        final_outputs: list[str],
    ) -> dict[str, Any]:
        return {
            "phases": [
                phase_record(
                    "gemini_video_evidence",
                    phase_status([record["status"] for record in evidence_records]),
                    model_name=self.evidence_agent["model"],
                    inputs={"source_video_snapshots": "data/evidence_bundle_index.json"},
                    outputs={"artifacts": self._paths(evidence_records)},
                    failure_details=self._failures(evidence_records),
                ),
                phase_record(
                    "gemini_creative_strategy",
                    phase_status([record["status"] for record in creative_records]),
                    model_name=self.creative_agent["model"],
                    inputs={
                        "evidence": self._paths(evidence_records),
                        "brand_reference": str(self.brand_reference_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                    },
                    outputs={"artifacts": self._paths(creative_records)},
                    failure_details=self._failures(creative_records),
                ),
                phase_record(
                    "nattome_pov_reports",
                    phase_status([record["status"] for record in report_records]),
                    model_name=self.creative_agent["model"],
                    inputs={"creative_responses": self._paths(creative_records)},
                    outputs={
                        "reports": final_outputs,
                        "per_video_reports": self._paths(report_records),
                    },
                    failure_details=self._failures(report_records),
                ),
            ],
            "final_outputs": final_outputs,
        }

    def _artifact_record(
        self,
        candidate: dict[str, Any],
        prefix: str,
        status: str,
        path: Path,
    ) -> dict[str, Any]:
        return {
            "candidate_id": candidate.get("id"),
            "prefix": prefix,
            "status": status,
            "path": relative_path(path, self.run_folder),
        }

    def _failure_record(self, candidate: dict[str, Any], prefix: str, reason: str) -> dict[str, Any]:
        return {
            "candidate_id": candidate.get("id"),
            "prefix": prefix,
            "status": "failed",
            "reason": reason,
        }

    def _disabled_record(self, candidate: dict[str, Any], prefix: str) -> dict[str, Any]:
        return {
            "candidate_id": candidate.get("id"),
            "prefix": prefix,
            "status": "disabled",
            "reason": "agent is disabled",
        }

    def _skipped_record(self, candidate: dict[str, Any], prefix: str, reason: str) -> dict[str, Any]:
        return {
            "candidate_id": candidate.get("id"),
            "prefix": prefix,
            "status": "skipped",
            "reason": reason,
        }

    def _paths(self, records: list[dict[str, Any]]) -> list[str]:
        return [record["path"] for record in records if record.get("path")]

    def _compile_final_report(self, report_records: list[dict[str, Any]]) -> list[str]:
        available_reports = [
            record
            for record in report_records
            if record.get("status") in ("completed", "skipped") and record.get("path")
        ]
        if not available_reports:
            return []

        compiled_path = self.run_folder / "reports" / COMPILED_REPORT_FILENAME
        compiled_path.parent.mkdir(parents=True, exist_ok=True)
        sections = [
            "# Nattome Batch Analysis Final Outputs",
            "",
            "Compiled report for all generated Nattome POV video analyses.",
            "",
        ]
        for index, record in enumerate(available_reports, start=1):
            report_path = self.run_folder / str(record["path"])
            if not report_path.exists():
                continue
            report_text = report_path.read_text(encoding="utf-8").strip()
            sections.extend(
                [
                    f"## Video {index}: {record.get('prefix') or record.get('candidate_id')}",
                    "",
                    f"- Source report: `{record['path']}`",
                    "",
                    report_text,
                    "",
                ]
            )

        compiled_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
        return [relative_path(compiled_path, self.run_folder)]

    def _failures(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "candidate_id": record.get("candidate_id"),
                "prefix": record.get("prefix"),
                "status": record.get("status"),
                "reason": record.get("reason"),
            }
            for record in records
            if record.get("status") in ("failed", "missing_credentials")
        ]

    def _uploaded_file_record(self, uploaded_file: Any) -> dict[str, Any]:
        if isinstance(uploaded_file, dict):
            return uploaded_file
        return {
            "uri": getattr(uploaded_file, "uri", None),
            "name": getattr(uploaded_file, "name", None),
            "mime_type": getattr(uploaded_file, "mime_type", None),
            "state": self._file_state_name(uploaded_file),
        }

    def _wait_for_uploaded_file_active(self, client: Any, uploaded_file: Any) -> Any:
        name = self._uploaded_file_name(uploaded_file)
        if not name or not hasattr(client.files, "get"):
            return uploaded_file

        deadline = time.monotonic() + DEFAULT_FILE_ACTIVE_TIMEOUT_SECONDS
        current_file = uploaded_file
        while time.monotonic() < deadline:
            state = self._file_state_name(current_file)
            if state in ("ACTIVE", "STATE_ACTIVE"):
                return current_file
            if state in ("FAILED", "STATE_FAILED"):
                raise RuntimeError(f"Gemini uploaded file {name} failed processing")
            time.sleep(DEFAULT_FILE_ACTIVE_POLL_SECONDS)
            current_file = client.files.get(name=name)

        state = self._file_state_name(current_file) or "unknown"
        raise TimeoutError(
            f"Gemini uploaded file {name} did not become ACTIVE within "
            f"{DEFAULT_FILE_ACTIVE_TIMEOUT_SECONDS}s; state={state}"
        )

    def _uploaded_file_name(self, uploaded_file: Any) -> str | None:
        if isinstance(uploaded_file, dict):
            name = uploaded_file.get("name")
            return str(name) if name else None
        name = getattr(uploaded_file, "name", None)
        return str(name) if name else None

    def _file_state_name(self, uploaded_file: Any) -> str | None:
        if isinstance(uploaded_file, dict):
            state = uploaded_file.get("state")
        else:
            state = getattr(uploaded_file, "state", None)
        if state is None:
            return None
        name = getattr(state, "name", None)
        return str(name or state)

    def _start_trace(
        self,
        agent: str,
        candidate: dict[str, Any],
        prefix: str,
        substep: str,
    ) -> dict[str, Any] | None:
        if self.trace_writer is None:
            return None
        now = _iso_now()
        event = {
            "event_id": str(uuid4()),
            "run_id": self.trace_run_id,
            "agent": agent,
            "candidate_id": str(candidate.get("id") or ""),
            "candidate_prefix": prefix,
            "substep": substep,
            "status": "running",
            "started_at": now,
            "ended_at": None,
            "duration_ms": None,
            "config_source": self.config_source,
            "config_version": self.config_version,
            "artifact_references": [],
            "uploaded_file": {},
            "usage_metadata": {},
            "error_summary": "",
            "created_at": now,
            "updated_at": now,
        }
        self._write_trace(event)
        return event

    def _finish_trace(
        self,
        event: dict[str, Any] | None,
        status: str,
        *,
        artifact_references: list[str] | None = None,
        uploaded_file: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        error_summary: str = "",
    ) -> None:
        if event is None:
            return
        ended_at = _iso_now()
        event.update(
            {
                "status": status,
                "ended_at": ended_at,
                "duration_ms": _duration_ms(event["started_at"], ended_at),
                "artifact_references": artifact_references or [],
                "uploaded_file": _compact_json_object(uploaded_file),
                "usage_metadata": _compact_json_object(usage_metadata),
                "error_summary": _sanitize_trace_error(error_summary),
                "updated_at": ended_at,
            }
        )
        self._write_trace(event)

    def _instant_trace(
        self,
        agent: str,
        candidate: dict[str, Any],
        prefix: str,
        substep: str,
        status: str,
        *,
        artifact_references: list[str] | None = None,
        uploaded_file: dict[str, Any] | None = None,
        usage_metadata: dict[str, Any] | None = None,
        error_summary: str = "",
    ) -> None:
        event = self._start_trace(agent, candidate, prefix, substep)
        self._finish_trace(
            event,
            status,
            artifact_references=artifact_references,
            uploaded_file=uploaded_file,
            usage_metadata=usage_metadata,
            error_summary=error_summary,
        )

    def _write_trace(self, event: dict[str, Any]) -> None:
        if self.trace_writer is None:
            return
        self.trace_writer(dict(event))

    def _usage_metadata(self, response: Any) -> dict[str, Any]:
        usage = getattr(response, "usage_metadata", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage_metadata") or response.get("usageMetadata")
        if usage is None:
            return {}
        if isinstance(usage, dict):
            return _compact_json_object(usage)
        to_dict = getattr(usage, "to_dict", None)
        if callable(to_dict):
            return _compact_json_object(to_dict())
        return {}

    def _generation_config(self, agent: dict[str, Any]) -> dict[str, Any]:
        generation = {
            key: value
            for key, value in dict(agent.get("generation") or {}).items()
            if value is not None
        }
        generation.update(dict(agent.get("advanced_generation_config") or {}))
        return generation

    def _validated_agent_settings(self, agent_settings: dict[str, Any] | None) -> dict[str, Any]:
        from dashboard.agent_settings import DEFAULT_AGENT_SETTINGS, validate_agent_settings

        return validate_agent_settings(agent_settings or DEFAULT_AGENT_SETTINGS)


def generate_nattome_pov_reports(
    run_folder: Path,
    candidates: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    model_name: str = DEFAULT_GEMINI_MODEL,
    client_factory: GeminiClientFactory | None = None,
    agent_settings: dict[str, Any] | None = None,
    trace_writer: Callable[[dict[str, Any]], Any] | None = None,
    trace_run_id: str = "",
    config_source: str = "defaults",
    config_version: int | None = None,
) -> dict[str, Any]:
    return GeminiNattomePovReporter(
        run_folder,
        api_key=api_key,
        model_name=model_name,
        client_factory=client_factory,
        agent_settings=agent_settings,
        trace_writer=trace_writer,
        trace_run_id=trace_run_id,
        config_source=config_source,
        config_version=config_version,
    ).run(candidates)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _duration_ms(started_at: str, ended_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
    except ValueError:
        return 0
    return max(0, int((end - start).total_seconds() * 1000))


def _sanitize_trace_error(value: object) -> str:
    from dashboard.runtime import sanitize_error_summary

    return sanitize_error_summary(value)


def _compact_json_object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if item in (None, ""):
            continue
        text = str(item)
        if "\\" in text or ":/" in text:
            if str(key) not in {"uri", "name", "mime_type", "state"}:
                continue
        compact[str(key)] = item
    return compact
