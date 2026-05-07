from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .tool_adapters import copy_or_download_video, source_video_filename


def read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def stable_evidence_prefix(candidate: dict[str, Any]) -> str:
    rank = int(candidate.get("rank") or 0)
    candidate_id = candidate.get("id") or f"rank-{rank}"
    token = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "-"
        for ch in str(candidate_id)
    )
    token = token.strip("-") or "unknown"
    return f"{rank:03d}_{token}"


def relative_path(path: Path, run_folder: Path) -> str:
    return str(path.relative_to(run_folder)).replace("\\", "/")


def prefixed_data_artifact_path(
    run_folder: Path,
    snapshot: dict[str, Any],
    artifact_name: str,
) -> Path:
    return run_folder / "data" / f"{snapshot['prefix']}_{artifact_name}.json"


def prefixed_report_path(
    run_folder: Path,
    snapshot: dict[str, Any],
    report_name: str,
) -> Path:
    return run_folder / "reports" / f"{snapshot['prefix']}_{report_name}.md"


def gemini_evidence_from_snapshot(
    run_folder: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    artifact = snapshot.get("artifacts", {}).get("gemini_evidence")
    if isinstance(artifact, dict):
        artifact_path = artifact.get("path")
        if artifact_path:
            loaded = read_json_object(run_folder / str(artifact_path))
            if isinstance(loaded, dict):
                return loaded
        status = str(artifact.get("state") or "missing")
        return {
            "status": status,
            "reason": artifact.get("reason") or "Gemini evidence is missing from the Evidence Bundle snapshot",
            "visual_observations": [],
            "visible_text": [],
            "spoken_content": [],
            "audio_cues": [],
            "hook_evidence": [],
            "claim_evidence": [],
            "missing_evidence": artifact.get("missing_evidence") or [
                "visual_observations",
                "visible_text",
                "spoken_content",
                "audio_cues",
                "hook_evidence",
                "claim_evidence",
            ],
        }
    return {
        "status": "missing",
        "reason": "Gemini evidence state is missing from the Evidence Bundle snapshot",
        "visual_observations": [],
        "visible_text": [],
        "spoken_content": [],
        "audio_cues": [],
        "hook_evidence": [],
        "claim_evidence": [],
        "missing_evidence": [
            "visual_observations",
            "visible_text",
            "spoken_content",
            "audio_cues",
            "hook_evidence",
            "claim_evidence",
        ],
    }


class EvidenceBundleStore:
    def __init__(self, run_folder: Path):
        self.run_folder = run_folder
        self.data_folder = run_folder / "data"
        self.evidence_folder = run_folder / "evidence"

    def source_metadata_path(self, candidate: dict[str, Any]) -> Path:
        return self.data_folder / f"{stable_evidence_prefix(candidate)}_source_metadata.json"

    def snapshot_path(self, candidate: dict[str, Any]) -> Path:
        return self.data_folder / f"{stable_evidence_prefix(candidate)}_evidence_snapshot.json"

    def gemini_evidence_path(self, candidate: dict[str, Any]) -> Path:
        return self.data_folder / f"{stable_evidence_prefix(candidate)}_gemini_evidence.json"

    def source_video_path(self, candidate: dict[str, Any]) -> Path:
        video_source = str(candidate.get("video_download_url") or "")
        filename = source_video_filename(video_source)
        return self.evidence_folder / f"{stable_evidence_prefix(candidate)}_{filename}"

    def write_source_snapshots(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.evidence_folder.mkdir(parents=True, exist_ok=True)

        snapshots = []
        for candidate in candidates:
            snapshots.append(self.write_source_snapshot(candidate))

        index = {
            "bundle_count": len(snapshots),
            "bundles": [
                {
                    "candidate_id": snapshot["candidate_id"],
                    "rank": snapshot["rank"],
                    "prefix": snapshot["prefix"],
                    "snapshot": snapshot["snapshot_path"],
                    "source_metadata": snapshot["source_metadata"]["path"],
                    "source_video": snapshot["source_video"]["path"],
                    "source_video_state": snapshot["source_video"]["state"],
                }
                for snapshot in snapshots
            ],
        }
        (self.data_folder / "evidence_bundle_index.json").write_text(
            json.dumps(index, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return index

    def write_source_snapshot(self, candidate: dict[str, Any]) -> dict[str, Any]:
        metadata_path = self.source_metadata_path(candidate)
        metadata_path.write_text(
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        video_source = str(candidate.get("video_download_url") or "")
        video_path = self.source_video_path(candidate)
        download_status = copy_or_download_video(video_source, video_path)
        if download_status.get("status") != "downloaded" and video_path.exists():
            video_path.unlink()

        source_video_state = self.source_video_state(download_status, video_path)
        snapshot = {
            "candidate_id": candidate.get("id") or f"rank-{candidate.get('rank')}",
            "rank": candidate.get("rank"),
            "prefix": stable_evidence_prefix(candidate),
            "snapshot_path": relative_path(self.snapshot_path(candidate), self.run_folder),
            "source_metadata": {
                "state": "available",
                "path": relative_path(metadata_path, self.run_folder),
            },
            "source_video": source_video_state,
            "artifacts": {
                "gemini_evidence": {
                    "state": "missing",
                    "path": None,
                    "reason": "Gemini evidence has not been captured in this slice",
                },
                "derived_evidence": {
                    "state": "missing",
                    "path": None,
                    "reason": "Derived evidence has not been captured in this slice",
                },
            },
        }
        self.snapshot_path(candidate).write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return snapshot

    def source_video_state(
        self,
        download_status: dict[str, Any],
        video_path: Path,
    ) -> dict[str, Any]:
        if download_status.get("status") == "downloaded":
            return {
                "state": "available",
                "path": relative_path(video_path, self.run_folder),
                "bytes": download_status.get("bytes"),
                "source": download_status.get("source"),
            }
        return {
            "state": "missing" if download_status.get("status") == "missing" else "failed",
            "path": None,
            "reason": download_status.get("reason", "source video artifact is unavailable"),
            "source": download_status.get("source"),
        }

    def load_snapshot(self, candidate: dict[str, Any]) -> dict[str, Any]:
        snapshot = read_json_object(self.snapshot_path(candidate))
        if snapshot is None:
            return {
                "candidate_id": candidate.get("id") or f"rank-{candidate.get('rank')}",
                "rank": candidate.get("rank"),
                "prefix": stable_evidence_prefix(candidate),
                "snapshot_path": relative_path(self.snapshot_path(candidate), self.run_folder),
                "source_metadata": {
                    "state": "missing",
                    "path": None,
                    "reason": "source metadata artifact is missing",
                },
                "source_video": {
                    "state": "missing",
                    "path": None,
                    "reason": "source video artifact is missing",
                },
                "artifacts": {},
            }
        return snapshot

    def write_gemini_evidence(
        self,
        candidate: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        evidence_path = self.gemini_evidence_path(candidate)
        evidence_path.write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        snapshot = self.load_snapshot(candidate)
        status = str(evidence.get("status") or "failed")
        snapshot.setdefault("artifacts", {})
        snapshot["artifacts"]["gemini_evidence"] = {
            "state": status,
            "path": relative_path(evidence_path, self.run_folder),
            "reason": evidence.get("reason"),
            "missing_evidence": evidence.get("missing_evidence", []),
        }
        self.snapshot_path(candidate).write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return snapshot
