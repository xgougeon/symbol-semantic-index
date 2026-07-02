from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ..visual_selector import VisualSelectionItem, icon_to_json, select_visual_icons
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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service_version=SERVICE_VERSION)


@app.post("/v1/icons/select", response_model=IconSelectResponse)
def select_icon(payload: IconSelectRequest) -> IconSelectResponse:
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
    selected = icon_to_json(choice.icon, repo_root=REPO_ROOT)
    return IconSelectResponse(
        icon=selected,
        asset_ref=selected["asset_ref"],
        score=choice.score,
        rationale=choice.rationale,
        alternatives=[
            {
                **icon_to_json(candidate.icon, repo_root=REPO_ROOT),
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
