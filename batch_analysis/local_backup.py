from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import isoformat_z, parse_run_timestamp

LOCAL_BACKUP_INPUTS = ("data", "outputs", "runs", ".env")
LOCAL_BACKUP_DIR = "local-backups"


@dataclass(frozen=True)
class LocalEvidenceBackup:
    archive_path: Path
    receipt_path: Path
    created_at: str
    protected_inputs: tuple[str, ...]


def create_local_evidence_backup(
    project_root: Path,
    backup_root: Path | None = None,
    timestamp: str | None = None,
) -> LocalEvidenceBackup:
    root = project_root.resolve()
    created_at = parse_run_timestamp(timestamp)
    backup_dir = (backup_root or root / LOCAL_BACKUP_DIR).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    archive_path = backup_dir / (
        f"nattome-local-evidence-backup-{created_at.strftime('%Y%m%dT%H%M%SZ')}.zip"
    )

    missing_inputs = [
        name for name in LOCAL_BACKUP_INPUTS if not (root / name).exists()
    ]
    if missing_inputs:
        raise FileNotFoundError(
            "required local backup input not found: " + ", ".join(missing_inputs)
        )

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for input_name in LOCAL_BACKUP_INPUTS:
            input_path = root / input_name
            if input_path.is_dir():
                _write_directory(archive, input_path, root)
            else:
                archive.write(input_path, input_name)

    receipt_path = archive_path.with_suffix(".md")
    receipt_path.write_text(
        _backup_receipt_markdown(
            archive_path=archive_path,
            created_at=isoformat_z(created_at),
            protected_inputs=LOCAL_BACKUP_INPUTS,
        ),
        encoding="utf-8",
    )

    return LocalEvidenceBackup(
        archive_path=archive_path,
        receipt_path=receipt_path,
        created_at=isoformat_z(created_at),
        protected_inputs=LOCAL_BACKUP_INPUTS,
    )


def _write_directory(archive: zipfile.ZipFile, directory: Path, root: Path) -> None:
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    if not files:
        archive.writestr(f"{directory.relative_to(root).as_posix()}/", "")
        return

    for path in files:
        archive.write(path, path.relative_to(root).as_posix())


def _backup_receipt_markdown(
    archive_path: Path,
    created_at: str,
    protected_inputs: tuple[str, ...],
) -> str:
    display_inputs = [
        f"{name}/" if name != ".env" else name for name in protected_inputs
    ]
    return "\n".join(
        [
            "# Local Evidence Backup Receipt",
            "",
            f"Archive: {archive_path}",
            f"Created at: {created_at}",
            "Protected inputs: " + ", ".join(display_inputs),
            "",
            "## Migration Safety Checklist",
            "",
            "- Old local history is backed up but not imported into cloud dashboard v1.",
            "- The cloud dashboard v1 starts from newly published run records only.",
            "- Keep this receipt local with the archive; do not commit credentials or archives.",
            "",
        ]
    )
