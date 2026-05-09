import tempfile
import unittest
import zipfile
from pathlib import Path

from batch_analysis.local_backup import create_local_evidence_backup


class LocalEvidenceBackupTest(unittest.TestCase):
    def test_backup_archive_contains_local_evidence_roots_and_env_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            for folder in ["data", "outputs", "runs"]:
                path = project_root / folder
                path.mkdir()
                (path / "kept.txt").write_text(folder, encoding="utf-8")
            (project_root / ".env").write_text(
                "GEMINI_API_KEY=test-only\n",
                encoding="utf-8",
            )

            result = create_local_evidence_backup(
                project_root=project_root,
                backup_root=project_root / "local-backups",
                timestamp="2026-05-09T02:03:04Z",
            )

            self.assertEqual(
                result.archive_path.name,
                "nattome-local-evidence-backup-20260509T020304Z.zip",
            )
            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())

            self.assertIn("data/kept.txt", names)
            self.assertIn("outputs/kept.txt", names)
            self.assertIn("runs/kept.txt", names)
            self.assertIn(".env", names)

    def test_backup_writes_local_receipt_with_migration_safety_policy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            for folder in ["data", "outputs", "runs"]:
                (project_root / folder).mkdir()
            (project_root / ".env").write_text("APIFY_TOKEN=test-only\n", encoding="utf-8")

            result = create_local_evidence_backup(
                project_root=project_root,
                backup_root=project_root / "local-backups",
                timestamp="2026-05-09T02:03:04Z",
            )

            receipt = result.receipt_path.read_text(encoding="utf-8")

            self.assertIn(str(result.archive_path), receipt)
            self.assertIn("Created at: 2026-05-09T02:03:04Z", receipt)
            self.assertIn("Protected inputs: data/, outputs/, runs/, .env", receipt)
            self.assertIn("Old local history is backed up but not imported into cloud dashboard v1.", receipt)

    def test_project_gitignore_protects_local_migration_artifacts(self):
        project_root = Path(__file__).resolve().parents[1]
        ignored = set(
            line.strip()
            for line in (project_root / ".gitignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )

        for pattern in [
            ".env",
            ".env.*",
            "data/dashboard/*.sqlite3",
            "data/dashboard/*.sqlite3-*",
            "/outputs/",
            "/runs/",
            "/local-backups/",
        ]:
            self.assertIn(pattern, ignored)


if __name__ == "__main__":
    unittest.main()
