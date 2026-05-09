import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
PRIMARY_SKILL = WORKSPACE / "skills" / "nattome-viral-intelligence-run" / "SKILL.md"
OLD_PRIMARY_SKILL = WORKSPACE / "skills" / "nattome-tiktok-run-coordinate" / "SKILL.md"
DISCOVERY_SKILL = WORKSPACE / "skills" / "nattome-tiktok-candidate-discovery" / "SKILL.md"
EVIDENCE_SKILL = WORKSPACE / "skills" / "nattome-evidence-insight-analysis" / "SKILL.md"
README = WORKSPACE / "README.md"


class DailyEvidenceSkillContractTest(unittest.TestCase):
    def test_primary_skill_is_the_only_normal_operation_entry_point(self):
        primary = PRIMARY_SKILL.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")

        self.assertTrue(PRIMARY_SKILL.is_file())
        self.assertFalse(OLD_PRIMARY_SKILL.exists())
        self.assertIn("name: nattome-viral-intelligence-run", primary)
        self.assertIn("only normal-operation skill", primary)
        self.assertIn("nattome-viral-intelligence-run", readme)
        self.assertNotIn("nattome-tiktok-run-coordinate", readme)

    def test_primary_skill_documents_daily_commands_outputs_and_reporting(self):
        primary = PRIMARY_SKILL.read_text(encoding="utf-8")

        for expected in (
            "Daily Evidence Run",
            "Daily Top-3 Selection",
            "APIFY_TOKEN",
            "GEMINI_API_KEY",
            "scrape_tiktok.py",
            "--daily-selection-output",
            "scripts/run_batch_analysis.py",
            "--mode daily",
            "raw_scrape_top30.json",
            "daily_selection_top3.json",
            "top5_creative_production_report",
            "top5_angle_planning_sheet",
            "runs/batch-analysis",
            "Evidence completion status",
            "Shootable Angles",
            "Nattome Priority Scores",
            "Claim Safety Review risks",
            "Manual Review Flags",
            "Failed downloads",
            "Do not call an idea a Shootable Angle unless Gemini source-video evidence supports",
            "references/nattome_brand.md",
            "references/virality_framework.md",
        ):
            self.assertIn(expected, primary)

    def test_phase_skills_are_supporting_references_only(self):
        discovery = DISCOVERY_SKILL.read_text(encoding="utf-8")
        evidence = EVIDENCE_SKILL.read_text(encoding="utf-8")

        for text in (discovery, evidence):
            self.assertIn("user-invocable: false", text)
            self.assertIn("supporting phase reference", text)
            self.assertIn("Normal users should trigger `nattome-viral-intelligence-run`", text)
            self.assertIn("references/nattome_brand.md", text)
            self.assertIn("references/virality_framework.md", text)

    def test_discovery_support_skill_keeps_pre_gemini_output_as_preview(self):
        discovery = DISCOVERY_SKILL.read_text(encoding="utf-8")

        for expected in (
            "Daily Top-3 Selection",
            "data/daily_runs/<run_id>/daily_selection_top3.json",
            "candidate previews",
            "metadata inferences",
            "Do not claim exact visible text",
            "Do not say `Shootable Angle`",
            "Do not say `Nattome Priority Score`",
            "Do not say `production-ready`",
        ):
            self.assertIn(expected, discovery)

    def test_evidence_support_skill_documents_daily_reruns_and_evidence_reporting(self):
        evidence = EVIDENCE_SKILL.read_text(encoding="utf-8")

        for expected in (
            "data/daily_runs/<run_id>/daily_selection_top3.json",
            "--mode daily",
            "completed",
            "partial",
            "missing_credentials",
            "missing",
            "failed",
            "Manual Review Flags",
            "Claim Safety Review",
            "Gemini evidence status exactly",
        ):
            self.assertIn(expected, evidence)

    def test_current_daily_evidence_surfaces_do_not_teach_top5_operation(self):
        current_surfaces = [
            PRIMARY_SKILL,
            DISCOVERY_SKILL,
            EVIDENCE_SKILL,
            README,
            WORKSPACE / "CONTEXT.md",
            WORKSPACE / "docs" / "cloud-operations.md",
        ]

        for surface in current_surfaces:
            text = surface.read_text(encoding="utf-8")
            with self.subTest(surface=surface.name):
                self.assertNotIn("Daily Top-5 Selection", text)
                self.assertNotIn("daily_selection_top5.json", text)
                self.assertNotIn("top-5 handoff", text.lower())


if __name__ == "__main__":
    unittest.main()
