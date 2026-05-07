import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from batch_analysis.evidence_io import EvidenceBundleStore
from batch_analysis.run import create_run


def selected_candidate(candidate_id, rank, **overrides):
    candidate = {
        "id": candidate_id,
        "rank": rank,
        "url": f"https://www.tiktok.com/@creator/video/{candidate_id}",
        "caption": "Acid reflux and bloating routine",
        "video_download_url": "",
    }
    candidate.update(overrides)
    return candidate


class EvidenceBundleStoreTest(unittest.TestCase):
    def test_writes_flat_prefixed_source_artifacts_and_loads_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            run_folder = temp_path / "run"
            for child in ("reports", "data", "evidence", "logs"):
                (run_folder / child).mkdir(parents=True)

            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            candidates = [
                selected_candidate(
                    "video-alpha",
                    1,
                    video_download_url=str(source_video),
                ),
                selected_candidate("missing/video", 2),
            ]

            store = EvidenceBundleStore(run_folder)
            index = store.write_source_snapshots(candidates)

            self.assertEqual(index["bundle_count"], 2)
            self.assertEqual(
                [bundle["prefix"] for bundle in index["bundles"]],
                ["001_video-alpha", "002_missing-video"],
            )

            metadata_path = run_folder / "data" / "001_video-alpha_source_metadata.json"
            source_path = run_folder / "evidence" / "001_video-alpha_source_video.mp4"
            snapshot_path = run_folder / "data" / "001_video-alpha_evidence_snapshot.json"
            self.assertTrue(metadata_path.is_file())
            self.assertEqual(source_path.read_bytes(), b"fake mp4 bytes")
            self.assertTrue(snapshot_path.is_file())
            self.assertTrue((run_folder / "data" / "evidence_bundle_index.json").is_file())

            loaded = store.load_snapshot(candidates[0])
            self.assertEqual(loaded["candidate_id"], "video-alpha")
            self.assertEqual(loaded["source_metadata"]["state"], "available")
            self.assertEqual(loaded["source_metadata"]["path"], "data/001_video-alpha_source_metadata.json")
            self.assertEqual(loaded["source_video"]["state"], "available")
            self.assertEqual(loaded["source_video"]["path"], "evidence/001_video-alpha_source_video.mp4")
            self.assertEqual(loaded["source_video"]["bytes"], len(b"fake mp4 bytes"))

            missing = store.load_snapshot(candidates[1])
            self.assertEqual(missing["candidate_id"], "missing/video")
            self.assertEqual(missing["source_video"]["state"], "missing")
            self.assertIn("no downloadable video source", missing["source_video"]["reason"])
            self.assertIsNone(missing["source_video"]["path"])

            snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot_payload, loaded)

            nested_directories = [
                path.relative_to(run_folder)
                for path in run_folder.rglob("*")
                if path.is_dir() and len(path.relative_to(run_folder).parts) > 1
            ]
            self.assertEqual(nested_directories, [])

    def test_selected_batch_run_writes_flat_evidence_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_video = temp_path / "source.mp4"
            source_video.write_bytes(b"fake mp4 bytes")
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps(
                    {
                        "top": [
                            {
                                "id": "selected-video",
                                "url": "https://www.tiktok.com/@creator/video/selected",
                                "video_download_url": str(source_video),
                                "caption": "Acid reflux and bloating routine",
                                "play_count": 100000,
                                "like_count": 10000,
                                "comment_count": 500,
                                "share_count": 600,
                                "created_at": "2026-05-05T00:00:00Z",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            run_folder = create_run(
                Namespace(
                    mode="debug",
                    batch_size=1,
                    runs_dir=temp_path / "runs",
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-06T13:45:30Z",
                )
            )

            snapshot = json.loads(
                (run_folder / "data" / "001_selected-video_evidence_snapshot.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(snapshot["candidate_id"], "selected-video")
            self.assertEqual(snapshot["source_video"]["state"], "available")
            self.assertTrue((run_folder / "data" / "001_selected-video_source_metadata.json").is_file())
            self.assertEqual(
                (run_folder / "evidence" / "001_selected-video_source_video.mp4").read_bytes(),
                b"fake mp4 bytes",
            )


if __name__ == "__main__":
    unittest.main()
