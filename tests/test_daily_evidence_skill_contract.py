import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
PRIMARY_SKILL = WORKSPACE / "skills" / "nattome-viral-intelligence-run" / "SKILL.md"
OLD_PRIMARY_SKILL = WORKSPACE / "skills" / "nattome-tiktok-run-coordinate" / "SKILL.md"
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
            "Daily Top-5 Selection",
            "APIFY_TOKEN",
            "GEMINI_API_KEY",
            "scrape_tiktok.py",
            "--daily-selection-output",
            "scripts/run_batch_analysis.py",
            "--mode daily",
            "raw_scrape_top30.json",
            "daily_selection_top5.json",
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


if __name__ == "__main__":
    unittest.main()
