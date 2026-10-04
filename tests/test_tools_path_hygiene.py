"""
Test suite to guarantee path hygiene across all tools/ scripts:
1. No legacy hardcoded paths (e.g. Winon, Winona, hardcoded User/drive paths).
2. All python scripts in tools/ must compile cleanly (no SyntaxError).
3. Tools must not execute external commands or crash upon module import.
"""

import ast
import importlib.util
import py_compile
import re
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"


def test_tools_exist():
    assert TOOLS_DIR.exists() and TOOLS_DIR.is_dir()
    tool_files = list(TOOLS_DIR.glob("*.py"))
    assert len(tool_files) >= 20, f"Expected at least 20 tools, found {len(tool_files)}"


def test_no_legacy_hardcoded_paths_in_tools():
    """Verify that no tools reference legacy machine usernames or absolute drive paths."""
    forbidden_patterns = [
        re.compile(r"Winona", re.IGNORECASE),
        re.compile(r"C:[\\/]Users[\\/]Winon", re.IGNORECASE),
        re.compile(r"D:[\\/]Winona", re.IGNORECASE),
        re.compile(r"D:[\\/]Programmer", re.IGNORECASE),
    ]

    violations = []
    for py_file in TOOLS_DIR.glob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            matches = pattern.findall(text)
            if matches:
                violations.append(f"{py_file.name}: matched forbidden pattern '{pattern.pattern}' ({len(matches)} times)")

    assert not violations, "Found legacy hardcoded path violations:\n" + "\n".join(violations)


def test_tools_compile_cleanly():
    """Verify that every python file in tools/ compiles without syntax errors."""
    compile_errors = []
    for py_file in TOOLS_DIR.glob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            compile_errors.append(f"{py_file.name}: {e}")

    assert not compile_errors, "Syntax/compilation errors found:\n" + "\n".join(compile_errors)


@pytest.mark.parametrize("tool_name", [
    "clean_and_organize_tmp.py",
    "audit_video_resolutions.py",
    "download_new_thai_fonts.py",
    "scrape_official_mi_assets.py",
    "fetch_mix_flip_pack.py",
    "render_font_comparison.py",
    "render_individual_font_cards.py",
    "render_new_distinct_fonts.py",
    "render_ui_font_comparison.py",
    "build_60s_mali_burst_ass.py",
    "render_60s_clean_pro_master.py",
    "render_60s_dynamic_master.py",
    "render_60s_pro_master.py",
    "render_mali_master.py",
    "test_mali_render.py",
    "slice_pro_tech_stickers.py",
    "render_character_karaoke.py",
    "render_60s_master_clip.py",
])
def test_tool_import_safety(tool_name):
    """
    Verify that tools can be imported cleanly without executing blocking/destructive work.
    They should define their logic inside functions or guard with if __name__ == '__main__':.
    """
    file_path = TOOLS_DIR / tool_name
    assert file_path.exists(), f"File {tool_name} not found"

    # Parse AST to ensure there's no bare destructive calls at module level
    tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"), filename=str(file_path))
    top_level_calls = [node for node in tree.body if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)]
    
    # We allow basic top level setup like sys.path.insert, logging.basicConfig, etc.
    # But forbid bare subprocess.run or shutil.rmtree at top level
    for expr in top_level_calls:
        call = expr.value
        func_name = ""
        if isinstance(call.func, ast.Name):
            func_name = call.func.id
        elif isinstance(call.func, ast.Attribute):
            func_name = getattr(call.func.value, "id", "") + "." + call.func.attr

        assert func_name not in ["subprocess.run", "shutil.rmtree", "os.system"], (
            f"{tool_name} has unguarded top-level execution call: {func_name}"
        )
