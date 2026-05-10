from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import Request

from .config import DashboardSettings


DASHBOARD_ACCESS_TOKEN_COOKIE = "dashboard_access_token"
DASHBOARD_REFRESH_TOKEN_COOKIE = "dashboard_refresh_token"


class AuthenticationError(Exception):
    """Raised when a Supabase Auth login or session lookup fails."""


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str
    access_token: str

    @property
    def audit_identity(self) -> str:
        return self.email or self.user_id


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user: AuthenticatedUser


class SupabaseAuthClient:
    def __init__(self, settings: DashboardSettings):
        self._settings = settings

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        self._require_supabase_settings()
        response = httpx.post(
            self._auth_url("/token?grant_type=password"),
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=10,
        )
        if response.status_code >= 400:
            raise AuthenticationError("Invalid login credentials")

        payload = response.json()
        access_token = str(payload.get("access_token") or "")
        refresh_token = str(payload.get("refresh_token") or "")
        user_payload = payload.get("user") or {}
        if not access_token or not isinstance(user_payload, dict):
            raise AuthenticationError("Supabase Auth returned an incomplete session")

        user = _user_from_payload(user_payload, access_token)
        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(payload.get("expires_in") or 3600),
            user=user,
        )

    def get_user(self, access_token: str) -> AuthenticatedUser:
        self._require_supabase_settings()
        response = httpx.get(
            self._auth_url("/user"),
            headers={**self._headers(), "Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if response.status_code >= 400:
            raise AuthenticationError("Invalid session")
        return _user_from_payload(response.json(), access_token)

    def _require_supabase_settings(self) -> None:
        if not self._settings.supabase_url or not self._settings.supabase_anon_key:
            raise AuthenticationError("Supabase Auth is not configured")

    def _auth_url(self, path: str) -> str:
        return f"{self._settings.supabase_url.rstrip('/')}/auth/v1{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._settings.supabase_anon_key,
            "Content-Type": "application/json",
        }


def get_current_user(request: Request) -> AuthenticatedUser:
    access_token = request.cookies.get(DASHBOARD_ACCESS_TOKEN_COOKIE)
    if not access_token:
        raise AuthenticationError("Missing session")
    return request.app.state.auth_client.get_user(access_token)


def _user_from_payload(payload: dict, access_token: str) -> AuthenticatedUser:
    email = str(payload.get("email") or "")
    user_id = str(payload.get("id") or payload.get("sub") or "")
    if not user_id:
        raise AuthenticationError("Supabase Auth returned an incomplete user")
    return AuthenticatedUser(user_id=user_id, email=email, access_token=access_token)
