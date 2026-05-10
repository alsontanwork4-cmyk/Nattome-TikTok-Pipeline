from __future__ import annotations

import csv
import json
from io import StringIO

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import (
    DASHBOARD_ACCESS_TOKEN_COOKIE,
    DASHBOARD_REFRESH_TOKEN_COOKIE,
    AuthenticationError,
    SupabaseAuthClient,
    get_current_user,
)
from .config import DashboardSettings
from .markdown import render_markdown
from .runtime import ActiveManualRunError, enqueue_manual_run, sanitize_error_summary
from .scrape_settings import DEFAULT_SCRAPE_SETTINGS, validate_scrape_settings
from .supabase_client import ArtifactMetadata
from .web_constants import CURATION_LABELS, NAV_GROUPS as LEGACY_NAV_GROUPS

RAW_VIDEO_CSV_COLUMNS = [
    "video_id",
    "tiktok_url",
    "author_handle",
    "caption",
    "hashtags",
    "source_input",
    "play_count",
    "like_count",
    "comment_count",
    "share_count",
    "created_at",
    "is_downloadable",
    "run_id",
    "config_version",
    "selection_status",
    "curation_labels",
    "exclude_similar_reason",
    "curation_note",
    "source_artifact_path",
]

RUN_SUMMARY_CSV_COLUMNS = [
    "run_id",
    "timestamp",
    "run_type",
    "source_type",
    "triggered_by",
    "config_version",
    "raw_candidates",
    "eligible_candidates",
    "selected_count",
    "top_issue",
    "output_types",
    "output_links",
]


class EmptyDashboardDataClient:
    def list_runs(self, *, limit: int = 50) -> list[dict]:
        return []

    def get_run(self, run_id: str) -> dict | None:
        return None

    def list_run_outputs(self, run_id: str) -> list[dict]:
        return []

    def get_artifact_metadata(self, artifact_id: str) -> object | None:
        return None

    def create_signed_artifact_url(
        self,
        metadata: object,
        *,
        expires_in: int = 900,
    ) -> str:
        return ""

    def get_report_artifact(self, run_id: str) -> object | None:
        return None

    def download_artifact_text(self, metadata: object) -> str | None:
        return None

    def list_raw_videos(self) -> list[dict]:
        return []

    def list_selected_videos(self) -> list[dict]:
        return []

    def list_video_curation(self) -> list[dict]:
        return []

    def list_settings_versions(self) -> list[dict]:
        return []

    def save_settings_version(
        self,
        settings: dict,
        *,
        reason: str,
        user: str,
    ) -> dict:
        return {}

    def rollback_settings_version(
        self,
        *,
        target_version: int,
        reason: str,
        user: str,
    ) -> dict:
        return {}

    def upsert_video_curation(
        self,
        video_id: str,
        *,
        labels: list[str],
        note: str,
        exclude_similar_reason: str,
        user: str,
    ) -> dict:
        return {}

    def get_active_manual_run(self, *, run_type: str) -> dict | None:
        return None

    def enqueue_manual_run(self, manual_run: dict, run: dict) -> dict:
        return manual_run


def create_app(
    settings: DashboardSettings | None = None,
    *,
    auth_client: object | None = None,
    dashboard_client: object | None = None,
) -> FastAPI:
    resolved_settings = settings or DashboardSettings.from_env()
    app = FastAPI(title="Nattome TikTok Scraper")
    templates = Jinja2Templates(directory=str(resolved_settings.templates_path))

    app.state.settings = resolved_settings
    app.state.templates = templates
    app.state.auth_client = auth_client or SupabaseAuthClient(resolved_settings)
    app.state.dashboard_client = dashboard_client or EmptyDashboardDataClient()

    app.mount(
        "/static",
        StaticFiles(directory=str(resolved_settings.assets_path)),
        name="static",
    )

    @app.get("/", response_class=HTMLResponse)
    def dashboard_shell(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        latest_runs = app.state.dashboard_client.list_runs(limit=1)
        latest_run = _run_view(latest_runs[0]) if latest_runs else None
        outputs = (
            [
                _output_view(row)
                for row in app.state.dashboard_client.list_run_outputs(latest_run["run_id"])
            ]
            if latest_run
            else []
        )
        return templates.TemplateResponse(
            request,
            "overview.html",
            {
                **_template_context(
                    resolved_settings,
                    page_title="Overview",
                    active_path="/",
                ),
                "current_user": user,
                "latest_run": latest_run,
                "outputs": outputs,
                "report_href": f"/reports/{latest_run['run_id']}" if latest_run else "",
                "output_count_label": _output_count_label(outputs),
                "top_operational_issue": (
                    latest_run["error_summary"]
                    if latest_run and latest_run["error_summary"]
                    else "No operational issue reported."
                ),
            },
        )

    @app.get("/runs", response_class=HTMLResponse)
    def runs_page(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        runs = [_run_view(row) for row in app.state.dashboard_client.list_runs(limit=50)]
        return templates.TemplateResponse(
            request,
            "runs.html",
            {
                **_template_context(resolved_settings, page_title="Runs", active_path="/runs"),
                "current_user": user,
                "runs": runs,
                "run_error": "",
            },
        )

    @app.post("/runs", response_class=HTMLResponse)
    def request_manual_run(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        try:
            enqueue_manual_run(
                app.state.dashboard_client,
                triggered_by=user.audit_identity,
            )
        except ActiveManualRunError as exc:
            runs = [_run_view(row) for row in app.state.dashboard_client.list_runs(limit=50)]
            return templates.TemplateResponse(
                request,
                "runs.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Runs",
                        active_path="/runs",
                    ),
                    "current_user": user,
                    "runs": runs,
                    "run_error": str(exc),
                },
                status_code=409,
            )
        return RedirectResponse("/runs", status_code=303)

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail_page(request: Request, run_id: str) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        run = app.state.dashboard_client.get_run(run_id)
        if not run:
            return templates.TemplateResponse(
                request,
                "run_detail.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Run not found",
                        active_path="/runs",
                    ),
                    "current_user": user,
                    "run": None,
                    "outputs": [],
                    "curation_videos": [],
                    "curation_labels": CURATION_LABELS,
                    "curation_error": "",
                },
                status_code=404,
            )
        outputs = [_output_view(row) for row in app.state.dashboard_client.list_run_outputs(run_id)]
        curation_videos = _curation_video_views(
            run_id=run_id,
            raw_videos=_call_client_list(app.state.dashboard_client, "list_raw_videos"),
            video_curation=_call_client_list(app.state.dashboard_client, "list_video_curation"),
        )
        return templates.TemplateResponse(
            request,
            "run_detail.html",
            {
                **_template_context(
                    resolved_settings,
                    page_title=str(run.get("run_id") or run_id),
                    active_path="/runs",
                ),
                "current_user": user,
                "run": _run_view(run),
                "outputs": outputs,
                "curation_videos": curation_videos,
                "curation_labels": CURATION_LABELS,
                "curation_error": "",
            },
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        return templates.TemplateResponse(
            request,
            "settings.html",
            _settings_template_context(
                resolved_settings,
                user=user,
                versions=_call_client_list(app.state.dashboard_client, "list_settings_versions"),
                error="",
            ),
        )

    @app.post("/settings", response_class=HTMLResponse)
    async def save_settings(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        form = await request.form()
        try:
            payload = _settings_form_payload(form)
            reason = _form_value(form, "reason").strip()
            if not reason:
                raise ValueError("saving production scrape settings requires a reason")
            validated = validate_scrape_settings(payload)
            app.state.dashboard_client.save_settings_version(
                validated,
                reason=reason,
                user=user.audit_identity,
            )
        except ValueError as exc:
            return templates.TemplateResponse(
                request,
                "settings.html",
                _settings_template_context(
                    resolved_settings,
                    user=user,
                    versions=_call_client_list(app.state.dashboard_client, "list_settings_versions"),
                    error=str(exc),
                    form_settings=_form_settings_from_payload(_settings_form_payload(form)),
                ),
                status_code=400,
            )
        return RedirectResponse("/settings", status_code=303)

    @app.post("/settings/{version}/rollback", response_class=HTMLResponse)
    async def rollback_settings(request: Request, version: int) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        form = await request.form()
        try:
            reason = _form_value(form, "reason").strip()
            if not reason:
                raise ValueError("rolling back production scrape settings requires a reason")
            app.state.dashboard_client.rollback_settings_version(
                target_version=version,
                reason=reason,
                user=user.audit_identity,
            )
        except ValueError as exc:
            return templates.TemplateResponse(
                request,
                "settings.html",
                _settings_template_context(
                    resolved_settings,
                    user=user,
                    versions=_call_client_list(app.state.dashboard_client, "list_settings_versions"),
                    error=str(exc),
                ),
                status_code=400,
            )
        return RedirectResponse("/settings", status_code=303)

    @app.post("/videos/{video_id}/curation", response_class=HTMLResponse)
    async def save_video_curation(request: Request, video_id: str) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        form = await request.form()
        labels = [str(label) for label in form.getlist("labels")]
        invalid = [label for label in labels if label not in CURATION_LABELS]
        run_id = _form_value(form, "run_id").strip()
        if invalid:
            return Response(
                f"Invalid curation labels: {', '.join(invalid)}",
                status_code=400,
                media_type="text/plain; charset=utf-8",
            )
        exclude_reason = _form_value(form, "exclude_similar_reason")[:160]
        if "Exclude Similar" in labels and not exclude_reason.strip():
            labels = [label for label in labels if label != "Exclude Similar"]
        app.state.dashboard_client.upsert_video_curation(
            video_id,
            labels=labels,
            note=_form_value(form, "note")[:500],
            exclude_similar_reason=exclude_reason,
            user=user.audit_identity,
        )
        return RedirectResponse(f"/runs/{run_id}" if run_id else "/runs", status_code=303)

    @app.get("/reports", response_class=HTMLResponse)
    def reports_page(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        reports = [
            _report_list_view(
                run,
                app.state.dashboard_client.list_run_outputs(str(run.get("run_id") or "")),
            )
            for run in app.state.dashboard_client.list_runs(limit=50)
        ]
        return templates.TemplateResponse(
            request,
            "reports.html",
            {
                **_template_context(
                    resolved_settings,
                    page_title="Reports",
                    active_path="/reports",
                ),
                "current_user": user,
                "reports": reports,
            },
        )

    @app.get("/reports/{run_id}", response_class=HTMLResponse)
    def report_detail_page(request: Request, run_id: str) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        run = app.state.dashboard_client.get_run(run_id)
        if not run:
            return templates.TemplateResponse(
                request,
                "report_detail.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Report not found",
                        active_path="/reports",
                    ),
                    "current_user": user,
                    "run": None,
                    "report_html": "",
                },
                status_code=404,
            )
        metadata = _get_report_artifact(app.state.dashboard_client, run_id)
        markdown = (
            app.state.dashboard_client.download_artifact_text(metadata)
            if metadata is not None
            else None
        )
        return templates.TemplateResponse(
            request,
            "report_detail.html",
            {
                **_template_context(
                    resolved_settings,
                    page_title=str(run.get("run_id") or run_id),
                    active_path="/reports",
                ),
                "current_user": user,
                "run": _run_view(run),
                "report_html": render_markdown(markdown) if markdown else "",
            },
        )

    @app.get("/exports/raw-videos.csv")
    def raw_videos_export(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        return _csv_download_response(
            _csv_text(
                RAW_VIDEO_CSV_COLUMNS,
                _raw_video_export_rows(
                    raw_videos=_call_client_list(app.state.dashboard_client, "list_raw_videos"),
                    selected_videos=_call_client_list(app.state.dashboard_client, "list_selected_videos"),
                    video_curation=_call_client_list(app.state.dashboard_client, "list_video_curation"),
                ),
            ),
            filename="nattome-raw-videos.csv",
        )

    @app.get("/exports/run-summaries.csv")
    def run_summaries_export(request: Request) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        runs = app.state.dashboard_client.list_runs(limit=50)
        return _csv_download_response(
            _csv_text(
                RUN_SUMMARY_CSV_COLUMNS,
                [
                    _run_summary_export_row(
                        run,
                        app.state.dashboard_client.list_run_outputs(str(run.get("run_id") or "")),
                    )
                    for run in runs
                ],
            ),
            filename="nattome-run-summaries.csv",
        )

    @app.get("/artifacts/{artifact_id:path}", response_class=HTMLResponse)
    def artifact_download(request: Request, artifact_id: str) -> Response:
        user = _authenticated_user_or_redirect(request)
        if isinstance(user, RedirectResponse):
            return user
        metadata = app.state.dashboard_client.get_artifact_metadata(artifact_id)
        if not metadata:
            return templates.TemplateResponse(
                request,
                "artifact_status.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Artifact not found",
                        active_path="/runs",
                    ),
                    "current_user": user,
                    "status_title": "Artifact not found",
                    "status_message": "No Supabase artifact metadata exists for this route.",
                },
                status_code=404,
            )
        signed_url = app.state.dashboard_client.create_signed_artifact_url(
            metadata,
            expires_in=900,
        )
        if not signed_url:
            return templates.TemplateResponse(
                request,
                "artifact_status.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Artifact unavailable",
                        active_path="/runs",
                    ),
                    "current_user": user,
                    "status_title": "Artifact unavailable",
                    "status_message": "Supabase Storage did not return a signed download URL.",
                },
                status_code=502,
            )
        return RedirectResponse(signed_url, status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "login.html",
            _template_context(resolved_settings, page_title="Login", active_path="/login"),
        )

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        email: str = Form(...),
        password: str = Form(...),
    ) -> Response:
        try:
            session = app.state.auth_client.sign_in_with_password(email, password)
        except AuthenticationError:
            return templates.TemplateResponse(
                request,
                "login.html",
                {
                    **_template_context(
                        resolved_settings,
                        page_title="Login",
                        active_path="/login",
                    ),
                    "error": "Invalid email or password",
                },
                status_code=401,
            )

        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            DASHBOARD_ACCESS_TOKEN_COOKIE,
            session.access_token,
            httponly=True,
            secure=resolved_settings.runtime_mode == "production",
            samesite="lax",
            max_age=session.expires_in,
        )
        if session.refresh_token:
            response.set_cookie(
                DASHBOARD_REFRESH_TOKEN_COOKIE,
                session.refresh_token,
                httponly=True,
                secure=resolved_settings.runtime_mode == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30,
            )
        return response

    @app.post("/logout")
    def logout() -> RedirectResponse:
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(DASHBOARD_ACCESS_TOKEN_COOKIE)
        response.delete_cookie(DASHBOARD_REFRESH_TOKEN_COOKIE)
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _template_context(
    settings: DashboardSettings,
    *,
    page_title: str,
    active_path: str,
) -> dict:
    return {
        "settings": settings,
        "page_title": page_title,
        "active_path": active_path,
        "nav_groups": _fastapi_nav_groups(),
        "current_user": None,
        "error": "",
    }


def _fastapi_nav_groups() -> tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...]:
    groups = []
    for group_label, items in LEGACY_NAV_GROUPS:
        updated_items = []
        for label, route, icon_name in items:
            if route == "/report":
                updated_items.append(("Reports", "/reports", icon_name))
            elif route == "/scrape-settings":
                updated_items.append(("Scrape Settings", "/settings", icon_name))
            else:
                updated_items.append((label, route, icon_name))
        groups.append((group_label, tuple(updated_items)))
    return tuple(groups)


def _authenticated_user_or_redirect(request: Request) -> object:
    try:
        return get_current_user(request)
    except AuthenticationError:
        return RedirectResponse("/login", status_code=303)


def _call_client_list(dashboard_client: object, method_name: str) -> list[dict]:
    method = getattr(dashboard_client, method_name, None)
    if not callable(method):
        return []
    return list(method() or [])


def _run_view(row: dict) -> dict:
    status = str(row.get("status") or "unknown").lower()
    return {
        "run_id": str(row.get("run_id") or ""),
        "status": status,
        "status_label": _status_label(status),
        "status_tone": _status_tone(status),
        "run_type": str(row.get("run_type") or row.get("mode") or ""),
        "started_at": str(row.get("started_at") or ""),
        "finished_at": str(row.get("finished_at") or ""),
        "duration": _format_duration(row.get("duration_seconds")),
        "triggered_by": str(row.get("triggered_by") or row.get("created_by") or ""),
        "raw_candidate_count": row.get("raw_candidate_count") or 0,
        "eligible_candidate_count": row.get("eligible_candidate_count") or 0,
        "selected_count": row.get("selected_count") or 0,
        "error_summary": _safe_error_summary(row.get("error_summary")),
    }


def _output_view(row: dict) -> dict:
    object_path = str(row.get("object_path") or "")
    return {
        "artifact_type": str(row.get("artifact_type") or ""),
        "bucket": str(row.get("bucket") or ""),
        "object_path": object_path,
        "artifact_href": f"/artifacts/{object_path}" if object_path else "",
        "filename": str(row.get("filename") or row.get("object_path") or ""),
        "content_type": str(row.get("content_type") or ""),
        "size": _format_bytes(row.get("size_bytes")),
        "checksum": str(row.get("checksum") or ""),
        "created_at": str(row.get("created_at") or ""),
    }


def _status_label(status: str) -> str:
    return {
        "queued": "Queued",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "canceled": "Canceled",
        "cancelled": "Canceled",
    }.get(status, status.title() or "Unknown")


def _status_tone(status: str) -> str:
    if status == "succeeded":
        return "ok"
    if status in {"queued", "running"}:
        return "accent"
    if status in {"failed", "error"}:
        return "err"
    if status in {"canceled", "cancelled"}:
        return "warn"
    return "warn"


def _format_duration(value: object) -> str:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return "--"
    minutes, remaining_seconds = divmod(seconds, 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {remaining_minutes}m {remaining_seconds}s"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


def _format_bytes(value: object) -> str:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return "--"
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _output_count_label(outputs: list[dict]) -> str:
    if not outputs:
        return "No outputs published"
    if len(outputs) == 1:
        return "1 output available"
    return f"{len(outputs)} outputs available"


def _settings_template_context(
    settings: DashboardSettings,
    *,
    user: object,
    versions: list[dict],
    error: str,
    form_settings: dict | None = None,
) -> dict:
    normalized_versions = [_settings_version_view(version) for version in versions]
    active = next((version for version in normalized_versions if version["is_active"]), None)
    if active is None:
        active = {
            "version": 0,
            "settings": dict(DEFAULT_SCRAPE_SETTINGS),
            "reason": "Default production settings",
            "is_active": True,
            "rollback_of_version": None,
            "created_by": "system",
            "created_at": "",
        }
    return {
        **_template_context(settings, page_title="Scrape Settings", active_path="/settings"),
        "current_user": user,
        "active": active,
        "versions": normalized_versions,
        "form": _settings_form_view(form_settings or active["settings"]),
        "scope_options": [
            ("all", "All sources"),
            ("hashtags", "Only hashtags"),
            ("keywords", "Only keywords"),
            ("profiles", "Only competitor profiles"),
        ],
        "error": error,
    }


def _settings_version_view(record: dict) -> dict:
    settings = record.get("settings")
    if not isinstance(settings, dict):
        settings = record.get("new_settings") if isinstance(record.get("new_settings"), dict) else {}
    return {
        "version": int(record.get("version") or 0),
        "settings": {**DEFAULT_SCRAPE_SETTINGS, **settings},
        "reason": str(record.get("reason") or ""),
        "is_active": bool(record.get("is_active")),
        "rollback_of_version": record.get("rollback_of_version"),
        "created_by": str(record.get("created_by") or record.get("changed_by") or ""),
        "created_at": str(record.get("created_at") or record.get("timestamp") or ""),
    }


def _settings_form_view(settings: dict) -> dict:
    return {
        "hashtags": _lines(settings.get("hashtags")),
        "keywords": _lines(settings.get("keywords")),
        "competitor_profiles": _lines(settings.get("competitor_profiles")),
        "scope": str(settings.get("scope") or "all"),
        "results_per_input": settings.get("results_per_input") or "",
        "minimum_views": settings.get("minimum_views") or "",
        "maximum_age_days": settings.get("maximum_age_days") or "",
        "minimum_engagement_rate_percent": _percent_value(
            settings.get("minimum_weighted_engagement_rate")
        ),
        "requires_downloadable_video": bool(settings.get("requires_downloadable_video")),
        "exclusion_terms": _lines(settings.get("exclusion_terms")),
    }


def _settings_form_payload(form: object) -> dict[str, object]:
    engagement_rate = _form_value(form, "minimum_weighted_engagement_rate")
    engagement_rate_percent = _form_value(form, "minimum_engagement_rate_percent")
    if engagement_rate_percent:
        engagement_rate = str(float(engagement_rate_percent) / 100)
    return {
        "hashtags": _form_value(form, "hashtags"),
        "keywords": _form_value(form, "keywords"),
        "competitor_profiles": _form_value(form, "competitor_profiles"),
        "scope": _form_value(form, "scope") or "all",
        "results_per_input": _form_value(form, "results_per_input"),
        "minimum_views": _form_value(form, "minimum_views"),
        "maximum_age_days": _form_value(form, "maximum_age_days"),
        "minimum_weighted_engagement_rate": engagement_rate,
        "requires_downloadable_video": "requires_downloadable_video" in form,
        "exclusion_terms": _form_value(form, "exclusion_terms"),
    }


def _form_settings_from_payload(payload: dict[str, object]) -> dict:
    settings = dict(DEFAULT_SCRAPE_SETTINGS)
    settings.update(payload)
    try:
        settings["minimum_weighted_engagement_rate"] = float(
            payload.get("minimum_weighted_engagement_rate") or 0
        )
    except (TypeError, ValueError):
        settings["minimum_weighted_engagement_rate"] = payload.get(
            "minimum_weighted_engagement_rate"
        )
    return settings


def _form_value(form: object, key: str) -> str:
    value = form.get(key) if hasattr(form, "get") else ""
    return str(value or "")


def _lines(value: object) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    return str(value or "")


def _percent_value(value: object) -> str:
    try:
        percent = float(value) * 100
    except (TypeError, ValueError):
        return ""
    return f"{percent:g}"


def _curation_video_views(
    *,
    run_id: str,
    raw_videos: list[dict],
    video_curation: list[dict],
) -> list[dict]:
    curation_by_video = {str(row.get("video_id") or ""): row for row in video_curation}
    videos = []
    for video in raw_videos:
        if str(video.get("run_id") or "") != run_id:
            continue
        video_id = str(video.get("video_id") or "")
        curation = curation_by_video.get(video_id, {})
        videos.append(
            {
                "video_id": video_id,
                "caption": str(video.get("caption") or ""),
                "author_handle": str(video.get("author_handle") or ""),
                "tiktok_url": str(video.get("tiktok_url") or ""),
                "play_count": _cell(video.get("play_count")),
                "labels": _list_value(curation.get("labels")),
                "note": str(curation.get("note") or ""),
                "exclude_similar_reason": str(curation.get("exclude_similar_reason") or ""),
            }
        )
    return videos


def _report_list_view(run: dict, outputs: list[dict]) -> dict:
    run_view = _run_view(run)
    report = _first_report_output(outputs)
    return {
        "run": run_view,
        "filename": str(report.get("filename") or report.get("object_path") or "") if report else "",
        "size": _format_bytes(report.get("size_bytes")) if report else "--",
    }


def _get_report_artifact(dashboard_client: object, run_id: str) -> ArtifactMetadata | None:
    get_report_artifact = getattr(dashboard_client, "get_report_artifact", None)
    if callable(get_report_artifact):
        metadata = get_report_artifact(run_id)
        if isinstance(metadata, ArtifactMetadata):
            return metadata
        if isinstance(metadata, dict):
            return _artifact_metadata_from_output(metadata)
    outputs = dashboard_client.list_run_outputs(run_id)
    report = _first_report_output(outputs)
    return _artifact_metadata_from_output(report) if report else None


def _first_report_output(outputs: list[dict]) -> dict | None:
    for output in outputs:
        artifact_type = str(output.get("artifact_type") or "").lower()
        content_type = str(output.get("content_type") or "").lower()
        filename = str(output.get("filename") or output.get("object_path") or "").lower()
        if artifact_type == "report" or content_type == "text/markdown" or filename.endswith(".md"):
            return output
    return None


def _artifact_metadata_from_output(output: dict) -> ArtifactMetadata:
    object_path = str(output.get("object_path") or "")
    return ArtifactMetadata(
        run_id=str(output.get("run_id") or ""),
        artifact_type=str(output.get("artifact_type") or ""),
        bucket=str(output.get("bucket") or ""),
        object_path=object_path,
        filename=str(output.get("filename") or object_path.rsplit("/", 1)[-1]),
        content_type=str(output.get("content_type") or ""),
        size_bytes=output.get("size_bytes"),
        checksum=output.get("checksum"),
        created_at=output.get("created_at"),
    )


def _raw_video_export_rows(
    *,
    raw_videos: list[dict],
    selected_videos: list[dict],
    video_curation: list[dict],
) -> list[dict[str, object]]:
    selected_by_video = {str(row.get("video_id") or ""): row for row in selected_videos}
    curation_by_video = {str(row.get("video_id") or ""): row for row in video_curation}
    rows = []
    for video in raw_videos:
        video_id = str(video.get("video_id") or "")
        selected = selected_by_video.get(video_id, {})
        curation = curation_by_video.get(video_id, {})
        rows.append(
            {
                "video_id": video_id,
                "tiktok_url": str(video.get("tiktok_url") or ""),
                "author_handle": str(video.get("author_handle") or ""),
                "caption": str(video.get("caption") or ""),
                "hashtags": "; ".join(str(item) for item in _list_value(video.get("hashtags"))),
                "source_input": str(video.get("source_input") or ""),
                "play_count": _cell(video.get("play_count")),
                "like_count": _cell(video.get("like_count")),
                "comment_count": _cell(video.get("comment_count")),
                "share_count": _cell(video.get("share_count")),
                "created_at": str(video.get("created_at") or ""),
                "is_downloadable": "yes" if video.get("is_downloadable") else "no",
                "run_id": str(video.get("run_id") or selected.get("run_id") or ""),
                "config_version": str(video.get("config_version") or ""),
                "selection_status": str(selected.get("evidence_status") or "raw"),
                "curation_labels": "; ".join(str(item) for item in _list_value(curation.get("labels"))),
                "exclude_similar_reason": str(curation.get("exclude_similar_reason") or ""),
                "curation_note": str(curation.get("note") or ""),
                "source_artifact_path": str(video.get("source_artifact_path") or ""),
            }
        )
    return rows


def _run_summary_export_row(run: dict, outputs: list[dict]) -> dict[str, object]:
    return {
        "run_id": str(run.get("run_id") or ""),
        "timestamp": str(run.get("started_at") or run.get("created_at") or ""),
        "run_type": str(run.get("run_type") or run.get("mode") or ""),
        "source_type": str(run.get("source_type") or ""),
        "triggered_by": str(run.get("triggered_by") or run.get("created_by") or ""),
        "config_version": str(run.get("config_version") or ""),
        "raw_candidates": _cell(run.get("raw_candidate_count")),
        "eligible_candidates": _cell(run.get("eligible_candidate_count")),
        "selected_count": _cell(run.get("selected_count")),
        "top_issue": _safe_error_summary(run.get("error_summary")),
        "output_types": "; ".join(str(output.get("artifact_type") or "") for output in outputs),
        "output_links": "; ".join(str(output.get("object_path") or "") for output in outputs),
    }


def _csv_text(columns: list[str], rows: list[dict[str, object]]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _csv_download_response(body: str, *, filename: str) -> Response:
    return Response(
        body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _list_value(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return loaded if isinstance(loaded, list) else [value]
    return []


def _cell(value: object) -> object:
    return "" if value is None else value


def _safe_error_summary(value: object) -> str:
    return sanitize_error_summary(value)


app = create_app()
