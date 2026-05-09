import json
import tempfile
import unittest
import zipfile
from argparse import Namespace
from pathlib import Path
from xml.etree import ElementTree

from batch_analysis.planning_workbook import write_top5_angle_planning_workbook
from batch_analysis.run import create_run


SPREADSHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def candidate(temp_path: Path, index: int, **overrides):
    source_video = temp_path / f"source-{index}.mp4"
    source_video.write_bytes(b"fake mp4 bytes")
    payload = {
        "id": f"video-{index}",
        "rank": index,
        "url": f"https://www.tiktok.com/@creator{index}/video/{index}",
        "video_download_url": str(source_video),
        "author_handle": f"creator{index}",
        "caption": f"Bloating after meals routine {index}",
        "play_count": 100000 + index,
        "like_count": 10000 + index,
        "comment_count": 500 + index,
        "share_count": 700 + index,
        "created_at": "2026-05-05T00:00:00Z",
        "weighted_engagement_rate": 0.12,
        "nattome_relevance_score": 0.75,
        "selection_score": 0.82,
        "audio_format_hint": "talking_head",
        "visible_text_expected": True,
    }
    payload.update(overrides)
    return payload


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def snapshot(candidate_id: str, rank: int):
    prefix = f"{rank:03d}_{candidate_id}"
    return {
        "candidate_id": candidate_id,
        "rank": rank,
        "prefix": prefix,
        "artifacts": {
            "baseline_audio_analysis": {"path": f"data/{prefix}_baseline_audio_analysis.json"},
            "claim_safety_review": {"path": f"data/{prefix}_claim_safety_review.json"},
            "evidence_quality": {"path": f"data/{prefix}_evidence_quality.json"},
            "shootable_angles": {"path": f"data/{prefix}_shootable_angles.json"},
        },
    }


def angles(prefix: str):
    return {
        "status": "completed",
        "angles": [
            {
                "angle_title": f"{prefix} Daily Digestive Check",
                "hook": "Ask what changed after meals.",
                "format": "Talking-head explainer",
                "recommendation": "Convert the discomfort moment into routine support.",
                "recommended_because": "It is the clearest low-lift way to turn the source tension into a Nattome retail education moment.",
                "priority_score": {
                    "dimensions": {
                        "viral_strength": 4,
                        "nattome_relevance": 4,
                        "evidence_confidence": 5,
                        "brand_safety": 5,
                        "ease_of_production": 5,
                        "product_fit": 5,
                    },
                    "total": 28,
                    "max_points": 30,
                },
                "timed_script": [{"exact_line": "FORBIDDEN FULL SCRIPT LINE"}],
                "cta": "FORBIDDEN CTA LINE",
            },
            {
                "angle_title": f"{prefix} Claim-Safe Overlay",
                "hook": "Turn the source tension into a safer question.",
                "format": "Text-led explainer",
                "recommendation": "Keep the tension, remove outcome promises.",
            },
            {
                "angle_title": f"{prefix} Voiceover Routine",
                "hook": "Use a calm routine opener.",
                "format": "Voiceover with simple B-roll",
                "recommendation": "Borrow the pacing while rewriting for Nattome.",
            },
        ],
    }


def complete_gemini_evidence():
    return {
        "status": "completed",
        "model": "gemini-2.5-flash",
        "visual_observations": [{"timestamp_seconds": 0.5, "observation": "Creator points at stomach"}],
        "visible_text": [{"timestamp_seconds": 0.8, "text": "Bloated after meals?"}],
        "spoken_content": [
            {
                "start_seconds": 0,
                "end_seconds": 2,
                "text": "Here is a gentle routine for digestion support",
            }
        ],
        "audio_cues": [{"timestamp_seconds": 0, "cue": "calm talking-head voiceover"}],
        "hook_evidence": [{"timestamp_seconds": 0.5, "evidence": "problem question opens the video"}],
        "claim_evidence": [{"timestamp_seconds": 1.2, "text": "supports digestion"}],
        "missing_evidence": [],
    }


class FakeGeminiAdapter:
    def analyze_source_video(self, source_video_path, candidate_context):
        return complete_gemini_evidence()


def workbook_sheet_names(path: Path):
    with zipfile.ZipFile(path) as archive:
        workbook_xml = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    return [sheet.attrib["name"] for sheet in workbook_xml.findall(".//x:sheet", SPREADSHEET_NS)]


def cell_text(cell):
    inline_text = cell.find("x:is/x:t", SPREADSHEET_NS)
    if inline_text is not None:
        return inline_text.text or ""
    value = cell.find("x:v", SPREADSHEET_NS)
    return value.text if value is not None else ""


def sheet_rows(path: Path, sheet_number: int):
    with zipfile.ZipFile(path) as archive:
        sheet_xml = ElementTree.fromstring(archive.read(f"xl/worksheets/sheet{sheet_number}.xml"))
    rows = []
    for row in sheet_xml.findall(".//x:sheetData/x:row", SPREADSHEET_NS):
        rows.append([cell_text(cell) for cell in row.findall("x:c", SPREADSHEET_NS)])
    return rows


class Top5AnglePlanningWorkbookTest(unittest.TestCase):
    def test_renderer_writes_two_sheet_workbook_without_full_scripts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_folder = Path(temp_dir) / "run"
            output_root = Path(temp_dir) / "outputs"
            (run_folder / "data").mkdir(parents=True)
            candidates = [candidate(Path(temp_dir), index) for index in range(1, 6)]
            selected_batch = {
                "selected_at": "2026-05-07T08:00:00Z",
                "selected_candidates": candidates,
            }
            bundles = []
            for item in candidates:
                bundle = snapshot(item["id"], item["rank"])
                bundles.append(bundle)
                write_json(
                    run_folder / bundle["artifacts"]["shootable_angles"]["path"],
                    angles(item["id"]),
                )
                write_json(
                    run_folder / bundle["artifacts"]["evidence_quality"]["path"],
                    {
                        "evidence_quality_score": {
                            "level": "high",
                            "reason": "All core evidence was captured.",
                        },
                        "manual_review_flag": {"required": False, "reasons": []},
                    },
                )
                write_json(
                    run_folder / bundle["artifacts"]["claim_safety_review"]["path"],
                    {"flagged_claims": []},
                )
                write_json(
                    run_folder / bundle["artifacts"]["baseline_audio_analysis"]["path"],
                    {"audio_format": "talking_head"},
                )
            evidence_index = {"bundle_count": len(bundles), "bundles": bundles}

            status = write_top5_angle_planning_workbook(
                run_folder,
                output_root,
                selected_batch,
                evidence_index,
                "2026-05-07T08:00:00Z",
            )

            self.assertEqual(
                status["path"],
                "reports/2026-05-07/production_angle_planning_sheet_2026-05-07.xlsx",
            )
            workbook_path = output_root / status["path"]
            self.assertEqual(workbook_sheet_names(workbook_path), ["Angles", "Source Videos"])

            angle_rows = sheet_rows(workbook_path, 1)
            source_rows = sheet_rows(workbook_path, 2)
            self.assertEqual(len(angle_rows) - 1, 15)
            self.assertEqual(len(source_rows) - 1, 5)

            angle_headers = angle_rows[0]
            by_header = {header: index for index, header in enumerate(angle_headers)}
            self.assertIn("Recommended Shoot", angle_headers)
            self.assertIn("Priority Score", angle_headers)
            self.assertIn("Evidence Quality", angle_headers)
            self.assertIn("Why It Works", angle_headers)
            for source_id in [f"video-{index}" for index in range(1, 6)]:
                markers = [
                    row[by_header["Recommended Shoot"]]
                    for row in angle_rows[1:]
                    if row[by_header["Source ID"]] == source_id
                ]
                self.assertEqual(markers.count("Yes"), 1)
                self.assertEqual(markers.count("No"), 2)

            first_angle = angle_rows[1]
            self.assertEqual(first_angle[by_header["Source Link"]], "https://www.tiktok.com/@creator1/video/1")
            self.assertEqual(first_angle[by_header["Creator"]], "creator1")
            self.assertEqual(first_angle[by_header["Priority Score"]], "28")
            self.assertEqual(first_angle[by_header["Evidence Quality"]], "high")

            all_cells = "\n".join(cell for row in angle_rows + source_rows for cell in row)
            self.assertNotIn("FORBIDDEN FULL SCRIPT LINE", all_cells)
            self.assertNotIn("FORBIDDEN CTA LINE", all_cells)

    def test_completed_run_writes_dated_angle_planning_workbook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidates_path = temp_path / "candidates.json"
            candidates_path.write_text(
                json.dumps({"top": [candidate(temp_path, index) for index in range(1, 6)]}),
                encoding="utf-8",
            )
            output_root = temp_path / "outputs"

            create_run(
                Namespace(
                    mode="daily",
                    batch_size=None,
                    runs_dir=temp_path / "runs",
                    outputs_dir=output_root,
                    config=None,
                    candidates=candidates_path,
                    timestamp="2026-05-07T08:00:00Z",
                    gemini_adapter=FakeGeminiAdapter(),
                )
            )

            workbook_path = (
                output_root
                / "reports"
                / "2026-05-07"
                / "20260507T080000Z_daily"
                / "production_angle_planning_sheet_2026-05-07.xlsx"
            )
            self.assertTrue(workbook_path.is_file())
            self.assertEqual(workbook_sheet_names(workbook_path), ["Angles", "Source Videos"])
            self.assertEqual(len(sheet_rows(workbook_path, 1)) - 1, 9)
            self.assertEqual(len(sheet_rows(workbook_path, 2)) - 1, 3)


if __name__ == "__main__":
    unittest.main()
