"""Shared React shell for the three TriAgent services.

One Vite build in ``frontend/dist`` is served by every FastAPI app. Each app
injects its own default tab and the ports of its companion services, so the
same SPA works whether it is opened on the Mail, Lens or Docs port.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def companion_ports() -> dict[str, int]:
    return {
        "part1": settings.app_port,
        "part2": settings.scraper_port,
        "part3": settings.chat_port,
    }


def install_web_ui(app: FastAPI, *, default_tab: str) -> None:
    """Allow the SPA to call sibling services and serve the built bundle."""

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> str:
        index_path = FRONTEND_DIST / "index.html"
        if not index_path.is_file():
            return (
                "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                "<title>TriAgent</title></head><body>"
                "<h1>TriAgent</h1>"
                "<p>The React frontend has not been built. Run "
                "<code>npm install &amp;&amp; npm run build</code> in "
                "<code>frontend/</code>, then reload.</p>"
                "</body></html>"
            )

        html = index_path.read_text(encoding="utf-8")
        return (
            html.replace("__TRIAGENT_DEFAULT_TAB__", default_tab)
            .replace("__TRIAGENT_PORTS__", escape(json.dumps(companion_ports()), quote=True))
        )
