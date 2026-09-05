"""
Script Stage for OmniCut Pro Studio.
Generates or prepares TikTok script cues using custom script, AIBridge, ScriptGenerator, or manifest reuse.
"""

from scripts.ai_bridge import AIBridge
from scripts.script_generator import ScriptGenerator
from scripts.pipeline_context import PipelineContext


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
            else:
                ai_script = None
                if AIBridge.is_available():
                    try:
                        ctx.notify("🧠 [1/5] ให้ AI Pro วิเคราะห์จุดขายและเขียนบทพากย์พร้อมแปล...", 0.12)
                        print("✨ [1/5] Generating dynamic script via AIBridge...")
                        ai_ctx = {
                            "product_name": ctx.product_name,
                            "angle_title": ctx.angle_meta.get("title", "รีวิวสินค้า") if ctx.angle_meta else "รีวิวสินค้าสุดปัง",
                            "hook": ctx.angle_meta.get("hook", "") if ctx.angle_meta else f"ใครหา {ctx.product_name} อยู่ดูคลิปนี้เลย",
                            "specs": [{"label": "จุดเด่น", "value": ctx.key_features[:60]}],
                            "price_deal": ctx.price_deal
                        }
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
        else:
            if not ctx.manifest:
                raise ValueError("Cannot reuse script without manifest")
            script_data = ctx.manifest["script_data"]
            print(f"♻️  [1/5] Reusing script ({len(script_data.get('lines', []))} lines)")

        ctx.script_data = script_data
