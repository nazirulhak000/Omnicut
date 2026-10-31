"""
Script Stage for OmniCut Pro Studio.
Generates or prepares TikTok script cues using custom script, AIBridge, ScriptGenerator, or manifest reuse.
"""

from scripts.ai_bridge import AIBridge
from scripts.script_generator import ScriptGenerator
from scripts.pipeline_context import PipelineContext, normalize_story_format, normalize_target_duration
from scripts.quota import is_quota_error
from scripts.compliance_lint import enforce_script_compliance, format_violations_th, lint_script


class ScriptStage:
    """Handles script generation, formatting, and cue parsing."""

    @classmethod
    def run(cls, ctx: PipelineContext) -> None:
        if ctx.should_run("script"):
            ctx.notify("🧠 [1/5] วิเคราะห์สินค้าและจัดเตรียมสคริปต์ TikTok...", 0.10)
            print("🧠 [1/5] Setting up TikTok Script & Cues...")

            if ctx.custom_script:
                overlays = ctx.script_overlays or []
                lines = [
                    {
                        "text": l.strip(),
                        "sfx": "pop" if i > 0 else "whoosh",
                        "on_screen": (overlays[i].strip() if i < len(overlays) else "")
                    }
                    for i, l in enumerate(ctx.custom_script.strip().split("\n"))
                    if l.strip()
                ]
                if lines:
                    lines[-1]["sfx"] = "cash"
                script_data = {
                    "hook": lines[0]["text"] if lines else ctx.product_name,
                    "lines": lines,
                    "full_text": "\n".join([l["text"] for l in lines])
                }
                # The user's own script is never rewritten, but a price/claim
                # hit must not pass silently either.
                custom_hits = lint_script(script_data)
                if custom_hits:
                    print(
                        "⚠️ [Pipeline] สคริปต์ที่ผู้ใช้เขียนเองมีจุดผิดกฎ compliance (ไม่แก้ให้อัตโนมัติ):\n"
                        f"{format_violations_th(custom_hits)}"
                    )
                    ctx.notify("⚠️ สคริปต์มีคำเรื่องราคา/เคลมเกินจริง/เปิดคลิปด้วยคำขอให้หยุดดู — ควรแก้ก่อนโพสต์", 0.10)
            else:
                ai_script = None
                if AIBridge.is_available():
                    try:
                        ctx.notify("🧠 [1/5] ให้ AI Pro วิเคราะห์จุดขายและเขียนบทพากย์พร้อมแปล...", 0.12)
                        print("✨ [1/5] Generating dynamic script via AIBridge...")
                        ai_ctx = {
                            "product_name": ctx.product_name,
                            "angle_title": ctx.angle_meta.get("title", "รีวิวสินค้า") if ctx.angle_meta else "รีวิวสินค้าสุดปัง",
                            # Default hook opens with a concrete question, not a
                            # "stop scrolling / watch this" filler (Q3).
                            "hook": ctx.angle_meta.get("hook", "") if ctx.angle_meta else f"{ctx.product_name} ใช้งานจริงเป็นยังไง เดี๋ยวให้ดูกับตา",
                            "specs": [{"label": "จุดเด่น", "value": ctx.key_features[:60]}],
                            "price_deal": ctx.price_deal
                        }
                        # M3 retention controls. Optional: with no target the
                        # prompt keeps today's default length rules exactly.
                        # PipelineContext already normalised both fields;
                        # normalising again keeps a hand-built context safe.
                        target_duration = normalize_target_duration(ctx.target_duration)
                        if target_duration is not None:
                            ai_ctx["target_duration"] = target_duration
                        ai_ctx["story_format"] = normalize_story_format(ctx.story_format)
                        ai_resp = AIBridge.generate("script", ai_ctx)
                        ai_lines = ai_resp.get("lines", [])
                        if ai_lines:
                            ai_script = {
                                "hook": ai_resp.get("hook_title") or ai_lines[0].get("text", ctx.product_name),
                                "lines": ai_lines,
                                "full_text": "\n".join([l.get("text", "") for l in ai_lines])
                            }
                            print(f"✨ [Pipeline] Dynamic script ready! ({len(ai_lines)} lines)")
                    except Exception as ai_err:
                        # A quota hit means the user's own daily AI budget
                        # cap stopped this call, not a provider failure.
                        # Script generation still has a safe, non-AI
                        # fallback (ScriptGenerator) so the render is never
                        # blocked -- but the reason must be loud and visible
                        # in the job's own progress log, not just a
                        # server-side print, so the user knows it was their
                        # budget cap and not a broken provider.
                        if is_quota_error(ai_err):
                            ctx.notify(
                                "⚠️ เกินโควต้า AI ต่อวันแล้ว — ใช้สคริปต์สำเร็จรูปแทนสคริปต์ AI",
                                0.12,
                            )
                            print(f"⚠️ [Pipeline] AI script gen skipped: quota exceeded ({ai_err}) — falling back to ScriptGenerator...")
                        else:
                            print(f"⚠️ [Pipeline] AI script gen failed ({ai_err}) — falling back to ScriptGenerator...")

                if ai_script:
                    script_data = ai_script
                else:
                    script_data = ScriptGenerator.generate(
                        product_name=ctx.product_name,
                        key_features=ctx.key_features,
                        pain_point=ctx.pain_point,
                        price_deal=ctx.price_deal
                    )
                    # Template text is clean, but pain_point/key_features come
                    # from product data and could carry a price or claim.
                    script_data, removed = enforce_script_compliance(script_data)
                    if removed:
                        print(
                            "⚠️ [Pipeline] สคริปต์สำเร็จรูปมีจุดผิดกฎ compliance — ตัดบรรทัดที่ผิดออกแล้ว:\n"
                            f"{format_violations_th(removed)}"
                        )
                        kept = script_data.get("lines") or []
                        script_data["full_text"] = "\n".join(l["text"] for l in kept)
                        if kept:
                            script_data["hook"] = kept[0]["text"]
        else:
            if not ctx.manifest:
                raise ValueError("Cannot reuse script without manifest")
            script_data = ctx.manifest["script_data"]
            print(f"♻️  [1/5] Reusing script ({len(script_data.get('lines', []))} lines)")

        ctx.script_data = script_data
