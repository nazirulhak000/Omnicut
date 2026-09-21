"""Deterministic hard gates and editorial score for Gadget Media masters."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from scripts.gadget_media_project import ProductVideoProject, STORY_ROLES, utc_now


REQUIRED_STORY_ROLES = {"hook", "hero_benefit", "proof", "caveat", "verdict"}
FACTUAL_TYPES = {"brand_claim", "verified_fact", "caveat"}


def _gate(gate_id: str, passed: bool, message: str) -> Dict[str, Any]:
    return {"id": gate_id, "passed": bool(passed), "message": message}


def _native_1080(source: Dict[str, Any]) -> bool:
    width = int(source.get("width") or 0)
    height = int(source.get("height") or 0)
    return max(width, height) >= 1920 and min(width, height) >= 1080 and not bool(source.get("upscaled"))


def _audio_ready(project: ProductVideoProject, project_root: Path | None) -> bool:
    if project.presentation.get("mode") == "product_only":
        return True
    configured = str(project.presentation.get("audio_path") or "").strip()
    if not configured:
        return False
    candidate = Path(configured)
    if not candidate.is_absolute() and project_root:
        candidate = project_root / candidate
    candidate = candidate.resolve(strict=False)
    if project_root:
        root = project_root.resolve(strict=False)
        if candidate != root and root not in candidate.parents:
            return False
    return candidate.is_file()


def validate_product_video(
    project: ProductVideoProject,
    timeline: Dict[str, Any] | None,
    *,
    project_root: Path | None = None,
) -> Dict[str, Any]:
    used_source_ids: Set[str] = {
        str(clip.get("source_id") or "")
        for clip in ((timeline or {}).get("clips") or [])
        if clip.get("source_id")
    }
    sources = {str(item.get("source_id") or ""): item for item in project.source_assets}
    used_sources = [sources[source_id] for source_id in used_source_ids if source_id in sources]
    product_key = f"{project.product_identity.get('brand', '')} {project.product_identity.get('model', '')}".strip().lower()
    purity_ok = bool(product_key) and bool(used_sources) and all(
        not str(source.get("product_key") or product_key).strip().lower()
        or str(source.get("product_key") or product_key).strip().lower() == product_key
        for source in used_sources
    )
    native_ok = bool(used_sources) and all(_native_1080(source) for source in used_sources)
    rights_ok = bool(used_sources) and all(bool(source.get("rights_reviewed")) for source in used_sources)

    facts = project.facts
    evidence_ok = bool(facts) and all(
        fact.get("type") == "opinion" or bool(fact.get("evidence_refs"))
        for fact in facts
        if fact.get("type") in FACTUAL_TYPES or fact.get("type") == "opinion"
    )
    blocks = project.story.get("blocks") or []
    roles = {str(block.get("role") or "") for block in blocks}
    story_ok = REQUIRED_STORY_ROLES.issubset(roles)

    duration = float((timeline or {}).get("duration") or project.edit.get("duration") or 0)
    duration_ok = 45.0 <= duration <= 60.0
    output = (timeline or {}).get("output") or {}
    technical_ok = (
        int(output.get("width") or 0) == 1080
        and int(output.get("height") or 0) == 1920
        and float(output.get("fps") or 0) == 30
    )
    parity_ok = bool(project.edit.get("parity_verified"))
    audio_ok = _audio_ready(project, project_root)

    gates = [
        _gate("product_purity", purity_ok, "ทุกช็อตต้องเป็นสินค้ารุ่นเดียวกัน"),
        _gate("native_source", native_ok, "Source ที่ใช้ต้องเป็น Native 1080p ขึ้นไปและไม่ใช่ไฟล์ upscale"),
        _gate("rights", rights_ok, "Source ที่ใช้ทุกตัวต้องผ่านการตรวจสิทธิ์"),
        _gate("evidence", evidence_ok, "Claim เชิงข้อเท็จจริงต้องมี Evidence และ Opinion ต้องระบุประเภท"),
        _gate("story", story_ok, "Story ต้องมี Hook, Hero benefit, Proof, Caveat และ Verdict"),
        _gate("duration", duration_ok, "Master ต้องยาว 45–60 วินาที"),
        _gate("technical", technical_ok, "Timeline ต้องเป็น 1080×1920 ที่ 30 FPS"),
        _gate("audio", audio_ok, "โหมด Creator/Gemini TTS ต้องมีไฟล์เสียงภายใน Product Project"),
        _gate("parity", parity_ok, "ต้องยืนยัน Preview/Render parity ก่อน Render"),
    ]
    blockers = [gate for gate in gates if not gate["passed"]]

    # The score is advisory and cannot override a failed hard gate.
    clarity = 15 if {"hook", "product_reveal"}.intersection(roles) else 8 if "hook" in roles else 0
    knowledge = min(25, len(facts) * 5 + (5 if evidence_ok else 0))
    visual = min(25, len((timeline or {}).get("clips") or []) * 3 + (5 if duration_ok else 0))
    audio = 15 if audio_ok and technical_ok else 5
    purchase = 15 if {"hero_benefit", "caveat", "verdict"}.issubset(roles) else 5
    finish = 5 if parity_ok else 0
    score = min(100, clarity + knowledge + visual + audio + purchase + finish)
    return {
        "schema_version": 1,
        "project_id": project.project_id,
        "passed": not blockers,
        "gates": gates,
        "blockers": blockers,
        "editorial_score": score,
        "duration": duration,
        "validated_at": utc_now(),
    }
