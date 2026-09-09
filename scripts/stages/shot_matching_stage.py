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
from scripts.quota import is_quota_error


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
            ImageMotionEngine.generate_motion_video_from_images(
                image_paths=ctx.image_files,
                cues=cues,
                total_duration=total_duration,
                output_video_path=str(motion_raw_path),
                project_dir=ctx.project_dir
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

        ai_matched_shots = None
        if not actual_clip_list and raw_video and ctx.use_ai_vision and os.environ.get("GEMINI_API_KEY"):
            cached_shots = GeminiVisionMatcher.get_cached_matches(str(raw_video), micro_cues)
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
                        raw_duration=raw_duration
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
                    cut_points = [0.0]
                    for i in range(1, n_cues):
                        c_curr_start = float(active_cues[i].get("start", 0.0))
                        prev_dur = float(active_cues[i - 1].get("end", 0.0)) - float(active_cues[i - 1].get("start", 0.0))
                        curr_dur = float(active_cues[i].get("end", 0.0)) - float(active_cues[i].get("start", 0.0))
                        lead = min(J_CUT_OFFSET_SECONDS, prev_dur * 0.25, curr_dur * 0.25, 0.25)
                        cut_points.append(round(c_curr_start + lead, 3))
                    cut_points.append(round(total_duration, 3))

                    groups: List[List[int]] = []
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

                    MERGE_TOLERANCE = 1.15
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

                    boundary_times = [cut_points[0]] + [cut_points[g[-1] + 1] for g in groups]
                    if motion_times:
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
                    if beat_times:
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

                            target_offset = (g_idx * 3.5) % max(1.0, raw_duration - c_dur - 1.0)
                            raw_offset = target_offset
                            if motion_times:
                                window = 2.0
                                candidates = [
                                    (t, s) for t, s in zip(motion_times, motion_scores)
                                    if abs(t - target_offset) <= window and t + c_dur <= raw_duration
                                ]
                                if candidates:
                                    raw_offset = max(candidates, key=lambda ts: ts[1])[0]

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
