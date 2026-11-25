"""
Cleanup TikTok Studio scheduled posts:
Keeps only the 10 canonical Day 1 (Nov 23) clips.
Deletes any duplicate / stacked clips belonging to Day 2 or Day 3.
"""
import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / ".tmp"))

from browser_client import BrowserClient

TAB_ID = 1319918330

DAY1_KEEP_PREFIXES = [
    "พัดลมตั้งโต๊ะ Hatari Cyclone Max 8 นิ้ว",
    "จะออกจากบ้านไปเที่ยว แบตเหลือ 5%",
    "ใส่หูฟังจุกยางเจ็บรูหูจนจะระเบิด",
    "หมดปัญหาชาร์จไปเล่นเกมไปแล้วค้ำมือ",
    "บอกลาสายชาร์จพันกันในกระเป๋า",
    "เจาะลึกฟิล์มกระจก ESSAGER",
    "แกะกล่อง TRANYOO T-S20",
    "ปลอกนิ้วเล่นเกมสเปกเทพ TRANYOO GS-01",
    "หมดปัญหาพิมพ์งานตอนมืด! เปลี่ยนชีวิตด้วย",
    "รีวิวสเปกเจาะลึก! เมาส์ไร้สาย Memzuoix",
]

class TikTokCleaner:
    def __init__(self, tab_id=TAB_ID):
        self.tab_id = tab_id
        self.client = None

    async def connect(self):
        self.client = BrowserClient()
        await self.client.connect()
        # Find active tiktok studio tab
        tab_res = await self.client.command("tab list")
        text = tab_res.get("result", {}).get("content", [{}])[0].get("text", "")
        for line in text.splitlines():
            if "TikTok Studio" in line and "content" in line:
                parts = line.strip().split()
                if parts[0] == "*":
                    self.tab_id = int(parts[1])
                elif parts[0].isdigit():
                    self.tab_id = int(parts[0])
        print(f"Connected to BrowserClient on tab {self.tab_id}")

    async def eval_js(self, js):
        clean_js = " ".join([l.strip() for l in js.splitlines()])
        cmd = f'tab select {self.tab_id}\neval {json.dumps(clean_js)}'
        res = await self.client.command(cmd)
        text = res.get("result", {}).get("content", [{}])[0].get("text", "")
        lines = text.splitlines()
        eval_idx = -1
        page_idx = len(lines)
        for i, l in enumerate(lines):
            if l.startswith("✓ eval "):
                eval_idx = i
            elif eval_idx != -1 and l.startswith("Page: http"):
                page_idx = i
                break
        if eval_idx != -1:
            raw = "\n".join(lines[eval_idx + 1:page_idx]).strip()
            try:
                val = json.loads(raw)
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except Exception:
                        return val
                return val
            except Exception:
                return raw
        return None

    async def run(self):
        await self.connect()
        deleted_count = 0
        empty_retries = 0
        consecutive_errors = 0

        while True:
            # Evaluate current rows
            rows_data = await self.eval_js('''(() => {
                const rows = Array.from(document.querySelectorAll('a[href*="/video/"]'));
                return JSON.stringify(rows.map((a, idx) => {
                    const text = a.textContent.trim();
                    return { idx, text };
                }));
            })()''')

            if not rows_data or not isinstance(rows_data, list) or len(rows_data) == 0:
                empty_retries += 1
                if empty_retries <= 4:
                    print(f"Rows empty or table reloading (retry {empty_retries}/4), waiting 2.5s...")
                    await asyncio.sleep(2.5)
                    continue
                else:
                    print(f"No more rows found after retries. Eval was: {rows_data}")
                    break

            empty_retries = 0

            # Find first row that is NOT in DAY1_KEEP_PREFIXES
            target_to_delete = None
            for r in rows_data:
                text = r["text"]
                is_keep = any(text.startswith(prefix) for prefix in DAY1_KEEP_PREFIXES)
                if not is_keep:
                    target_to_delete = r
                    break

            if not target_to_delete:
                print(f"All remaining rows are canonical Day 1 clips! (Total kept: {len(rows_data)})")
                break

            idx = target_to_delete["idx"]
            title_snippet = target_to_delete["text"][:40]
            print(f"Deleting duplicate/stack row [{idx}]: {title_snippet}...")

            # 1. Click 3-dots button for that row
            click_res = await self.eval_js(f'''(() => {{
                const rows = Array.from(document.querySelectorAll('a[href*="/video/"]'));
                const a = rows[{idx}];
                if (!a) return false;
                a.scrollIntoView({{ block: 'center' }});
                let row = a;
                while (row && !row.querySelector('button[data-tt="components_ActionCell_Clickable"]')) {{
                    row = row.parentElement;
                }}
                if (!row) return false;
                const dotsBtn = row.querySelector('button[data-tt="components_ActionCell_Clickable"]');
                if (dotsBtn) {{
                    dotsBtn.click();
                    return true;
                }}
                return false;
            }})()''')

            if not click_res:
                print(f"Failed to click 3-dots on row {idx}, retrying...")
                consecutive_errors += 1
                if consecutive_errors >= 4:
                    break
                await asyncio.sleep(1.5)
                continue

            await asyncio.sleep(0.5)

            # 2. Click "Delete" menu item with retry
            delete_menu_res = False
            for _ in range(6):
                delete_menu_res = await self.eval_js('''(() => {
                    const items = Array.from(document.querySelectorAll('[data-tt="components_ActionCell_FlexRow"], [data-tt*="ActionCell"], span, div')).filter(el => {
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && el.textContent.trim() === 'Delete';
                    });
                    if (items.length > 0) {
                        items[items.length - 1].click();
                        return true;
                    }
                    return false;
                })()''')
                if delete_menu_res:
                    break
                await asyncio.sleep(0.4)

            if not delete_menu_res:
                print("Failed to click 'Delete' in dropdown menu, retrying...")
                await self.client.command("press Escape")
                consecutive_errors += 1
                if consecutive_errors >= 4:
                    break
                await asyncio.sleep(1.5)
                continue

            await asyncio.sleep(0.5)

            # 3. Confirm Delete in modal with retry
            confirm_res = False
            for _ in range(6):
                confirm_res = await self.eval_js('''(() => {
                    const btns = Array.from(document.querySelectorAll('button')).filter(b => {
                        const r = b.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && b.textContent.trim() === 'Delete' && (b.className.includes('css-y1m958') || b.parentElement.textContent.includes('Cancel'));
                    });
                    if (btns.length > 0) {
                        btns[0].click();
                        return true;
                    }
                    return false;
                })()''')
                if confirm_res:
                    break
                await asyncio.sleep(0.4)

            if not confirm_res:
                print("Failed to click 'Delete' in confirm modal, retrying...")
                await self.client.command("press Escape")
                consecutive_errors += 1
                if consecutive_errors >= 4:
                    break
                await asyncio.sleep(1.5)
                continue

            consecutive_errors = 0
            deleted_count += 1
            print(f"  -> Successfully deleted ({deleted_count} total deleted)")
            await asyncio.sleep(2.5)

        print(f"Finished cleanup! Total deleted: {deleted_count}")

if __name__ == "__main__":
    cleaner = TikTokCleaner()
    asyncio.run(cleaner.run())
