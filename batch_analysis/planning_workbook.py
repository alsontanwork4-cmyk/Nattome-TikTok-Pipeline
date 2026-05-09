from __future__ import annotations

import html
import math
import zipfile
from pathlib import Path
from typing import Any

from .outputs import (
    candidate_metric,
    compact_markdown_text,
    evidence_bundles_by_candidate,
    output_report_date,
    priority_score_points_from_artifacts,
    ranked_top_five,
    read_bundle_artifact,
    relative_external_output_path,
    shootable_angles_for_bundle,
    source_creator,
)
from .report_dates import report_output_path
from .reports import product_tie_in_for_candidate


ANGLE_HEADERS = [
    "Source Rank",
    "Source ID",
    "Creator",
    "Source Link",
    "Views",
    "Likes",
    "Comments",
    "Shares",
    "Angle Number",
    "Concept",
    "Hook",
    "Format",
    "Why It Works",
    "Recommended Shoot",
    "Priority Score",
    "Priority Max Points",
    "Priority Viral Strength",
    "Priority Nattome Relevance",
    "Priority Evidence Confidence",
    "Priority Brand Safety",
    "Priority Ease Of Production",
    "Priority Product Fit",
    "Evidence Quality",
    "Evidence Quality Reason",
    "Manual Review Required",
    "Manual Review Reasons",
]

SOURCE_VIDEO_HEADERS = [
    "Rank",
    "Source ID",
    "Creator",
    "Source Link",
    "Caption",
    "Views",
    "Likes",
    "Comments",
    "Shares",
    "Weighted Engagement Rate",
    "Nattome Relevance Score",
    "Selection Score",
    "Evidence Quality",
    "Evidence Quality Reason",
    "Manual Review Required",
    "Manual Review Reasons",
    "Recommended Shoot Concept",
    "Recommended Shoot Hook",
    "Product Fit",
    "Priority Score",
]

def clean_xml_text(value: Any) -> str:
    text = str(value or "")
    return "".join(char for char in text if char in "\t\n\r" or ord(char) >= 32)


def column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def cell_xml(row_index: int, column_index: int, value: Any) -> str:
    reference = f"{column_name(column_index)}{row_index}"
    if isinstance(value, bool):
        return f'<c r="{reference}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, int) and not isinstance(value, bool):
        return f'<c r="{reference}" t="n"><v>{value}</v></c>'
    if isinstance(value, float) and math.isfinite(value):
        return f'<c r="{reference}" t="n"><v>{value}</v></c>'
    escaped = html.escape(clean_xml_text(value), quote=False)
    return f'<c r="{reference}" t="inlineStr"><is><t>{escaped}</t></is></c>'


def sheet_xml(rows: list[list[Any]]) -> str:
    row_count = len(rows)
    column_count = max((len(row) for row in rows), default=1)
    dimension = f"A1:{column_name(column_count)}{max(row_count, 1)}"
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            cell_xml(row_index, column_index, value)
            for column_index, value in enumerate(row, start=1)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    auto_filter = f'<autoFilter ref="{dimension}"/>' if rows else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        f'<dimension ref="{dimension}"/>'
        '<sheetData>'
        f'{"".join(sheet_rows)}'
        '</sheetData>'
        f'{auto_filter}'
        '</worksheet>'
    )


def workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{html.escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets>{sheets}</sheets>'
        '</workbook>'
    )


def workbook_rels_xml(sheet_count: int) -> str:
    relationships = []
    for index in range(1, sheet_count + 1):
        relationships.append(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
    relationships.append(
        f'<Relationship Id="rId{sheet_count + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{"".join(relationships)}'
        '</Relationships>'
    )


def content_types_xml(sheet_count: int) -> str:
    sheet_overrides = "".join(
        '<Override '
        f'PartName="/xl/worksheets/sheet{index}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f'{sheet_overrides}'
        '</Types>'
    )


def package_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '</styleSheet>'
    )


def write_xlsx(path: Path, sheets: list[tuple[str, list[list[Any]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml(len(sheets)))
        archive.writestr("_rels/.rels", package_rels_xml())
        archive.writestr("xl/workbook.xml", workbook_xml([name for name, _rows in sheets]))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml(len(sheets)))
        archive.writestr("xl/styles.xml", styles_xml())
        for index, (_name, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", sheet_xml(rows))


def manual_review_fields(quality: dict[str, Any] | None) -> tuple[str, str]:
    manual_review = quality.get("manual_review_flag") if isinstance(quality, dict) else {}
    if not isinstance(manual_review, dict):
        return ("Yes" if manual_review else "No", "")
    required = "Yes" if manual_review.get("required") else "No"
    reasons = manual_review.get("reasons")
    if isinstance(reasons, list):
        return required, "; ".join(str(reason) for reason in reasons)
    return required, compact_markdown_text(reasons, "")


def quality_fields(quality: dict[str, Any] | None) -> tuple[str, str, str, str]:
    quality_score = quality.get("evidence_quality_score") if isinstance(quality, dict) else {}
    if not isinstance(quality_score, dict):
        quality_score = {}
    manual_required, manual_reasons = manual_review_fields(quality)
    return (
        compact_markdown_text(quality_score.get("level"), "unknown"),
        compact_markdown_text(quality_score.get("reason"), ""),
        manual_required,
        manual_reasons,
    )


def priority_score_for_angle(
    angle: dict[str, Any],
    candidate: dict[str, Any],
    quality: dict[str, Any] | None,
    claim_review: dict[str, Any] | None,
    audio_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    priority_score = (
        angle.get("priority_score")
        if isinstance(angle.get("priority_score"), dict)
        else {}
    )
    dimensions = priority_score.get("dimensions") if isinstance(priority_score, dict) else {}
    if not isinstance(dimensions, dict) or not dimensions:
        dimensions = priority_score_points_from_artifacts(
            candidate,
            quality,
            claim_review,
            audio_analysis,
        )
    total = priority_score.get("total") if isinstance(priority_score, dict) else None
    if not isinstance(total, (int, float)):
        total = sum(value for value in dimensions.values() if isinstance(value, int))
    max_points = (
        priority_score.get("max_points", 30)
        if isinstance(priority_score, dict)
        else 30
    )
    return {"dimensions": dimensions, "total": total, "max_points": max_points}


def build_planning_workbook_rows(
    run_folder: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
) -> tuple[list[list[Any]], list[list[Any]]]:
    angle_rows: list[list[Any]] = [ANGLE_HEADERS]
    source_rows: list[list[Any]] = [SOURCE_VIDEO_HEADERS]
    bundles_by_candidate = evidence_bundles_by_candidate(evidence_index)

    for candidate in ranked_top_five(selected_batch):
        candidate_id = str(candidate.get("id") or "")
        bundle = bundles_by_candidate.get(candidate_id, {})
        angles = shootable_angles_for_bundle(run_folder, bundle) if bundle else []
        quality = read_bundle_artifact(
            run_folder,
            bundle,
            "evidence_quality",
            "evidence_quality.json",
        )
        claim_review = read_bundle_artifact(
            run_folder,
            bundle,
            "claim_safety_review",
            "claim_safety_review.json",
        )
        audio_analysis = read_bundle_artifact(
            run_folder,
            bundle,
            "baseline_audio_analysis",
            "baseline_audio_analysis.json",
        )
        evidence_quality, evidence_reason, manual_required, manual_reasons = quality_fields(quality)
        first_angle = angles[0] if angles else {}
        first_priority = (
            priority_score_for_angle(
                first_angle,
                candidate,
                quality,
                claim_review,
                audio_analysis,
            )
            if first_angle
            else {"total": "", "dimensions": {}, "max_points": ""}
        )

        source_rows.append(
            [
                candidate.get("rank") or "",
                candidate_id,
                source_creator(candidate),
                compact_markdown_text(candidate.get("url"), ""),
                compact_markdown_text(candidate.get("caption"), ""),
                candidate_metric(candidate, "play_count"),
                candidate_metric(candidate, "like_count"),
                candidate_metric(candidate, "comment_count"),
                candidate_metric(candidate, "share_count"),
                candidate.get("weighted_engagement_rate") or "",
                candidate.get("nattome_relevance_score") or "",
                candidate.get("selection_score") or "",
                evidence_quality,
                evidence_reason,
                manual_required,
                manual_reasons,
                compact_markdown_text(first_angle.get("angle_title"), ""),
                compact_markdown_text(first_angle.get("hook"), ""),
                compact_markdown_text(
                    first_angle.get("product_fit") or product_tie_in_for_candidate(candidate),
                    "",
                ),
                first_priority["total"],
            ]
        )

        for angle_index, angle in enumerate(angles, start=1):
            priority = priority_score_for_angle(
                angle,
                candidate,
                quality,
                claim_review,
                audio_analysis,
            )
            dimensions = priority["dimensions"]
            angle_rows.append(
                [
                    candidate.get("rank") or "",
                    candidate_id,
                    source_creator(candidate),
                    compact_markdown_text(candidate.get("url"), ""),
                    candidate_metric(candidate, "play_count"),
                    candidate_metric(candidate, "like_count"),
                    candidate_metric(candidate, "comment_count"),
                    candidate_metric(candidate, "share_count"),
                    angle_index,
                    compact_markdown_text(angle.get("angle_title"), "Nattome concept"),
                    compact_markdown_text(angle.get("hook"), ""),
                    compact_markdown_text(angle.get("format"), ""),
                    compact_markdown_text(
                        angle.get("recommendation") or angle.get("recommended_angle"),
                        "",
                    ),
                    "Yes" if angle_index == 1 else "No",
                    priority["total"],
                    priority["max_points"],
                    dimensions.get("viral_strength", ""),
                    dimensions.get("nattome_relevance", ""),
                    dimensions.get("evidence_confidence", ""),
                    dimensions.get("brand_safety", ""),
                    dimensions.get("ease_of_production", ""),
                    dimensions.get("product_fit", ""),
                    evidence_quality,
                    evidence_reason,
                    manual_required,
                    manual_reasons,
                ]
            )

    return angle_rows, source_rows


def write_top5_angle_planning_workbook(
    run_folder: Path,
    output_root: Path,
    selected_batch: dict[str, Any],
    evidence_index: dict[str, Any],
    timestamp: str,
    run_id: str = "",
) -> dict[str, Any]:
    report_date = output_report_date(timestamp)
    workbook_path = report_output_path(
        output_root,
        report_date,
        f"production_angle_planning_sheet_{report_date}.xlsx",
        run_id,
    )
    angle_rows, source_rows = build_planning_workbook_rows(
        run_folder,
        selected_batch,
        evidence_index,
    )
    write_xlsx(
        workbook_path,
        [
            ("Angles", angle_rows),
            ("Source Videos", source_rows),
        ],
    )
    return {
        "status": "completed",
        "path": relative_external_output_path(workbook_path, output_root),
        "angle_count": len(angle_rows) - 1,
        "source_video_count": len(source_rows) - 1,
    }
