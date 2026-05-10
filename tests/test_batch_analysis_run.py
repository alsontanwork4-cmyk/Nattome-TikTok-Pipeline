import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.run import build_metadata, create_run


WORKSPACE = Path(__file__).resolve().parents[1]
SCRIPT = WORKSPACE / "batch_analysis" / "run_batch_analysis.py"


def run_cli(*args, cwd=WORKSPACE):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
    )


def candidate(temp_path: Path, **overrides):
    source_video = temp_path / f"{overrides.get('id', 'video')}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    payload = {
        "id": "source-video",
        "url": "https://www.tiktok.com/@creator/video/source",
        "video_download_url": str(source_video),
        "caption": "Bloating after meals gut health routine",
        "play_count": 120000,
        "like_count": 12000,
        "comment_count": 600,
        "share_count": 700,
        "created_at": "2026-05-05T00:00:00Z",
    }
    payload.update(overrides)
    return payload


class BatchAnalysisRunCliTest(unittest.TestCase):
    def test_build_metadata_is_source_video_boundary_only(self):
        signature = inspect.signature(build_metadata)

        self.assertIn("has_candidate_selection", signature.parameters)
        self.assertIn("has_source_video_snapshots", signature.parameters)

    def test_skeleton_run_creates_compact_two_layer_layout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_dir = Path(temp_dir) / "runs"

            result = run_cli(
                "--runs-dir",
                str(runs_dir),
                "--timestamp",
                "2026-05-06T13:45:30Z",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            run_folder = runs_dir / "20260506T214530+0800_daily"
            self.assertEqual(
                sorted(child.name for child in run_folder.iterdir() if child.is_dir()),
                ["data", "evidence", "logs", "reports"],
            )
            self.assertTrue((run_folder / "run_metadata.json").is_file())
            self.assertTrue((run_folder / "run_manifest.json").is_file())
            self.assertFalse((run_folder / "batch_index.md").exists())
            self.assertFalse((run_folder / "batch_outputs").exists())
            self.assertFalse((run_folder / "evidence_bundles").exists())

            metadata = json.loads((run_folder / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["run_timestamp"], "2026-05-06T21:45:30+08:00")
            self.assertEqual(metadata["implementation_status"]["candidate_selection"], "not_implemented")
            self.assertEqual(metadata["implementation_status"]["source_video_download"], "not_implemented")

    def test_candidates_are_selected_and_source_videos_are_snapshotted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            expected_run_folder = temp_path / "runs" / "20260506T214530+0800_daily"
            expected_run_folder.joinpath("data").mkdir(parents=True)
            expected_run_folder.joinpath("data", "raw_scrape_all.json").write_text(
                json.dumps({"top": []}),
                encoding="utf-8",
            )
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            candidate(temp_path, id="first-video", play_count=100000),
                            candidate(temp_path, id="second-video", play_count=90000),
                        ]
                    }
                ),
                encoding="utf-8",
            )

            run_folder = create_run(
                Namespace(
                    mode="daily",
                    batch_size=None,
                    runs_dir=temp_path / "runs",
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-06T13:45:30Z",
                )
            )

            self.assertEqual(run_folder, expected_run_folder)
            self.assertTrue((run_folder / "data" / "selected_batch.json").is_file())
            self.assertTrue((run_folder / "reports" / "selected_batch.md").is_file())
            self.assertTrue((run_folder / "data" / "evidence_bundle_index.json").is_file())
            self.assertEqual(len(list((run_folder / "data").glob("*_evidence_snapshot.json"))), 2)
            self.assertEqual(len(list((run_folder / "data").glob("*_source_metadata.json"))), 2)
            self.assertEqual(len(list((run_folder / "evidence").glob("*_source_video.mp4"))), 2)

            manifest = json.loads((run_folder / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_timestamp"], "2026-05-06T21:45:30+08:00")
            self.assertEqual(
                next(phase for phase in manifest["phases"] if phase["name"] == "source_video_snapshots")["status"],
                "completed",
            )

    def test_missing_explicit_config_fails_without_creating_run_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runs_dir = temp_path / "runs"

            result = run_cli(
                "--runs-dir",
                str(runs_dir),
                "--config",
                str(temp_path / "missing.json"),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("required config file not found", result.stderr)
            self.assertFalse(runs_dir.exists())


if __name__ == "__main__":
    unittest.main()
