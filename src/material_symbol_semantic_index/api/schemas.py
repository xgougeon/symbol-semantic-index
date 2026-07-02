from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class IconSelectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    tone: str | None = None
    context: str | None = None
    prefer_style: str = "datagalaxy"
    allow_material_fallback: bool = True
    avoid: list[str] | None = None
    alternatives: int = Field(default=5, ge=0, le=50)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class IconSelectItem(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    label: str | None = None
    tone: str | None = None
    context: str | None = None
    avoid: list[str] | None = None

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value


class IconSelectBatchRequest(BaseModel):
    items: list[IconSelectItem] = Field(..., min_length=1, max_length=50)
    prefer_style: str = "datagalaxy"
    allow_material_fallback: bool = True
    alternatives: int = Field(default=5, ge=0, le=50)


class IconInfo(BaseModel):
    icon_id: str
    name: str
    style: str
    source_collection: str
    asset_ref: str | None
    source_path: str
    semantic_domains: list[str]
    semiotic_roles: list[str]
    visual_weight: str


class IconAlternative(IconInfo):
    score: float
    reasons: list[str]


class IconSelectResponse(BaseModel):
    icon: IconInfo
    asset_ref: str | None
    score: float
    rationale: str
    alternatives: list[IconAlternative]
    warnings: list[str]
    metadata_sha256: str
    service_version: str


class IconSelectBatchChoice(BaseModel):
    label: str | None
    icon: IconInfo
    asset_ref: str | None
    score: float
    rationale: str
    alternatives: list[IconAlternative]


class IconSelectBatchResponse(BaseModel):
    choices: list[IconSelectBatchChoice]
    warnings: list[str]
    metadata_sha256: str
    service_version: str


class HealthResponse(BaseModel):
    status: str
    service_version: str


class ErrorResponse(BaseModel):
    detail: str
