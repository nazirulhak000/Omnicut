"""ส่ง filter graph ที่ยาวเกินให้ ffmpeg ผ่านไฟล์แทนบรรทัดคำสั่ง

Windows CreateProcess รับบรรทัดคำสั่งได้ไม่เกิน 32,767 อักขระ (นับรวมทุก
อาร์กิวเมนต์ที่ `subprocess.list2cmdline` ต่อให้) ถ้าเกิน Python จะโยน
`FileNotFoundError: [WinError 206] The filename or extension is too long`
ก่อนที่ ffmpeg จะได้เริ่มทำงานด้วยซ้ำ graph ของไทม์ไลน์หลายคลิปโตตามจำนวนคลิป
(ราว 360-450 อักขระต่อคลิป) จึงชนเพดานนี้ที่ราว 70 คลิป

โมดูลนี้เปลี่ยนเฉพาะ "วิธีส่ง" graph เท่านั้น เนื้อหา graph ไม่ถูกแตะ และถ้า
คำสั่งสั้นกว่าเกณฑ์ `cmd` จะถูกคืนกลับมาเหมือนเดิมไบต์ต่อไบต์
"""

from __future__ import annotations

import functools
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

# เพดานจริงของ Windows คือ 32,767 อักขระ เกณฑ์ที่ใช้ต่ำกว่าเพดานราว 4,700
# เผื่อไว้สำหรับอาร์กิวเมนต์ที่ผู้เรียกเติมทีหลัง (เช่น `-progress pipe:1 -nostats`)
# และการ quote ที่ list2cmdline เพิ่มให้ path ที่มีช่องว่าง
FILTER_GRAPH_SCRIPT_THRESHOLD = 28_000
WINDOWS_CMDLINE_LIMIT = 32_767

# `-/<option> <file>` อ่านค่า option จากไฟล์ (เริ่มใน ffmpeg 7.0) ส่วน
# `-filter_complex_script` ถูกประกาศ deprecated ตั้งแต่ 7.0 แต่ยังใช้ได้ใน
# ทุกเวอร์ชัน จึงเป็นทางสำรองเมื่อตรวจ ffmpeg ไม่ได้หรือเป็นรุ่นเก่า
_FLAG_SLASH = "-/filter_complex"
_FLAG_SCRIPT = "-filter_complex_script"


def cmdline_length(cmd: Sequence[object]) -> int:
    """ความยาวบรรทัดคำสั่งแบบเดียวกับที่ subprocess ส่งให้ CreateProcess บน Windows"""
    return len(subprocess.list2cmdline([str(part) for part in cmd]))


@functools.lru_cache(maxsize=None)
def supports_slash_option(ffmpeg_bin: str = "ffmpeg") -> bool:
    """True เมื่อ ffmpeg ที่ติดตั้งรู้จัก `-/filter_complex <file>` (ffmpeg >= 7)

    ตรวจด้วยการสั่ง `-/filter_complex` ชี้ไฟล์ที่ไม่มีอยู่จริง: รุ่นที่รองรับจะ
    ฟ้องว่าอ่านไฟล์ไม่ได้ ส่วนรุ่นเก่าจะฟ้อง "Unrecognized option" วิธีนี้ใช้ได้กับ
    build จาก git (เลขรุ่น `N-xxxxx`) ที่เทียบเวอร์ชันตรง ๆ ไม่ได้ ผลถูกแคชไว้
    ครั้งเดียวต่อ process และถ้าตรวจพลาดด้วยเหตุใดก็ตามให้ถอยไป
    `-filter_complex_script` เสมอ ห้ามทำให้การเรนเดอร์ล้ม
    """
    try:
        probe = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-/filter_complex",
             "omnicut_filter_graph_probe_missing.txt", "-f", "null", "-"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=15,
            stdin=subprocess.DEVNULL,
        )
        output = f"{probe.stdout or ''}\n{probe.stderr or ''}".lower()
        return probe.returncode != 0 and "unrecognized option" not in output
    except Exception as exc:  # noqa: BLE001 - ตรวจไม่ได้ = ใช้ทางสำรอง ไม่ล้ม
        print(f"Notice: ตรวจความสามารถ -/filter_complex ของ ffmpeg ไม่ได้ ({exc}) "
              f"ใช้ -filter_complex_script แทน")
        return False


def filter_graph_file_flag(ffmpeg_bin: str = "ffmpeg") -> str:
    """ชื่อ option ที่ใช้ส่ง graph ผ่านไฟล์กับ ffmpeg ตัวที่ติดตั้งอยู่"""
    return _FLAG_SLASH if supports_slash_option(ffmpeg_bin) else _FLAG_SCRIPT


def cleanup_graph_file(path: Optional[Path]) -> None:
    """ลบไฟล์ graph ชั่วคราว (ไม่มีอยู่แล้วก็ไม่เป็นไร) ห้ามโยน exception ออกไป"""
    if path is None:
        return
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        print(f"Notice: ลบไฟล์ filter graph ชั่วคราวไม่สำเร็จ {path}: {exc}")


def externalize_filter_graph(
    cmd: List[str],
    graph: str,
    *,
    threshold: Optional[int] = None,
    temp_dir: Optional[Path] = None,
    ffmpeg_bin: str = "ffmpeg",
) -> Tuple[List[str], Optional[Path]]:
    """ย้าย `-filter_complex <graph>` ไปไฟล์เมื่อคำสั่งยาวเกินเกณฑ์

    คืน `(cmd, graph_file)`:
    - สั้นกว่าหรือเท่าเกณฑ์: คืน `cmd` ตัวเดิมที่ไม่ถูกแตะและ `None`
    - ยาวเกินเกณฑ์: คืน cmd ใหม่ที่ `-filter_complex <graph>` ถูกแทนด้วย
      `-/filter_complex <ไฟล์>` (หรือ `-filter_complex_script <ไฟล์>`) และ path ของ
      ไฟล์ UTF-8 (ไม่มี BOM) ที่ผู้เรียก "ต้อง" ลบด้วย `cleanup_graph_file`
      ใน finally เสมอ (ลบแม้ ffmpeg ล้มเหลว)

    ถ้าไม่เจอคู่ `-filter_complex <graph>` ใน cmd จะคืนของเดิมโดยไม่ทำอะไร
    """
    limit = FILTER_GRAPH_SCRIPT_THRESHOLD if threshold is None else threshold
    length = cmdline_length(cmd)
    if length <= limit:
        return cmd, None

    position = None
    for i in range(len(cmd) - 1):
        if cmd[i] == "-filter_complex" and cmd[i + 1] == graph:
            position = i
            break
    if position is None:
        return cmd, None

    fd, raw_path = tempfile.mkstemp(
        prefix="omnicut_filtergraph_",
        suffix=".txt",
        dir=str(temp_dir) if temp_dir is not None else None,
    )
    graph_file = Path(raw_path)
    try:
        # เขียนเป็นไบต์ตรง ๆ: UTF-8 ไม่มี BOM และไม่ให้ Windows แปลง \n เป็น \r\n
        with os.fdopen(fd, "wb") as handle:
            handle.write(graph.encode("utf-8"))
    except BaseException:
        cleanup_graph_file(graph_file)
        raise

    flag = filter_graph_file_flag(ffmpeg_bin)
    new_cmd = list(cmd)
    new_cmd[position] = flag
    new_cmd[position + 1] = str(graph_file)
    new_length = cmdline_length(new_cmd)
    print(
        f"Notice: คำสั่ง ffmpeg ยาว {length:,} อักขระ (เกณฑ์ {limit:,}) "
        f"ย้าย filter graph {len(graph):,} อักขระไปไฟล์ {graph_file.name} "
        f"ด้วย {flag} คำสั่งเหลือ {new_length:,} อักขระ"
    )
    if new_length > WINDOWS_CMDLINE_LIMIT:
        print(
            f"Warning: คำสั่ง ffmpeg ยังยาว {new_length:,} อักขระ เกินเพดาน Windows "
            f"{WINDOWS_CMDLINE_LIMIT:,} แม้ย้าย graph ไปไฟล์แล้ว (จำนวน -i มากเกินไป)"
        )
    return new_cmd, graph_file


@contextmanager
def filter_graph_via_file(
    cmd: List[str],
    graph: str,
    **kwargs,
) -> Iterator[List[str]]:
    """context manager ครอบ `externalize_filter_graph` ลบไฟล์ให้เสมอ

    ```
    with filter_graph_via_file(cmd, graph) as run_cmd:
        subprocess.run(run_cmd, ...)
    ```
    """
    new_cmd, graph_file = externalize_filter_graph(cmd, graph, **kwargs)
    try:
        yield new_cmd
    finally:
        cleanup_graph_file(graph_file)
