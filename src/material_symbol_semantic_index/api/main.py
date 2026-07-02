from __future__ import annotations

import io
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from ..visual_selector import VisualIconRecord, VisualSelectionItem, icon_to_json, select_visual_icons
from .schemas import (
    HealthResponse,
    IconSelectBatchChoice,
    IconSelectBatchRequest,
    IconSelectBatchResponse,
    IconSelectRequest,
    IconSelectResponse,
)

SERVICE_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = REPO_ROOT / "data"

# Sampled from the DataGalaxy template itself where possible (see docs/color audit,
# 2026-07-02): red from the problem-single card icon, green from the
# cards-2-comparison "after" card gradient. No orange reference existed in the
# template, so it's a standard warm orange rather than a sampled brand value.
COLOR_PALETTE = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 64),
    "orange": (255, 152, 0),
    "green": (0, 190, 130),
}

HEX_COLOR_RE = re.compile(r"^#?([0-9A-Fa-f]{6})$")


def resolve_color(color: str) -> tuple[int, int, int] | None:
    """Named palette entry, or an arbitrary #RRGGBB / RRGGBB hex color."""
    if color in COLOR_PALETTE:
        return COLOR_PALETTE[color]
    match = HEX_COLOR_RE.match(color)
    if not match:
        return None
    hex_digits = match.group(1)
    return tuple(int(hex_digits[i : i + 2], 16) for i in (0, 2, 4))

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


def choice_to_dict(choice, base_url: str) -> dict:
    selected = icon_json_with_url(choice.icon, base_url)
    return {
        "icon": selected,
        "asset_ref": selected["asset_ref"],
        "score": choice.score,
        "rationale": choice.rationale,
        "alternatives": [
            {
                **icon_json_with_url(candidate.icon, base_url),
                "score": candidate.score,
                "reasons": list(candidate.reasons),
            }
            for candidate in choice.alternatives
        ],
    }


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

    base_url = str(request.base_url)
    return IconSelectResponse(
        **choice_to_dict(selection.choices[0], base_url),
        warnings=list(selection.warnings),
        metadata_sha256=selection.metadata_sha256,
        service_version=SERVICE_VERSION,
    )


@app.post("/v1/icons/select-batch", response_model=IconSelectBatchResponse)
def select_icons_batch(
    payload: IconSelectBatchRequest, request: Request
) -> IconSelectBatchResponse:
    items = []
    for entry in payload.items:
        combined_context = " ".join(part for part in (entry.tone, entry.context) if part)
        items.append(
            VisualSelectionItem(
                text=entry.text,
                label=entry.label,
                context=combined_context,
                avoid=tuple(entry.avoid or ()),
            )
        )

    try:
        selection = select_visual_icons(
            items,
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

    base_url = str(request.base_url)
    return IconSelectBatchResponse(
        choices=[
            IconSelectBatchChoice(label=choice.item.label, **choice_to_dict(choice, base_url))
            for choice in selection.choices
        ],
        warnings=list(selection.warnings),
        metadata_sha256=selection.metadata_sha256,
        service_version=SERVICE_VERSION,
    )


@app.get("/assets/{asset_path:path}")
def get_asset(asset_path: str, color: str | None = None):
    if not DATA_DIR.exists():
        raise HTTPException(status_code=404, detail="not found")
    resolved = (DATA_DIR / asset_path).resolve()
    try:
        resolved.relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="not found")

    if color is None:
        return FileResponse(resolved)

    rgb = resolve_color(color)
    if rgb is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"unknown color '{color}', choose one of {sorted(COLOR_PALETTE)} "
                "or a hex color like '1E3A8A' / '#1E3A8A'"
            ),
        )
    if resolved.suffix.lower() != ".png":
        raise HTTPException(
            status_code=400, detail="color recoloring is only supported for .png assets"
        )

    image = Image.open(resolved).convert("RGBA")
    r, g, b = rgb
    alpha = image.split()[3]
    tinted = Image.new("RGBA", image.size, (r, g, b, 0))
    tinted.putalpha(alpha)
    buffer = io.BytesIO()
    tinted.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


# Mounted after the routes above so /health, /v1/icons/select*, and /assets/... still match first.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
