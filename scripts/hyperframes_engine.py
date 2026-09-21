"""HyperFrames Engine wrapper for OmniCut Pro Studio.

Renders high-fidelity HTML/CSS/JS animations into deterministic MP4 videos or
transparent WebM (VP9 + Alpha) overlays using HeyGen's HyperFrames CLI.
"""

import os
import sys
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class HyperFramesEngine:
    """Wrapper for invoking HyperFrames CLI and compiling HTML motion graphics."""

    @classmethod
    def is_available(cls) -> bool:
        """Check if node and npx are available on the system."""
        try:
            res = subprocess.run(
                ["node", "-v"],
                capture_output=True,
                text=True,
                shell=True,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def render_composition(
        cls,
        project_dir: Path,
        output_path: Path,
        format_type: str = "webm",
        resolution: str = "portrait",
        low_memory_mode: bool = True,
        timeout_seconds: int = 180
    ) -> bool:
        """
        Render an initialized HyperFrames composition folder to MP4 or WebM.
        
        Args:
            project_dir: Path to directory containing index.html and hyperframes.json
            output_path: Target path for output video
            format_type: "webm" for transparent alpha, or "mp4" for standard video
            resolution: "portrait" (1080x1920) or "landscape" (1920x1080)
            low_memory_mode: True to restrict to single worker and screenshot capture (recommended on <=16GB RAM)
            timeout_seconds: Max execution timeout
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "npx", "hyperframes", "render",
            "--format", format_type,
            "-o", str(output_path),
            f"--resolution={resolution}",
        ]
        if low_memory_mode:
            cmd.append("--low-memory-mode")

        print(f"🎬 [HyperFrames] Rendering composition from {project_dir.name} -> {output_path.name}...")
        res = subprocess.run(
            cmd,
            cwd=str(project_dir),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_seconds
        )

        if res.returncode != 0:
            print(f"❌ [HyperFrames] Render failed (code {res.returncode}):\n{res.stderr[-600:]}")
            return False

        if not output_path.exists() or output_path.stat().st_size == 0:
            print(f"❌ [HyperFrames] Output file not found or empty: {output_path}")
            return False

        print(f"✅ [HyperFrames] Successfully rendered {output_path.name} ({output_path.stat().st_size} bytes)")
        return True

    @classmethod
    def render_tech_spec_card(
        cls,
        product_name: str,
        specs: Dict[str, str],
        output_webm_path: Path,
        duration: float = 5.0,
        temp_dir: Optional[Path] = None
    ) -> bool:
        """
        Generate and render a transparent 9:16 Glassmorphism Tech Spec Card overlay.
        
        Args:
            product_name: Name of the gadget (e.g. "Xiaomi MIX Flip")
            specs: Dict of key specs, e.g.:
                   {"processor": "Snapdragon 8 Gen 3", "camera": "50MP Leica Dual", "display": "4.01\" 1.5K AMOLED", "battery": "4,780 mAh / 67W"}
            output_webm_path: Path to write the transparent WebM file
            duration: Total duration of the animation in seconds
            temp_dir: Optional working directory
        """
        work_dir = temp_dir or (PROJECT_ROOT / ".tmp" / "hyperframes_work")
        work_dir.mkdir(parents=True, exist_ok=True)

        # Build clean HyperFrames project scaffolding
        hf_config = {
            "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
            "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
            "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}
        }
        (work_dir / "hyperframes.json").write_text(json.dumps(hf_config, indent=2), encoding="utf-8")

        # HTML template with Glassmorphism, Google Font Prompt, and GSAP Timeline
        html_content = cls._generate_spec_card_html(
            product_name=product_name,
            specs=specs,
            duration=duration
        )
        (work_dir / "index.html").write_text(html_content, encoding="utf-8")

        return cls.render_composition(
            project_dir=work_dir,
            output_path=output_webm_path,
            format_type="webm",
            resolution="portrait",
            low_memory_mode=True
        )

    @classmethod
    def _generate_spec_card_html(
        cls,
        product_name: str,
        specs: Dict[str, str],
        duration: float
    ) -> str:
        """Generate HTML string for the Glassmorphism Tech Spec Card."""
        spec_items = []
        icons = {
            "processor": "⚡",
            "chipset": "⚡",
            "camera": "📸",
            "display": "📱",
            "screen": "📱",
            "battery": "🔋",
            "charging": "⚡",
            "feature": "✨"
        }

        for key, val in specs.items():
            icon = icons.get(key.lower(), "🔹")
            label = key.replace("_", " ").title()
            spec_items.append(f"""
            <div class="spec-pill">
              <div class="spec-icon">{icon}</div>
              <div class="spec-text">
                <span class="spec-label">{label}</span>
                <span class="spec-value">{val}</span>
              </div>
            </div>
            """)

        spec_html = "\n".join(spec_items)

        return f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }}
      html, body {{
        margin: 0;
        width: 1080px;
        height: 1920px;
        overflow: hidden;
        background: transparent;
        font-family: 'Prompt', -apple-system, sans-serif;
      }}
      #root {{
        width: 100%;
        height: 100%;
        position: relative;
        background: transparent;
      }}
      
      /* Card positioned in lower third, above TikTok captions safe zone (bottom 480px) */
      .card-container {{
        position: absolute;
        bottom: 520px;
        left: 54px;
        width: 972px;
        background: rgba(14, 18, 27, 0.88);
        backdrop-filter: blur(28px);
        -webkit-backdrop-filter: blur(28px);
        border: 1.5px solid rgba(255, 255, 255, 0.18);
        border-radius: 36px;
        padding: 40px 48px;
        box-shadow: 0 30px 80px rgba(0, 0, 0, 0.75), inset 0 1px 1px rgba(255, 255, 255, 0.25);
        color: #ffffff;
        transform: translateY(120px);
        opacity: 0;
      }}

      .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 28px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        padding-bottom: 18px;
      }}

      .product-title {{
        font-size: 40px;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #FFFFFF 0%, #E2E8F0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }}

      .badge-tag {{
        background: rgba(255, 230, 0, 0.15);
        border: 1px solid #FFE600;
        color: #FFE600;
        padding: 6px 18px;
        border-radius: 999px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }}

      .specs-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
      }}

      .spec-pill {{
        display: flex;
        align-items: center;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 18px 22px;
        gap: 16px;
        opacity: 0;
        transform: scale(0.92);
      }}

      .spec-icon {{
        font-size: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
      }}

      .spec-text {{
        display: flex;
        flex-direction: column;
      }}

      .spec-label {{
        font-size: 19px;
        color: #94A3B8;
        font-weight: 600;
      }}

      .spec-value {{
        font-size: 26px;
        color: #F8FAFC;
        font-weight: 700;
      }}
    </style>
  </head>
  <body>
    <div
      id="root"
      data-composition-id="main"
      data-start="0"
      data-duration="{duration}"
      data-width="1080"
      data-height="1920"
    >
      <div class="card-container" id="specCard">
        <div class="card-header">
          <div class="product-title">{product_name}</div>
          <div class="badge-tag">OFFICIAL SPECS</div>
        </div>
        <div class="specs-grid">
          {spec_html}
        </div>
      </div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      
      // 1. Slide in card smoothly
      tl.to("#specCard", {{
        y: 0,
        opacity: 1,
        duration: 0.8,
        ease: "power3.out"
      }}, 0.2);

      // 2. Stagger in spec pills
      tl.to(".spec-pill", {{
        opacity: 1,
        scale: 1,
        duration: 0.5,
        stagger: 0.12,
        ease: "back.out(1.4)"
      }}, 0.5);

      // 3. Smooth exit fade
      const exitTime = Math.max(1.0, {duration} - 0.7);
      tl.to("#specCard", {{
        y: 60,
        opacity: 0,
        duration: 0.6,
        ease: "power2.in"
      }}, exitTime);

      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""
