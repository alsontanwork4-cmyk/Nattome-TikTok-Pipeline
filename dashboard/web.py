from __future__ import annotations

from .config import DashboardSettings

__all__ = [
    "DashboardSettings",
    "create_app",
    "main",
]


def create_app(*args, **kwargs):
    from .app import create_app as fastapi_create_app

    return fastapi_create_app(*args, **kwargs)


def main() -> None:
    import uvicorn

    uvicorn.run(
        "dashboard.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8765,
    )


if __name__ == "__main__":
    main()
