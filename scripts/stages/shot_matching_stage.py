"""
Shot Matching & Motion Stage for OmniCut Pro Studio.
Handles 9:16 Image Motion Slideshows, Gemini Vision Scene Matching,
J-Cut micro-cue grouping, acoustic/motion-guided zoom emphasis, and beat snapping.
"""

import os
from typing import List, Optional

from scripts.video_editor import VideoEditor
from scripts.image_motion_engine import ImageMotionEngine
from scripts.gemini_vision_matcher import GeminiVisionMatcher
from scripts.beat_sync import BeatSync
from scripts.motion_analyzer import MotionAnalyzer
from scripts.script_tone_analyzer import ScriptToneAnalyzer
from scripts.sfx_manager import SFXManager
from scripts.it_angles import LOOK_PRESETS
from scripts.pipeline_context import PipelineContext
from scripts.editorial_pacing import resolve_pacing_boundaries
from scripts.style_motion_policy import apply_transition_budget, camera_keyframes_for_clip
from scripts.quota import is_quota_error
from scripts.error_handler import AppError, ErrorCategory


class ShotMatchingStage:
    """Matches script cues to visual scenes, computes rhythmic cuts and content-aware zoom emphasis."""

    @staticmethod
    def _expand_ai_shots_to_cues(matched_shots: Optional[List[dict]], n_cues: int) -> Optional[List[dict]]:
        """
        Positionally-indexed one-entry-per-micro-cue array from Gemini's
        response, which may cover several consecutive cues with one merged
        shot (`cue_ids: [5, 6, 7]`) instead of the older one-shot-per-cue
        shape (`cue_id: 5`, 0- or 1-indexed depending on vintage). Every cue
        inside a merged shot is pointed at that same shot object, so the
        caller's ai_matched_shots[anchor_idx] lookup keeps working unchanged
        regardless of which shape the model (or a cached response) used.
        """
        if not matched_shots:
            return matched_shots
        expanded: List[Optional[dict]] = [None] * n_cues

        def place(idx0: int, shot: dict) -> None:
            if 0 <= idx0 < n_cues and expanded[idx0] is None:
                expanded[idx0] = shot

        for shot in matched_shots:
            if not isinstance(shot, dict):
                continue
            cue_ids = shot.get("cue_ids")
            if isinstance(cue_ids, list) and cue_ids:
                for cid in cue_ids:
                    try:
                        place(int(cid) - 1, shot)
                    except (TypeError, ValueError):
                        continue
                continue
            cue_id = shot.get("cue_id")
            if cue_id is not None:
                try:
                    idx0 = int(cue_id) - 1
                except (TypeError, ValueError):
                    continue
                place(idx0, shot)

        # Cues an older/partial response left unmapped fall back to no AI
        # shot (None) rather than misaligning every cue after the gap --
        # the caller already tolerates ai_shot being None per-cue.
        if any(s is None for s in expanded) and not any(expanded):
            # Nothing mapped at all (e.g. a legacy cache with neither key) --
            # positional passthrough matches the pre-merge behavior exactly.
            return list(matched_shots[:n_cues]) + [None] * max(0, n_cues - len(matched_shots))
        return expanded

    @staticmethod
    def _effective_shot_scales(ctx: PipelineContext) -> List[float]:
        shot_scales = LOOK_PRESETS.get(ctx.angle_meta.get("angle_key", "")) if ctx.angle_meta else None
        return shot_scales or [1.25, 1.0, 1.35, 1.05, 1.3, 1.0]

    @staticmethod
    def _compute_smart_fallback_offset(
        g_idx: int,
        total_groups: int,
        raw_duration: float,
        c_dur: float,
        motion_times: Optional[List[float]] = None,
        motion_scores: Optional[List[float]] = None,
        previous_offsets: Optional[List[float]] = None,
    ) -> float:
        """
        Calculates non-linear, well-distributed fallback offsets across raw footage.
        Avoids the rigid (g_idx * 3.5) repetitive crawl by distributing cuts across the
        full duration of the clip, leveraging motion peaks and enforcing anti-duplicate distance.
        """
        max_start = max(0.0, raw_duration - c_dur - 0.5)
        if max_start <= 0.5:
            return 0.0

        num_intervals = max(1, total_groups)
        step = max_start / num_intervals

        # Golden ratio jitter to avoid monotone equidistant steps
        jitter = (g_idx * 0.618033988749895) % 1.0
        target_offset = min(max_start, (g_idx * step) + (jitter * min(step * 0.4, 2.0)))

        # Sweet spot for opening shot (g_idx == 0):
        # Avoid 0.0s recording startup dead air / camera shake
        if g_idx == 0 and raw_duration >= 8.0 and max_start >= 1.5:
            target_offset = max(0.8, min(1.5, target_offset + 0.8))

        raw_offset = target_offset

        # Snap to nearest high-motion action peak if available
        if motion_times and motion_scores:
            window = max(2.0, step * 0.5)
            candidates = [
                (t, s) for t, s in zip(motion_times, motion_scores)
                if abs(t - target_offset) <= window and t + c_dur <= raw_duration
            ]
            if candidates:
                raw_offset = max(candidates, key=lambda ts: ts[1])[0]

        # Anti-collision check: ensure not too close to the immediately preceding shot
        if previous_offsets and len(previous_offsets) > 0:
            last_offset = previous_offsets[-1]
            if abs(raw_offset - last_offset) < 2.0 and max_start >= 4.0:
                shifted = (raw_offset + 2.5) % max_start
                raw_offset = shifted

        return max(0.0, min(max_start, round(raw_offset, 2)))

    @classmethod
    def calculate_contiguous_beat_durations(
        cls,
        beat_cues: List[Dict[str, Any]],
        total_duration: float,
    ) -> List[float]:
        """Calculates contiguous timeline duration slices for each beat cue.

        Guarantees:
        1. Beat 0 starts at 0.0s (absorbing any initial lead-in silence before speech).
        2. Intermediate cuts align with subsequent beat start timestamps without gaps.
        3. The last beat extends exactly to total_duration, preventing any trailing gap.
        4. sum(durations) == total_duration (down to the millisecond).
        """
        if not beat_cues:
            return []
        n = len(beat_cues)
        if n == 1:
            dur = max(0.1, float(total_duration) if total_duration > 0 else float(beat_cues[0].get("end", 0.0)))
            return [round(dur, 3)]

        boundaries = [0.0]
        for i in range(n - 1):
            next_start = float(beat_cues[i + 1].get("start", beat_cues[i].get("end", 0.0)))
            prev_end = float(beat_cues[i].get("end", next_start))
            cut_point = next_start if next_start > boundaries[-1] else max(boundaries[-1] + 0.1, prev_end)
            boundaries.append(round(cut_point, 3))

        end_time = float(total_duration) if total_duration > 0 else float(beat_cues[-1].get("end", boundaries[-1] + 1.0))
        final_end = max(boundaries[-1] + 0.1, round(end_time, 3))
        boundaries.append(final_end)

        durations = []
        for i in range(n):
            dur = max(0.1, round(boundaries[i + 1] - boundaries[i], 3))
            durations.append(dur)

        if total_duration > 0 and durations:
            gap = round(float(total_duration) - sum(durations), 3)
            if abs(gap) >= 0.001:
                durations[-1] = max(0.1, round(durations[-1] + gap, 3))

        return durations

    @classmethod
    def _build_guided_take_clip_list(cls, ctx: PipelineContext, raw_video) -> List[dict]:
        """Exact mapping for a video recorded through the guided-filming flow
        (scripts/recording_sessions.py): each beat's raw footage span
        (`clip_map[i]`, from the concatenated segments) is time-stretched via
        the existing `speed` mechanism (scripts/video_editor.py) to exactly
        fill that beat's real voice-track slot (`ctx.beat_cues[i]`), so the
        final video's timing always matches the fixed narration track.
        """
        clip_map = (ctx.guided_take_meta or {}).get("clip_map") or []
        beat_cues = ctx.beat_cues or []
        if len(beat_cues) != len(clip_map):
            raise AppError(
                category=ErrorCategory.USER_CORRECTABLE,
                code="GUIDED_TAKE_BEAT_MISMATCH",
                message_th="สคริปต์หรือเสียงพากย์เปลี่ยนไปหลังจากสร้างแผนถ่ายและถ่ายทำแล้ว ไม่สามารถแมปช็อตให้ตรงได้อีกต่อไป",
                suggestion_th="กรุณาสร้างแผนถ่าย (Shot List) ใหม่ แล้วถ่ายทำใหม่ให้ตรงกับสคริปต์ปัจจุบัน",
                details=f"beat_cues={len(beat_cues)} beats, clip_map={len(clip_map)} segments",
            )

        effective_shot_scales = cls._effective_shot_scales(ctx)
        durations = cls.calculate_contiguous_beat_durations(beat_cues, ctx.total_duration or 0.0)
        clips = []
        for i, (cue, seg) in enumerate(zip(beat_cues, clip_map)):
            target_duration = durations[i] if i < len(durations) else max(0.1, float(cue.get("end", 0.0)) - float(cue.get("start", 0.0)))
            actual_duration = max(0.1, float(seg.get("actual_duration", target_duration)))
            speed = min(4.0, max(0.25, actual_duration / target_duration))
            zoom = round(float(effective_shot_scales[i % len(effective_shot_scales)]), 2)

            clip_entry = {
                "id": f"clip_{i}",
                "source_path": str(raw_video),
                "trim_start": round(float(seg.get("trim_start", 0.0)), 3),
                "trim_end": round(float(seg.get("trim_end", 0.0)), 3),
                "duration": round(target_duration, 3),
                "speed": round(speed, 4),
                "zoom": zoom,
                "shot_index": i,
                "transition_in": "cut",
            }
            camera_keyframes = camera_keyframes_for_clip(zoom, target_duration, i, style_preset=ctx.style_preset)
            if camera_keyframes:
                clip_entry["keyframes"] = camera_keyframes
            clips.append(clip_entry)
        return clips

    @classmethod
    def _build_proportional_clip_list(cls, ctx: PipelineContext, raw_video, raw_duration: float) -> List[dict]:
        """Fallback mapping for a video uploaded the normal way (not through
        the guided-filming flow) but explicitly attached to a shot list via
        "map to this shot list" -- there is no per-segment tag, so each
        beat's slice of the raw footage is only a PROPORTIONAL share (by
        planned-duration ratio) rather than an exact position. This makes
        every beat's speed factor come out to the same constant
        (raw_duration / total_planned_duration) by construction -- the whole
        clip is uniformly time-stretched to match the fixed voice track
        while each beat's raw-footage slice is proportional to its planned
        share. That's intentional, not a bug: this mode makes no frame-exact
        claim, unlike `_build_guided_take_clip_list` above.
        """
        beat_cues = ctx.beat_cues or []
        durations = cls.calculate_contiguous_beat_durations(beat_cues, ctx.total_duration or 0.0)
        total_planned = sum(durations) or ctx.total_duration or raw_duration
        global_speed = min(4.0, max(0.25, raw_duration / total_planned)) if total_planned > 0 else 1.0

        effective_shot_scales = cls._effective_shot_scales(ctx)
        clips = []
        cursor = 0.0
        for i, cue in enumerate(beat_cues):
            target_duration = durations[i] if i < len(durations) else max(0.1, float(cue.get("end", 0.0)) - float(cue.get("start", 0.0)))
            ratio = (target_duration / total_planned) if total_planned > 0 else (1.0 / len(beat_cues))
            trim_start = cursor
            trim_end = min(raw_duration, cursor + ratio * raw_duration)
            cursor = trim_end
            zoom = round(float(effective_shot_scales[i % len(effective_shot_scales)]), 2)

            clip_entry = {
                "id": f"clip_{i}",
                "source_path": str(raw_video),
                "trim_start": round(trim_start, 3),
                "trim_end": round(trim_end, 3),
                "duration": round(target_duration, 3),
                "speed": round(global_speed, 4),
                "zoom": zoom,
                "shot_index": i,
                "transition_in": "cut",
            }
            camera_keyframes = camera_keyframes_for_clip(zoom, target_duration, i, style_preset=ctx.style_preset)
            if camera_keyframes:
                clip_entry["keyframes"] = camera_keyframes
            clips.append(clip_entry)
        return clips

    @classmethod
    def _build_manual_storyboard_clip_list(
        cls,
        ctx: PipelineContext,
        raw_video,
        raw_duration: float,
    ) -> List[dict]:
        """Build clip list directly from user's manual storyboard pins mapped
        to script beat_cues (1 clip per beat).

        For pinned beats: uses the chosen video, trim_start, and trim_end,
        calculating playback speed to fit the beat duration cleanly.
        For unpinned beats: falls back to proportional slice of raw_video.
        Total clips will strictly match len(ctx.beat_cues), preventing any
        trailing overflow clips beyond the voiceover duration.
        """
        import pathlib
        from scripts import path_utils as _path_utils

        beat_cues = ctx.beat_cues or []
        if not beat_cues:
            return []

        pin_by_beat = {
            int(p["beat_index"]): p
            for p in (ctx.manual_shot_map or [])
            if p.get("video_path") and "beat_index" in p
        }

        effective_shot_scales = cls._effective_shot_scales(ctx)
        durations = cls.calculate_contiguous_beat_durations(beat_cues, ctx.total_duration or 0.0)
        clips = []
        cursor = 0.0
        total_planned = sum(durations) or ctx.total_duration or raw_duration

        for i, cue in enumerate(beat_cues):
            target_duration = durations[i] if i < len(durations) else max(0.1, float(cue.get("end", 0.0)) - float(cue.get("start", 0.0)))
            zoom = round(float(effective_shot_scales[i % len(effective_shot_scales)]), 2)

            if i in pin_by_beat:
                pin = pin_by_beat[i]
                raw_p = pin["video_path"]
                abs_p = _path_utils.to_absolute(raw_p)
                resolved = str(abs_p) if (abs_p and abs_p.exists()) else raw_p

                trim_start = round(float(pin.get("trim_start") or 0.0), 3)
                trim_end = round(float(pin.get("trim_end") or 0.0), 3)
                trim_span = max(0.05, trim_end - trim_start)
                speed = round(min(4.0, max(0.25, trim_span / target_duration)), 4)

                clip_entry = {
                    "id": f"clip_{i}",
                    "source_path": resolved,
                    "trim_start": trim_start,
                    "trim_end": trim_end,
                    "duration": round(target_duration, 3),
                    "speed": speed,
                    "zoom": zoom,
                    "shot_index": i,
                    "manual_pinned": True,
                    "transition_in": "cut",
                }
                print(
                    f"   📌 [ManualStoryboard] Beat {i} ({target_duration:.2f}s) → "
                    f"{pathlib.Path(resolved).name} [{trim_start:.2f}–{trim_end:.2f}s] (spd: {speed:.2f}x)"
                )
            else:
                ratio = (target_duration / total_planned) if total_planned > 0 else (1.0 / len(beat_cues))
                trim_start = cursor
                trim_end = min(raw_duration, cursor + ratio * raw_duration)
                cursor = trim_end
                trim_span = max(0.05, trim_end - trim_start)
                speed = round(min(4.0, max(0.25, trim_span / target_duration)), 4)

                clip_entry = {
                    "id": f"clip_{i}",
                    "source_path": str(raw_video) if raw_video else "",
                    "trim_start": round(trim_start, 3),
                    "trim_end": round(trim_end, 3),
                    "duration": round(target_duration, 3),
                    "speed": speed,
                    "zoom": zoom,
                    "shot_index": i,
                    "manual_pinned": False,
                    "transition_in": "cut",
                }
                print(
                    f"   🤖 [Storyboard-Auto] Beat {i} ({target_duration:.2f}s) → Proportional slice [{trim_start:.2f}–{trim_end:.2f}s]"
                )

            camera_keyframes = camera_keyframes_for_clip(zoom, target_duration, i, style_preset=ctx.style_preset)
            if camera_keyframes:
                clip_entry["keyframes"] = camera_keyframes

            clips.append(clip_entry)

        return clips


    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        raw_video = ctx.raw_video
        total_duration = ctx.total_duration
        cues = ctx.cues
        micro_cues = ctx.micro_cues

        # If source is still images, generate 9:16 Ken-Burns motion video footage first
        if ctx.is_image_source and ctx.image_files and ctx.project_dir:
            ctx.notify("🖼️ [Image Motion] สร้างวิดีโอ 9:16 Motion Slideshow จากรูปภาพสินค้า...", 0.70)
            print(f"\n🖼️ [Image Motion] Generating 9:16 Motion Slideshow from {len(ctx.image_files)} product images...")
            motion_raw_path = ctx.project_dir / "image_motion_footage.mp4"

            def _on_image_motion_progress(current_idx: int, total_segs: int, detail: str = ""):
                # Progress smoothly rises from 0.70 to 0.75
                pct = 0.70 + 0.05 * (current_idx / max(1, total_segs))
                msg = f"🖼️ [Image Motion] สร้างวิดีโอจากภาพสินค้า ({current_idx}/{total_segs})..."
                ctx.notify(msg, round(pct, 2))
                print(f"   🎬 [Image Motion] Segment {current_idx}/{total_segs} ready")

            ImageMotionEngine.ensure_motion_video_from_images(
                image_paths=ctx.image_files,
                cues=cues,
                total_duration=total_duration,
                output_video_path=str(motion_raw_path),
                project_dir=ctx.project_dir,
                progress_callback=_on_image_motion_progress,
            )
            raw_video = motion_raw_path
            ctx.raw_video = raw_video
            ctx.use_ai_vision = False

        raw_duration = 60.0
        if raw_video:
            try:
                raw_info = VideoEditor.get_media_info(str(raw_video))
                raw_duration = float(raw_info.get("duration", 60.0))
            except Exception:
                raw_duration = 60.0

        has_manual_clips = bool(ctx.clip_list and len(ctx.clip_list) > 0)
        actual_clip_list = ctx.clip_list if has_manual_clips else None
        is_newly_generated_clips = False

        # Guided-take / proportional mapping (scripts/recording_sessions.py,
        # scripts/shot_list_builder.py) -- takes priority over AI Vision and
        # rhythmic-fallback matching below, since it maps beats onto footage
        # deterministically instead of guessing. See
        # C:\Users\Winon\.claude\plans\cheeky-cooking-quokka.md (Phase D).
        if not actual_clip_list and raw_video and ctx.guided_take_meta:
            actual_clip_list = cls._build_guided_take_clip_list(ctx, raw_video)
            is_newly_generated_clips = True
        elif not actual_clip_list and ctx.manual_shot_map and ctx.beat_cues:
            actual_clip_list = cls._build_manual_storyboard_clip_list(ctx, raw_video, raw_duration)
            is_newly_generated_clips = True
        elif not actual_clip_list and raw_video and ctx.shot_list_id and ctx.beat_cues:
            actual_clip_list = cls._build_proportional_clip_list(ctx, raw_video, raw_duration)
            is_newly_generated_clips = True

        ai_matched_shots = None
        if not actual_clip_list and raw_video and ctx.use_ai_vision and GeminiVisionMatcher.is_available():
            vision_request = GeminiVisionMatcher.prepare_request_context(str(raw_video), micro_cues)
            cached_shots = (
                vision_request.cached_matches
                if vision_request is not None
                else GeminiVisionMatcher.get_cached_matches(str(raw_video), micro_cues)
            )
            if cached_shots:
                print(f"   ⚡ [AI Vision] Reusing {len(cached_shots)} cached scene matches (Instant 0s)")
                ai_matched_shots = cls._expand_ai_shots_to_cues(cached_shots, len(micro_cues))
            else:
                ctx.notify("👁️ [AI Vision] ให้ Gemini 2.5 Flash ดูคลิปและเลือกฉากที่ตรงกับสคริปต์ (ครั้งแรก)...", 0.76)
                print("\n👁️ [AI Vision] Gemini 2.5 Flash is analyzing raw footage scenes (first time)...")
                try:
                    raw_matched_shots = GeminiVisionMatcher.match_script_to_video(
                        raw_video_path=str(raw_video),
                        cues=micro_cues,
                        raw_duration=raw_duration,
                        request_context=vision_request,
                    )
                    # Gemini now merges consecutive micro-cues that belong to
                    # the same sentence/idea into one shot (cue_ids: [5,6,7]
                    # instead of a 1:1 cue_id), so the cut rhythm follows
                    # sentence beats instead of forcing a new shot every
                    # micro-cue. The grouping/anchor logic a few dozen lines
                    # below still indexes ai_matched_shots positionally by
                    # micro-cue (ai_matched_shots[anchor_idx]), so the merged
                    # response is expanded back to one entry per micro-cue
                    # here -- every cue inside a merged shot points at the
                    # same AI shot -- rather than touching that indexing.
                    ai_matched_shots = cls._expand_ai_shots_to_cues(raw_matched_shots, len(micro_cues))
                    ctx.notify("👁️ [AI Vision] จับคู่ฉากสมบูรณ์ กำลังส่งต่อให้ขั้นตอนตัดต่อ...", 0.82)
                except Exception as e:
                    # A quota hit means the user's own daily AI budget cap
                    # stopped this call -- not a Gemini/network failure. AI
                    # Vision matching is a quality enhancement (it only
                    # refines which scenes get picked); its absence never
                    # blocks the render, since the code below already
                    # tolerates ai_matched_shots staying None and falls back
                    # to rhythmic/beat-synced cuts. So we keep that graceful
                    # degradation instead of failing the whole render over a
                    # non-essential feature -- but the reason must be loud
                    # and visible in the job's own progress log, not just a
                    # server-side print, so the user knows it was their
                    # budget cap and not a broken provider.
                    if is_quota_error(e):
                        ctx.notify(
                            "⚠️ เกินโควต้า AI ต่อวันแล้ว — ข้าม AI Vision Matching ใช้จังหวะตัดต่อแบบ rhythmic cuts แทน",
                            0.82,
                        )
                        print(f"   ⚠️ AI Vision Matching skipped: quota exceeded ({e}) — using rhythmic cuts.")
                    else:
                        print(f"   ⚠️ AI Vision Matching skipped ({e}) — using rhythmic cuts.")

        shot_scales = LOOK_PRESETS.get(ctx.angle_meta.get("angle_key", "")) if ctx.angle_meta else None

        beat_times: List[float] = []
        try:
            resolved_bgm_path = SFXManager.resolve_bgm_path(ctx.effective_bgm_name)
            if resolved_bgm_path:
                beat_times = BeatSync.get_beat_times(resolved_bgm_path)
        except Exception:
            beat_times = []

        energy_times: List[float] = []
        energy_rms: List[float] = []
        energy_mean: Optional[float] = None
        energy_std: Optional[float] = None
        try:
            energy_times, energy_rms = (
                BeatSync.get_rms_energy(ctx.mixed_audio_path) if ctx.mixed_audio_path else ([], [])
            )
            if energy_rms:
                energy_mean = sum(energy_rms) / len(energy_rms)
                variance = sum((r - energy_mean) ** 2 for r in energy_rms) / len(energy_rms)
                energy_std = variance ** 0.5
        except Exception:
            energy_times, energy_rms, energy_mean, energy_std = [], [], None, None
        energy_peak = max(energy_rms) if energy_rms else None

        motion_times: List[float] = []
        motion_scores: List[float] = []
        try:
            if raw_video:
                motion_times, motion_scores = MotionAnalyzer.get_motion_scores(raw_video)
        except Exception:
            motion_times, motion_scores = [], []

        from scripts.pipeline import choose_transition

        if not actual_clip_list and raw_video:
            try:
                active_cues = micro_cues if (micro_cues and len(micro_cues) > 0) else cues
                effective_shot_scales = shot_scales or [1.25, 1.0, 1.35, 1.05, 1.3, 1.0]
                shots = []
                if active_cues:
                    from scripts.config import J_CUT_OFFSET_SECONDS, MIN_SHOT_DURATION, MAX_SHOT_DURATION
                    n_cues = len(active_cues)
                    pacing_boundaries = resolve_pacing_boundaries(
                        ctx.editorial_pacing,
                        total_duration,
                        min_segment_duration=MIN_SHOT_DURATION,
                    )
                    # Start at the first cue's actual start time (not 0.0).
                    # Gemini TTS generates ~0.1–0.4s of silence at the very
                    # beginning of the WAV before the first word; the cue
                    # timestamps already reflect that offset because they come
                    # from the real per-cue start times written by the TTS stage.
                    # Hardcoding 0.0 here made the first shot longer than the
                    # audio it covers and created a visible silent gap at the
                    # start of every render.
                    first_cue_start = float(active_cues[0].get("start", 0.0))
                    cut_points = [first_cue_start]
                    for i in range(1, n_cues):
                        c_curr_start = float(active_cues[i].get("start", 0.0))
                        prev_dur = float(active_cues[i - 1].get("end", 0.0)) - float(active_cues[i - 1].get("start", 0.0))
                        curr_dur = float(active_cues[i].get("end", 0.0)) - float(active_cues[i].get("start", 0.0))
                        lead = min(J_CUT_OFFSET_SECONDS, prev_dur * 0.25, curr_dur * 0.25, 0.25)
                        cut_points.append(round(c_curr_start + lead, 3))
                    cut_points.append(round(total_duration, 3))

                    groups: List[List[int]] = []
                    if pacing_boundaries:
                        # Beat boundaries are already word-safe. Choose the
                        # cue covering each segment midpoint only for content
                        # and AI-shot anchoring; the boundaries themselves are
                        # the single source of timing truth.
                        boundary_times = pacing_boundaries
                        for segment_start, segment_end in zip(boundary_times, boundary_times[1:]):
                            midpoint = (segment_start + segment_end) / 2.0
                            anchor_idx = next(
                                (
                                    idx for idx, cue in enumerate(active_cues)
                                    if float(cue.get("start", 0.0)) <= midpoint < float(cue.get("end", 0.0))
                                ),
                                n_cues - 1,
                            )
                            groups.append([anchor_idx])
                    else:
                        current: List[int] = []
                        group_start = cut_points[0]
                        for i in range(n_cues):
                            tentative_dur = cut_points[i + 1] - group_start
                            if current and tentative_dur > MAX_SHOT_DURATION:
                                groups.append(current)
                                current = []
                                group_start = cut_points[i]
                            current.append(i)
                            held_dur = cut_points[i + 1] - group_start
                            if held_dur >= MIN_SHOT_DURATION and i < n_cues - 1:
                                groups.append(current)
                                current = []
                                group_start = cut_points[i + 1]
                        if current:
                            groups.append(current)

                    if not pacing_boundaries:
                        # Two-pass merge to eliminate under-MIN_SHOT_DURATION groups.
                        #
                        # Pass 1 (greedy, tolerant): merge any group below MIN
                        # into a neighbour if the combined duration stays within
                        # MAX * MERGE_TOLERANCE.  This covers most cases cleanly.
                        #
                        # Pass 2 (force-merge ultra-short): any group that is still
                        # below MIN / 2 after pass 1 is force-merged into its
                        # *shorter* neighbour regardless of the MAX ceiling.
                        # Example: `นะครับ` (0.49 s) sandwiched between two 2.5 s
                        # shots would previously stay as a 0.49 s clip because
                        # merging with either neighbour would land at ~3.0 s,
                        # slightly above MAX * 1.15 = 2.875 s.  A 3.0 s clip is
                        # far less damaging than a 0.49 s clip, so we force it.
                        # MERGE_TOLERANCE = 1.5 (up from the original 1.15):
                        # TikTok content often has very short phrase clips (~1.2 s)
                        # flanked by ~2.2 s clips, giving combined ~3.4 s.
                        # At 1.15× MAX (= 2.875 s) those could never merge; 1.5×
                        # MAX (= 3.75 s) covers those real-world pairs while still
                        # preventing truly excessively long shots (>3.75 s).
                        MERGE_TOLERANCE = 1.5
                        FORCE_MERGE_THRESHOLD = MIN_SHOT_DURATION * 0.5

                        # Pass 1 – standard tolerance merge
                        changed = True
                        while changed:
                            changed = False
                            for gi, g in enumerate(groups):
                                dur = cut_points[g[-1] + 1] - cut_points[g[0]]
                                if dur >= MIN_SHOT_DURATION:
                                    continue
                                if gi > 0:
                                    prev = groups[gi - 1]
                                    merged_dur = cut_points[g[-1] + 1] - cut_points[prev[0]]
                                    if merged_dur <= MAX_SHOT_DURATION * MERGE_TOLERANCE:
                                        groups[gi - 1] = prev + g
                                        del groups[gi]
                                        changed = True
                                        break
                                if gi < len(groups) - 1:
                                    nxt = groups[gi + 1]
                                    merged_dur = cut_points[nxt[-1] + 1] - cut_points[g[0]]
                                    if merged_dur <= MAX_SHOT_DURATION * MERGE_TOLERANCE:
                                        groups[gi] = g + nxt
                                        del groups[gi + 1]
                                        changed = True
                                        break

                        # Pass 2 – force-merge ultra-short clips (< MIN/2)
                        changed = True
                        while changed:
                            changed = False
                            for gi, g in enumerate(groups):
                                dur = cut_points[g[-1] + 1] - cut_points[g[0]]
                                if dur >= FORCE_MERGE_THRESHOLD:
                                    continue
                                # Pick the neighbour with the shorter duration
                                # so the combined result stays as balanced as possible.
                                prev_dur_val = (
                                    cut_points[groups[gi - 1][-1] + 1] - cut_points[groups[gi - 1][0]]
                                    if gi > 0 else float("inf")
                                )
                                next_dur_val = (
                                    cut_points[groups[gi + 1][-1] + 1] - cut_points[groups[gi + 1][0]]
                                    if gi < len(groups) - 1 else float("inf")
                                )
                                if prev_dur_val <= next_dur_val and gi > 0:
                                    groups[gi - 1] = groups[gi - 1] + g
                                    del groups[gi]
                                    changed = True
                                    break
                                elif gi < len(groups) - 1:
                                    groups[gi] = g + groups[gi + 1]
                                    del groups[gi + 1]
                                    changed = True
                                    break

                    if not pacing_boundaries:
                        boundary_times = [cut_points[0]] + [cut_points[g[-1] + 1] for g in groups]
                    if motion_times and not pacing_boundaries:
                        MOTION_SNAP_TOLERANCE = 0.15
                        for b_idx in range(1, len(boundary_times) - 1):
                            trough = MotionAnalyzer.nearest_trough(
                                motion_times, motion_scores, boundary_times[b_idx], MOTION_SNAP_TOLERANCE
                            )
                            if trough is not None:
                                prev_b = boundary_times[b_idx - 1]
                                next_b = boundary_times[b_idx + 1]
                                if (trough - prev_b) >= MIN_SHOT_DURATION * 0.8 and (next_b - trough) >= MIN_SHOT_DURATION * 0.8:
                                    boundary_times[b_idx] = round(trough, 3)
                    if beat_times and not pacing_boundaries:
                        BEAT_SNAP_TOLERANCE = 0.15
                        for b_idx in range(1, len(boundary_times) - 1):
                            t = boundary_times[b_idx]
                            nearest = min(beat_times, key=lambda bt: abs(bt - t))
                            if abs(nearest - t) <= BEAT_SNAP_TOLERANCE:
                                prev_b = boundary_times[b_idx - 1]
                                next_b = boundary_times[b_idx + 1]
                                if (nearest - prev_b) >= MIN_SHOT_DURATION * 0.8 and (next_b - nearest) >= MIN_SHOT_DURATION * 0.8:
                                    boundary_times[b_idx] = round(nearest, 3)

                    emphasis_scale_idx = effective_shot_scales.index(max(effective_shot_scales))

                    group_texts = [
                        " ".join(str(active_cues[i].get("text", "")) for i in g).strip()
                        for g in groups
                    ]
                    tone_shifts = ScriptToneAnalyzer.classify_tone_shifts(group_texts)

                    auto_transitions = []
                    for g_idx, group in enumerate(groups):
                        v_start = boundary_times[g_idx]
                        v_end = boundary_times[g_idx + 1]
                        c_dur = max(0.2, v_end - v_start)
                        anchor_idx = group[0]
                        ai_shot = ai_matched_shots[anchor_idx] if ai_matched_shots and anchor_idx < len(ai_matched_shots) else None

                        motion_score = (
                            MotionAnalyzer.segment_mean_score(motion_times, motion_scores, v_start, v_end)
                            if motion_times else None
                        )
                        energy_score = None
                        if energy_peak and energy_rms:
                            seg_energy = BeatSync.segment_mean_energy(energy_times, energy_rms, v_start, v_end)
                            if seg_energy is not None:
                                energy_score = min(1.0, seg_energy / energy_peak)

                        if motion_score is not None and energy_score is not None:
                            emphasis_score = 0.6 * motion_score + 0.4 * energy_score
                        elif motion_score is not None:
                            emphasis_score = motion_score
                        elif energy_score is not None:
                            emphasis_score = energy_score
                        else:
                            emphasis_score = None

                        base_scale = effective_shot_scales[g_idx % len(effective_shot_scales)]
                        max_scale = effective_shot_scales[emphasis_scale_idx]

                        if ai_shot:
                            ai_start = float(ai_shot.get("start_time", 0.0))
                            if pacing_boundaries:
                                cue_start = float(active_cues[anchor_idx].get("start", 0.0))
                                ai_start += max(0.0, v_start - cue_start)
                            ai_zoom = float(ai_shot.get("punch_zoom", base_scale))
                            scale = min(1.4, max(1.0, ai_zoom))
                            raw_offset = max(0.0, min(ai_start, max(0.0, raw_duration - c_dur - 0.2)))
                        else:
                            if emphasis_score is not None:
                                scale = base_scale + (max_scale - base_scale) * emphasis_score
                            else:
                                has_emphasis = any(
                                    active_cues[i].get("sfx") or "!" in str(active_cues[i].get("text", ""))
                                    or any(e in str(active_cues[i].get("text", "")) for e in ("⚠️", "❌", "⚡"))
                                    for i in group
                                )
                                scale = max_scale if has_emphasis else base_scale

                            previous_offsets = [s["raw_offset"] for s in shots]
                            raw_offset = cls._compute_smart_fallback_offset(
                                g_idx=g_idx,
                                total_groups=len(groups),
                                raw_duration=raw_duration,
                                c_dur=c_dur,
                                motion_times=motion_times,
                                motion_scores=motion_scores,
                                previous_offsets=previous_offsets,
                            )

                        shots.append({
                            "start": v_start,
                            "end": v_end,
                            "scale": scale,
                            "raw_offset": raw_offset
                        })

                        if g_idx > 0:
                            prev_last_cue = active_cues[groups[g_idx - 1][-1]]
                            next_first_cue = active_cues[group[0]]
                            gap = float(next_first_cue.get("start", 0.0)) - float(prev_last_cue.get("end", 0.0))
                            prev_text = str(prev_last_cue.get("text", "")).strip()
                            sentence_end = prev_text.endswith((".", "!", "?", "ครับ", "ค่ะ", "นะคะ", "นะครับ"))
                            tone = tone_shifts[g_idx - 1] if (g_idx - 1) < len(tone_shifts) else "none"

                            previous_type = None
                            if auto_transitions:
                                last = auto_transitions[-1]
                                previous_type = last.get("type") if isinstance(last, dict) else str(last)
                            pick = choose_transition(
                                shots[g_idx - 1].get("scale") if g_idx - 1 < len(shots) else 1.0,
                                scale,
                                g_idx,
                                previous_type,
                                tone,
                            )
                            if tone != "major" and gap > 0.6:
                                pick["duration"] = max(pick["duration"], 0.35)
                            elif tone != "major" and not (gap > 0.35 or sentence_end):
                                pick["duration"] = min(pick["duration"], 0.25)
                            pick = apply_transition_budget(
                                pick,
                                style_preset=ctx.style_preset,
                                boundary_index=g_idx,
                            )
                            auto_transitions.append(pick)

                    if not ctx.transitions and auto_transitions:
                        ctx.transitions = auto_transitions
                else:
                    curr_t = 0.0
                    shot_idx = 0
                    while curr_t < total_duration:
                        dur = 2.0
                        end_t = min(curr_t + dur, total_duration)
                        scale = effective_shot_scales[shot_idx % len(effective_shot_scales)]
                        raw_offset = (shot_idx * 3.5) % max(1.0, raw_duration - dur - 1.0)
                        shots.append({
                            "start": curr_t,
                            "end": end_t,
                            "scale": scale,
                            "raw_offset": raw_offset
                        })
                        curr_t = end_t
                        shot_idx += 1

                generated_clips = []
                for idx, shot in enumerate(shots):
                    s_dur = max(0.2, shot["end"] - shot["start"])
                    raw_start_offset = float(shot.get("raw_offset", 0.0))
                    trim_end = round(raw_start_offset + s_dur, 3)
                    boundary = ctx.transitions[idx - 1] if (idx > 0 and ctx.transitions and idx - 1 < len(ctx.transitions)) else None
                    if isinstance(boundary, dict):
                        t_in, t_dur = boundary.get("type", "cut"), boundary.get("duration")
                    elif isinstance(boundary, str):
                        t_in, t_dur = boundary, None
                    else:
                        t_in, t_dur = "cut", None
                    clip_entry = {
                        "id": f"clip_{idx}",
                        "source_path": str(raw_video),
                        "trim_start": round(raw_start_offset, 3),
                        "trim_end": trim_end,
                        "duration": round(s_dur, 3),
                        "speed": 1.0,
                        "zoom": round(float(shot.get("scale", 1.0)), 2),
                        "shot_index": idx,
                        "transition_in": t_in,
                    }
                    if t_dur is not None:
                        clip_entry["transition_duration"] = float(t_dur)
                    camera_keyframes = camera_keyframes_for_clip(
                        clip_entry["zoom"],
                        s_dur,
                        idx,
                        style_preset=ctx.style_preset,
                    )
                    if camera_keyframes:
                        clip_entry["keyframes"] = camera_keyframes
                    generated_clips.append(clip_entry)
                actual_clip_list = generated_clips
                is_newly_generated_clips = True
            except Exception as shot_err:
                # Same reasoning as the AI Vision handler above: a quota hit is
                # the user's own daily cap, not a provider failure, and the
                # single-clip fallback below hides that distinction unless it
                # is said out loud in the job's progress log.
                if is_quota_error(shot_err):
                    ctx.notify(
                        "⚠️ เกินโควต้า AI ต่อวันแล้ว — ข้ามการวิเคราะห์โทนบท ใช้คลิปเดียวตลอดความยาวแทน",
                        0.85,
                    )
                    print(f"Warning: tone-shift analysis skipped: quota exceeded ({shot_err})")
                else:
                    # Anything else here is NOT an expected/recoverable
                    # failure mode -- AI Vision matching and beat/motion/BGM
                    # analysis each already have their own narrow try/except
                    # further up this method and never reach this block, so
                    # whatever lands here is a genuine bug in shot planning
                    # (e.g. malformed cue data). The single-clip fallback
                    # below still runs -- one static clip beats a hard-failed
                    # render -- but it must not look like a normal render:
                    # surface it the same way the quota branch does (visible
                    # in the live progress log) and record it on the job
                    # result so it's still visible after the render finishes,
                    # instead of only existing in a server-side print no one
                    # sees.
                    warning_msg = (
                        f"Unexpected error generating shot plan, fell back to a "
                        f"single static clip for the whole render: {shot_err}"
                    )
                    ctx.notify(
                        "⚠️ เกิดข้อผิดพลาดไม่คาดคิดระหว่างวางแผนช็อต — ใช้คลิปเดียวตลอดความยาวแทน",
                        0.85,
                    )
                    print(f"Warning: {warning_msg}")
                    ctx.result_paths["shot_matching_degraded"] = warning_msg
                actual_clip_list = [{
                    "id": "clip_0",
                    "source_path": str(raw_video),
                    "trim_start": 0.0,
                    "trim_end": round(total_duration, 3),
                    "duration": round(total_duration, 3),
                    "speed": 1.0,
                    "transition_in": "cut"
                }]
                is_newly_generated_clips = True

        ctx.actual_clip_list = actual_clip_list
        ctx.ai_matched_shots = ai_matched_shots
        ctx.shot_scales = shot_scales
        ctx.is_newly_generated_clips = is_newly_generated_clips

        # ── Manual Storyboard Mapper overrides ─────────────────────────────
        # If the user pinned specific beat→scene assignments via the Manual
        # Storyboard UI, enforce storyboard beat mapping.
        # This guarantees that regardless of which fallback path built the
        # initial clip list, clips are strictly aligned with beat_cues and
        # never spill beyond voiceover duration.
        if actual_clip_list and ctx.manual_shot_map:
            from scripts import path_utils as _path_utils
            pin_by_beat = {
                int(p["beat_index"]): p
                for p in ctx.manual_shot_map
                if p.get("video_path") and "beat_index" in p
            }
            if pin_by_beat:
                # Truncate any excess clips beyond beat_cues
                if ctx.beat_cues and len(actual_clip_list) > len(ctx.beat_cues):
                    print(
                        f"   ✂️ [ManualShotMap] Truncating {len(actual_clip_list)} clips to "
                        f"{len(ctx.beat_cues)} beats to match storyboard."
                    )
                    actual_clip_list = actual_clip_list[:len(ctx.beat_cues)]

                durations = cls.calculate_contiguous_beat_durations(ctx.beat_cues or [], ctx.total_duration or 0.0)
                for i, clip in enumerate(actual_clip_list):
                    cue = ctx.beat_cues[i] if (ctx.beat_cues and i < len(ctx.beat_cues)) else None
                    target_duration = durations[i] if i < len(durations) else (max(0.1, float(cue.get("end", 0.0)) - float(cue.get("start", 0.0))) if cue else float(clip.get("duration", 2.0)))

                    clip["shot_index"] = i
                    clip["duration"] = round(target_duration, 3)

                    if i not in pin_by_beat:
                        continue

                    pin = pin_by_beat[i]
                    raw_p = pin["video_path"]
                    abs_p = _path_utils.to_absolute(raw_p)
                    resolved = str(abs_p) if (abs_p and abs_p.exists()) else raw_p

                    trim_start = round(float(pin.get("trim_start") or 0.0), 3)
                    trim_end = round(float(pin.get("trim_end") or 0.0), 3)
                    trim_span = max(0.05, trim_end - trim_start)

                    clip["source_path"] = resolved
                    clip["trim_start"] = trim_start
                    clip["trim_end"] = trim_end
                    clip["speed"] = round(min(4.0, max(0.25, trim_span / target_duration)), 4)
                    clip["manual_pinned"] = True
                    print(
                        f"   📌 [ManualShotMap] Beat {i} ({target_duration:.2f}s) → "
                        f"{resolved} [{trim_start:.2f}–{trim_end:.2f}s] (spd: {clip['speed']:.2f}x)"
                    )

                if ctx.transitions and len(ctx.transitions) >= len(actual_clip_list):
                    ctx.transitions = ctx.transitions[:max(0, len(actual_clip_list) - 1)]

                ctx.actual_clip_list = actual_clip_list
