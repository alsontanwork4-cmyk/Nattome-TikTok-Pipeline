from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from .evidence_io import (
    EvidenceBundleStore,
    prefixed_data_artifact_path,
    relative_path,
    write_json_object,
)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
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
    ):
        self.run_folder = run_folder
        self.api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name
        self.client_factory = client_factory or create_official_gemini_client
        self.brand_reference_path = brand_reference_path
        self.store = EvidenceBundleStore(run_folder)

    def run(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return self._result([], [], [], [])
        if not self.api_key:
            missing = [
                {
                    "candidate_id": candidate.get("id"),
                    "prefix": self.store.load_snapshot(candidate)["prefix"],
                    "status": "missing_credentials",
                    "reason": "GEMINI_API_KEY is not configured",
                }
                for candidate in candidates
            ]
            return self._result(missing, missing, missing, [])

        try:
            client = self.client_factory(self.api_key)
            brand_reference = self.brand_reference_path.read_text(encoding="utf-8")
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
        final_outputs: list[str] = []

        for candidate in candidates:
            per_video = self._run_video(client, candidate, brand_reference)
            evidence_records.append(per_video["evidence"])
            creative_records.append(per_video["creative"])
            report_records.append(per_video["report"])
            if per_video["report"].get("status") in ("completed", "skipped") and per_video["report"].get("path"):
                final_outputs.append(per_video["report"]["path"])

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
            return {
                "evidence": self._artifact_record(candidate, prefix, "skipped", evidence_path),
                "creative": self._artifact_record(candidate, prefix, "skipped", creative_path),
                "report": self._artifact_record(candidate, prefix, "skipped", report_path),
            }

        source_video = snapshot.get("source_video", {})
        if source_video.get("state") != "available" or not source_video.get("path"):
            reason = source_video.get("reason") or "source video is not available"
            failed = self._failure_record(candidate, prefix, reason)
            return {"evidence": failed, "creative": failed, "report": failed}

        try:
            video_path = self.run_folder / source_video["path"]
            uploaded_file = client.files.upload(file=str(video_path))
            evidence_response = client.models.generate_content(
                model=self.model_name,
                contents=[build_video_evidence_prompt(candidate), uploaded_file],
            )
            evidence_payload = {
                "agent": "gemini_video_evidence",
                "model_name": self.model_name,
                "candidate_id": candidate.get("id"),
                "prefix": prefix,
                "source_video": source_video["path"],
                "uploaded_file": self._uploaded_file_record(uploaded_file),
                "response": normalized_response(evidence_response),
            }
            write_json_object(evidence_path, evidence_payload)

            creative_response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    build_creative_strategy_prompt(
                        candidate,
                        evidence_payload["response"],
                        brand_reference,
                    )
                ],
            )
            creative_payload = {
                "agent": "gemini_creative_strategy",
                "model_name": self.model_name,
                "candidate_id": candidate.get("id"),
                "prefix": prefix,
                "inputs": {
                    "evidence": relative_path(evidence_path, self.run_folder),
                    "source_metadata": snapshot["source_metadata"]["path"],
                    "brand_reference": str(self.brand_reference_path.relative_to(WORKSPACE_ROOT)).replace("\\", "/"),
                },
                "response": normalized_response(creative_response),
            }
            write_json_object(creative_path, creative_payload)

            report_text = response_text(creative_response).rstrip() + "\n"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(report_text, encoding="utf-8")

            return {
                "evidence": self._artifact_record(candidate, prefix, "completed", evidence_path),
                "creative": self._artifact_record(candidate, prefix, "completed", creative_path),
                "report": {
                    **self._artifact_record(candidate, prefix, "completed", report_path),
                    "path": report_relative,
                },
            }
        except Exception as exc:
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
                    model_name=self.model_name,
                    inputs={"source_video_snapshots": "data/evidence_bundle_index.json"},
                    outputs={"artifacts": self._paths(evidence_records)},
                    failure_details=self._failures(evidence_records),
                ),
                phase_record(
                    "gemini_creative_strategy",
                    phase_status([record["status"] for record in creative_records]),
                    model_name=self.model_name,
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
                    model_name=self.model_name,
                    inputs={"creative_responses": self._paths(creative_records)},
                    outputs={"reports": final_outputs},
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

    def _paths(self, records: list[dict[str, Any]]) -> list[str]:
        return [record["path"] for record in records if record.get("path")]

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
        }


def generate_nattome_pov_reports(
    run_folder: Path,
    candidates: list[dict[str, Any]],
    *,
    api_key: str | None = None,
    model_name: str = DEFAULT_GEMINI_MODEL,
    client_factory: GeminiClientFactory | None = None,
) -> dict[str, Any]:
    return GeminiNattomePovReporter(
        run_folder,
        api_key=api_key,
        model_name=model_name,
        client_factory=client_factory,
    ).run(candidates)
