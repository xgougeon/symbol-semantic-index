from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..visual_selector import VisualIconRecord, VisualSelectionItem, icon_to_json, select_visual_icons
from .schemas import (
    HealthResponse,
    IconSelectRequest,
    IconSelectResponse,
)

SERVICE_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = REPO_ROOT / "data"

app = FastAPI(title="Symbol Semantic Index API", version=SERVICE_VERSION)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400, content={"detail": jsonable_encoder(exc.errors())}
    )


def downloadable_asset_url(icon: VisualIconRecord, base_url: str) -> str | None:
    """Public URL for the icon PNG, servable via the /assets mount (not a server-local path)."""
    if not icon.source_path:
        return None
    relative = PurePosixPath(icon.source_path)
    if relative.parts and relative.parts[0] == "data":
        relative = PurePosixPath(*relative.parts[1:])
    encoded = "/".join(quote(part) for part in relative.parts)
    return f"{base_url.rstrip('/')}/assets/{encoded}"


def icon_json_with_url(icon: VisualIconRecord, base_url: str) -> dict:
    payload = icon_to_json(icon)
    payload["asset_ref"] = downloadable_asset_url(icon, base_url)
    return payload


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service_version=SERVICE_VERSION)


@app.post("/v1/icons/select", response_model=IconSelectResponse)
def select_icon(payload: IconSelectRequest, request: Request) -> IconSelectResponse:
    combined_context = " ".join(part for part in (payload.tone, payload.context) if part)
    item = VisualSelectionItem(
        text=payload.text,
        context=combined_context,
        avoid=tuple(payload.avoid or ()),
    )

    try:
        selection = select_visual_icons(
            [item],
            prefer_style=payload.prefer_style,
            allow_material_fallback=payload.allow_material_fallback,
            alternatives=payload.alternatives,
            repo_root=REPO_ROOT,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500, detail=f"icon metadata unavailable: {exc}"
        ) from exc

    choice = selection.choices[0]
    base_url = str(request.base_url)
    selected = icon_json_with_url(choice.icon, base_url)
    return IconSelectResponse(
        icon=selected,
        asset_ref=selected["asset_ref"],
        score=choice.score,
        rationale=choice.rationale,
        alternatives=[
            {
                **icon_json_with_url(candidate.icon, base_url),
                "score": candidate.score,
                "reasons": list(candidate.reasons),
            }
            for candidate in choice.alternatives
        ],
        warnings=list(selection.warnings),
        metadata_sha256=selection.metadata_sha256,
        service_version=SERVICE_VERSION,
    )


# Mounted after the routes above so /health and /v1/icons/select still match first.
if DATA_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DATA_DIR), name="assets")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
