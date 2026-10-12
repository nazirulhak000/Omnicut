"""Rebuild all 6 POV Couple Sitcom clips (goc01-pov-32s + goc01-pov1..5) with:
1. Separate Single-Speaker TTS calls for Female (น้องนุ้ย = Aoede) and Male (พี่บ่าว = Puck)
   -> Guarantees 100% consistent voice for Female and Male throughout the entire clip (never swaps!).
2. Southern Thai couple pairing: Male = "พี่บ่าว" (avatar "บ"), Female = "น้องนุ้ย" (avatar "น").
3. Stacked LINE Chat Bubbles: Each short sub-clause (<span class="w">) is its own separate LINE chat bubble stacked vertically (no horizontal overflow!).
4. Top Hook & Scene Titles sized at 64px (<= 920px width) so they NEVER overflow the 1080px screen edges.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STUDIO = HERE.parent
OMNICUT_ROOT = STUDIO.parent.parent
sys.path.insert(0, str(OMNICUT_ROOT))
sys.path.insert(0, str(STUDIO / "kit"))

from scripts.config import get_gemini_api_keys  # noqa: E402
from hf_timing import build  # noqa: E402


CLIPS_SPEC = [
    {
        "id": "goc01-pov-32s",
        "media_starts": [26.0, 31.0, 39.0, 76.0, 4.2, 108.0],
        "headlines": [
            ("POV: แอบบ่นเมียหลังบ้าน", "แต่ลืมปิด<br>ไมค์ไร้สาย!"),
            ("หลักฐานมัดตัวจากไมค์", "เสียงหลุดชัด<br>ระดับล้านเค!"),
            ("เปิดพัดลมเบอร์ 3 จ่อคอ", "ก็ตัดเสียงลม<br>ออกเกลี้ยง!"),
            ("ตัวต้นเหตุความชัด", "GoChek Ultra S24<br>ตัดเสียง 90%"),
            ("เคสชาร์จเท่ • แบต 35 ชม.", "ยึดไมค์!!<br>ได้แรงอก!"),
            ("บทสรุปพ่อบ้านใจกล้า", "โดนติดไมค์<br>คุมประพฤติ!"),
        ],
        "turns": [
            ("F", "พี่บ่าว! เมื่อกี้เดินไปหลังบ้าน แหลงไหรไว้!", [
                ("พี่บ่าว!", "พี่บ่าว", "c0_1"),
                ("เดินไปหลังบ้าน", "เดินไปหลังบ้าน", "c0_2"),
                ("แหลงไหรไว้!", "แหลงไหรไว้", "c0_3"),
            ]),
            ("M", "ฮะ เปล่าครับน้องนุ้ย เค้าไปเปิดพัดลมเฉยๆ", [
                ("ฮะ เปล่าครับน้องนุ้ย", "ฮะ เปล่าครับน้องนุ้ย", "c1_1"),
                ("ไปเปิดพัดลมเฉยๆ", "ไปเปิดพัดลมเฉยๆ", "c1_2"),
            ]),
            ("F", "ไม่ได้แหลงบ้านมึงสิ! ฟังนะ ชัดระดับล้านเค!", [
                ("ไม่ได้แหลงบ้านมึงสิ!", "ไม่ได้แหลงบ้านมึงสิ", "c2_1"),
                ("ฟังนะ ชัดระดับล้านเค!", "ฟังนะ ชัดระดับล้านเค", "c2_2"),
            ]),
            ("M", "น้องนุ้ยดุยังกะพิตบูล ด่าทีบ้านสะเทือน", [
                ("น้องนุ้ยดุยังกะพิตบูล", "น้องนุ้ยดุยังกะพิตบูล", "c3_1"),
                ("ด่าทีบ้านสะเทือน", "ด่าทีบ้านสะเทือน", "c3_2"),
            ]),
            ("F", "เปิดพัดลมเบอร์สาม แต่เสียงลมไม่เข้าสักแอะ!", [
                ("เปิดพัดลมเบอร์ 3", "เปิดพัดลมเบอร์ 3", "c4_1"),
                ("เสียงลมไม่เข้าสักแอะ!", "เสียงลมไม่เข้าสักแอะ", "c4_2"),
            ]),
            ("F", "เสียงนินทากูชัดยังกะมานอนแหลงในรูหู!", [
                ("เสียงนินทากูชัด", "เสียงนินทากูชัด", "c5_1"),
                ("ยังกะมานอนแหลงในรูหู!", "ยังกะมานอนแหลงในรูหู", "c5_2"),
            ]),
            ("M", "ใครจะคิดว่าไมค์ GoChek S24 ตัดเสียงลม 90% ล่ะ!", [
                ("ใครจะคิดว่า", "ใครจะคิดว่า", "c6_1"),
                ("GoChek S24", "GoChek S24", "c6_2"),
                ("ตัดเสียงลม 90%!", "ตัดเสียงลม 90%", "c6_3"),
            ]),
            ("F", "เคสชาร์จโคตรเท่ แบตอึดสามสิบห้าชั่วโมง ยึด!", [
                ("เคสเท่ แบต 35 ชม.", "เคสเท่ แบต 35 ชม.", "c7_1"),
                ("ยึด!! ได้แรงอก!", "ยึด ได้แรงอก", "c7_2"),
            ]),
            ("F", "ทีหลังไปเดินห้าง กูจะติดเสื้อมึงไว้ตลอด!", [
                ("ทีหลังไปเดินห้าง", "ทีหลังไปเดินห้าง", "c8_1"),
                ("กูจะติดเสื้อมึงไว้ตลอด!", "กูจะติดเสื้อมึงไว้ตลอด", "c8_2"),
            ]),
            ("M", "จบกันชีวิตผม พิกัดไมค์กดตะกร้าเหลืองซ้ายล่างครับ", [
                ("จบกันชีวิตผม...", "จบกันชีวิตผม", "c9_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c9_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างครับ", "ซ้ายล่างครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov1-anc",
        "media_starts": [12.0, 26.0, 44.0, 76.0, 92.0, 108.0],
        "headlines": [
            ("POV: โทรคุยกับเมียริมถนน", "แต่ไมค์ตัดเสียง<br>ดีเกินไป!"),
            ("ตลาดนัดหรือห้องแอร์?!", "เงียบกริบจน<br>เมียระแวง!"),
            ("ไม่ได้หนีเที่ยวครับ!", "เปิดโหมดตัดเสียง<br>ไว้เฉยๆ!"),
            ("ตัวต้นเหตุความเงียบ", "GoChek Ultra S24<br>ตัดเสียง 90%"),
            ("ตัดเสียงรถริมถนนเกลี้ยง!", "กดปุ่มเดียว<br>เงียบสนิท"),
            ("บทสรุปพ่อบ้านซื่อบื้อ", "ต้องเปิดเสียงแม่ค้า<br>เป็นพยาน!"),
        ],
        "turns": [
            ("F", "พี่บ่าว! ตอนนี้อยู่ไหน แหลงกับน้องนุ้ยมาเดี๋ยวนี้!", [
                ("พี่บ่าว! ตอนนี้อยู่ไหน", "พี่บ่าว ตอนนี้อยู่ไหน", "c0_1"),
                ("แหลงกับน้องนุ้ยมาเดี๋ยวนี้!", "แหลงกับน้องนุ้ยมาเดี๋ยวนี้", "c0_2"),
            ]),
            ("M", "เดินซื้อแกงอยู่ตลาดนัดริมถนนครับน้องนุ้ย", [
                ("เดินซื้อแกง", "เดินซื้อแกง", "c1_1"),
                ("อยู่ตลาดนัดริมถนนครับน้องนุ้ย", "อยู่ตลาดนัดริมถนนครับน้องนุ้ย", "c1_2"),
            ]),
            ("F", "ขี้หกทั้งเพ! ตลาดนัดไหรเงียบยังกะห้องแอร์!", [
                ("ขี้หกทั้งเพ!", "ขี้หกทั้งเพ", "c2_1"),
                ("ตลาดไหรเงียบยังกะห้องแอร์!", "ตลาดไหรเงียบยังกะห้องแอร์", "c2_2"),
            ]),
            ("F", "แอบหนีน้องนุ้ยไปเที่ยวไหน บอกมาเดี๋ยวนี้เลยนะ!", [
                ("แอบหนีน้องนุ้ยไปเที่ยวไหน", "แอบหนีน้องนุ้ยไปเที่ยวไหน", "c3_1"),
                ("บอกมาเดี๋ยวนี้เลยนะ!", "บอกมาเดี๋ยวนี้เลยนะ", "c3_2"),
            ]),
            ("M", "เค้าอยู่ตลาดจริง แต่เสียบไมค์ GoChek S24 ไว้!", [
                ("อยู่ตลาดจริง!", "อยู่ตลาดจริง", "c4_1"),
                ("แต่เสียบไมค์ GoChek S24 ไว้", "แต่เสียบไมค์ GoChek S24 ไว้", "c4_2"),
            ]),
            ("M", "ชิปอัจฉริยะมันตัดเสียงรถออกเกลี้ยงเก้าสิบเปอร์เซ็นต์!", [
                ("ชิปอัจฉริยะ", "ชิปอัจฉริยะ", "c5_1"),
                ("ตัดเสียงรถเกลี้ยง 90%!", "ตัดเสียงรถเกลี้ยง 90%", "c5_2"),
            ]),
            ("F", "ตัดเสียงเนียนเกิน! กดปิดโหมดตัดเสียงเดี๋ยวนี้!", [
                ("ตัดเสียงเนียนเกิน!", "ตัดเสียงเนียนเกิน", "c6_1"),
                ("กดปิดโหมดตัดเสียงเดี๋ยวนี้!", "กดปิดโหมดตัดเสียงเดี๋ยวนี้", "c6_2"),
            ]),
            ("M", "เกือบบ้านแตกเพราะไมค์เทพ กดตะกร้าเหลืองซ้ายล่างครับ", [
                ("เกือบบ้านแตกเพราะไมค์เทพ!", "เกือบบ้านแตกเพราะไมค์เทพ", "c7_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c7_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างครับ", "ซ้ายล่างครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov2-wall",
        "media_starts": [20.0, 35.0, 52.0, 76.0, 4.2, 108.0],
        "headlines": [
            ("POV: แอบซ่อนพัสดุหลังบ้าน", "ห่างไป 2 ห้อง<br>มีกำแพงกั้น!"),
            ("คิดว่าเมียไม่ได้ยิน...", "แต่ลืมถอดไมค์<br>ที่คอเสื้อ!"),
            ("ใบเสร็จสามพันห้า!", "ชัดทะลุกำแพงปูน<br>ถึง 2 ชั้น!"),
            ("รับสัญญาณไกล 50 เมตร", "GoChek Ultra S24<br>ทะลุกำแพง!"),
            ("ดูดเสียงกระซิบชัดแจ๋ว", "หนีไปมุมไหน<br>ก็ไม่รอด!"),
            ("บทสรุปพ่อบ้านซ่อนงบ", "โดนยึดทั้งของเล่น<br>ยึดทั้งไมค์!"),
        ],
        "turns": [
            ("M", "แอบแกะของเล่นดีกว่า บอกน้องนุ้ยว่าอันละสองร้อยพอ", [
                ("แอบแกะของเล่นดีกว่า", "แอบแกะของเล่นดีกว่า", "c0_1"),
                ("บอกน้องนุ้ยว่าอันละ 200 พอ", "บอกน้องนุ้ยว่าอันละ 200 พอ", "c0_2"),
            ]),
            ("F", "สองร้อยบ้านไหนพี่บ่าว! ใบเสร็จเขียนอยู่สามพันห้า!", [
                ("สองร้อยบ้านไหนพี่บ่าว!", "สองร้อยบ้านไหนพี่บ่าว", "c1_1"),
                ("ใบเสร็จเขียนอยู่ 3,500!", "ใบเสร็จเขียนอยู่ 3,500", "c1_2"),
            ]),
            ("M", "ฮะ! น้องนุ้ยอยู่หน้าบ้าน ได้ยินทะลุกำแพงได้ไงเนี่ย!", [
                ("ฮะ! น้องนุ้ยอยู่หน้าบ้าน", "ฮะ น้องนุ้ยอยู่หน้าบ้าน", "c2_1"),
                ("ได้ยินทะลุกำแพงได้ไงเนี่ย!", "ได้ยินทะลุกำแพงได้ไงเนี่ย", "c2_2"),
            ]),
            ("F", "ก็พี่บ่าวหนีบไมค์ไว้! เสียงกระซิบชัดทะลุกำแพงเลยนิ!", [
                ("ก็พี่บ่าวหนีบไมค์ไว้!", "ก็พี่บ่าวหนีบไมค์ไว้", "c3_1"),
                ("เสียงชัดทะลุกำแพงเลยนิ!", "เสียงชัดทะลุกำแพงเลยนิ", "c3_2"),
            ]),
            ("M", "ลืมไปว่าไมค์ GoChek S24 ส่งสัญญาณไกลห้าสิบเมตร!", [
                ("ลืมไปว่า GoChek S24", "ลืมไปว่า GoChek S24", "c4_1"),
                ("ส่งสัญญาณไกลตั้ง 50 เมตร!", "ส่งสัญญาณไกลตั้ง 50 เมตร", "c4_2"),
            ]),
            ("M", "เดินทะลุกำแพงไปหลังบ้าน สัญญาณยังไม่หลุดสักแอะ!", [
                ("เดินทะลุกำแพงไปหลังบ้าน", "เดินทะลุกำแพงไปหลังบ้าน", "c5_1"),
                ("สัญญาณยังไม่หลุดสักแอะ!", "สัญญาณยังไม่หลุดสักแอะ", "c5_2"),
            ]),
            ("F", "ดีมาก! วันนี้น้องนุ้ยยึดทั้งของเล่น ยึดทั้งไมค์!", [
                ("ดีมาก! วันนี้น้องนุ้ย", "ดีมาก วันนี้น้องนุ้ย", "c6_1"),
                ("ยึดทั้งของเล่น ยึดทั้งไมค์!", "ยึดทั้งของเล่น ยึดทั้งไมค์", "c6_2"),
            ]),
            ("M", "พ่อบ้านเช็กไมค์ก่อนซ่อนงบนะครับ พิกัดตะกร้าเหลืองซ้ายล่างครับ", [
                ("เช็กไมค์ก่อนซ่อนงบนะครับ!", "เช็กไมค์ก่อนซ่อนงบนะครับ", "c7_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c7_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างครับ", "ซ้ายล่างครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov3-bat",
        "media_starts": [4.2, 16.0, 31.0, 62.0, 88.0, 108.0],
        "headlines": [
            ("POV: ช่วยเมียอัดคลิปตั้งแต่เช้า", "รอเมื่อไหร่ไมค์<br>จะแบตหมด!"),
            ("ผ่านไป 8 ชั่วโมงเต็ม...", "ทำไมเมียยังมี<br>แรงบ่นต่อ?!"),
            ("แลเคสชาร์จซะก่อน!", "แบตยังเหลือ<br>เต็มเปี่ยม!"),
            ("เคสชาร์จอัจฉริยะ 35 ชม.", "GoChek Ultra S24<br>แบตโคตรอึด!"),
            ("ชาร์จเก็บในเคสได้ตลอดวัน", "ไลฟ์สดยาวๆ<br>ไม่มีสะดุด"),
            ("บทสรุปพ่อบ้านสายอดทน", "แบตไมค์อึดพอๆ<br>กับแรงเมีย!"),
        ],
        "turns": [
            ("M", "ช่วยน้องนุ้ยอัดคลิปตั้งแต่เช้า เมื่อไหร่ไมค์จะแบตหมดสักที", [
                ("ช่วยน้องนุ้ยอัดคลิปตั้งแต่เช้า", "ช่วยน้องนุ้ยอัดคลิปตั้งแต่เช้า", "c0_1"),
                ("เมื่อไหร่ไมค์จะแบตหมดสักที!", "เมื่อไหร่ไมค์จะแบตหมดสักที", "c0_2"),
            ]),
            ("F", "แอบบ่นไหรอีกพี่บ่าว! ฝันไปเถอะว่าแบตจะหมดง่ายๆ!", [
                ("แอบบ่นไหรอีกพี่บ่าว!", "แอบบ่นไหรอีกพี่บ่าว", "c1_1"),
                ("ฝันไปเถอะว่าแบตจะหมด!", "ฝันไปเถอะว่าแบตจะหมด", "c1_2"),
            ]),
            ("F", "แลเคสชาร์จซะก่อน เก็บเข้าเคสทีเดียว ชาร์จเต็มไวทันใจ!", [
                ("แลเคสชาร์จซะก่อน!", "แลเคสชาร์จซะก่อน", "c2_1"),
                ("เก็บเข้าเคส ชาร์จเต็มไว!", "เก็บเข้าเคส ชาร์จเต็มไว", "c2_2"),
            ]),
            ("M", "โห อัดคลิปมาทั้งวัน แบตในเคสยังไม่ยุบเลยเหรอน้องนุ้ย!", [
                ("โห อัดคลิปมาทั้งวัน", "โห อัดคลิปมาทั้งวัน", "c3_1"),
                ("แบตยังไม่ยุบเลยเหรอน้องนุ้ย!", "แบตยังไม่ยุบเลยเหรอน้องนุ้ย", "c3_2"),
            ]),
            ("F", "รุ่นนี้ GoChek S24 แบตอึดรวมเคสตั้งสามสิบห้าชั่วโมง!", [
                ("รุ่นนี้ GoChek S24", "รุ่นนี้ GoChek S24", "c4_1"),
                ("แบตอึดรวมเคส 35 ชั่วโมง!", "แบตอึดรวมเคส 35 ชั่วโมง", "c4_2"),
            ]),
            ("F", "น้องนุ้ยบ่นพี่บ่าวข้ามวันข้ามคืน แบตก็ไม่หมดนิ!", [
                ("น้องนุ้ยบ่นพี่บ่าวข้ามวัน", "น้องนุ้ยบ่นพี่บ่าวข้ามวัน", "c5_1"),
                ("แบตก็ไม่หมดนิ!", "แบตก็ไม่หมดนิ", "c5_2"),
            ]),
            ("M", "แบตไมค์รุ่นนี้อึดพอๆ กับแรงน้องนุ้ยเลยครับ", [
                ("แบตไมค์รุ่นนี้อึดสุดๆ", "แบตไมค์รุ่นนี้อึดสุดๆ", "c6_1"),
                ("อึดพอๆ กับแรงน้องนุ้ยเลยครับ!", "อึดพอๆ กับแรงน้องนุ้ยเลยครับ", "c6_2"),
            ]),
            ("M", "สายไลฟ์สดถ่ายคลิปยาวๆ กดตะกร้าเหลืองซ้ายล่างเลยครับ", [
                ("สายไลฟ์สดถ่ายคลิปยาวๆ", "สายไลฟ์สดถ่ายคลิปยาวๆ", "c7_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c7_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างเลยครับ", "ซ้ายล่างเลยครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov4-dual",
        "media_starts": [8.0, 24.0, 48.0, 72.0, 96.0, 108.0],
        "headlines": [
            ("POV: เมียกำลังอัดคลิปรีวิว", "แต่ผัวแอบกินขนม<br>หลังกล้อง!"),
            ("เสียงเคี้ยวกร๊อบแกร๊บแทรก!", "ดังชัดแจ๋ว<br>ระดับ ASMR!"),
            ("หลุดมาดสาวหวานทันที!", "ในกล่องมีไมค์คู่<br>ให้ถึง 2 ตัว!"),
            ("1 กล่องได้ไมค์ถึง 2 ตัว", "GoChek Ultra S24<br>คุ้มเกินราคา!"),
            ("รับเสียงคมชัดระดับสตูดิโอ", "สัมภาษณ์คู่<br>หรือ ASMR ก็เป๊ะ"),
            ("บทสรุปพ่อบ้านสายกิน", "ห้ามเคี้ยวขนม<br>เวลาเมียอัดคลิป!"),
        ],
        "turns": [
            ("F", "สวัสดีค่าทุกคน วันนี้น้องนุ้ยจะมารีวิวของดีนะคะ", [
                ("สวัสดีค่าทุกคน", "สวัสดีค่าทุกคน", "c0_1"),
                ("วันนี้น้องนุ้ยจะมารีวิวนะคะ", "วันนี้น้องนุ้ยจะมารีวิวนะคะ", "c0_2"),
            ]),
            ("M", "ง่ำๆ กร๊อบแกร๊บ อร่อยจังเลยขนมถุงนี้", [
                ("ง่ำๆ กร๊อบแกร๊บ", "ง่ำๆ กร๊อบแกร๊บ", "c1_1"),
                ("อร่อยจังเลยขนมถุงนี้!", "อร่อยจังเลยขนมถุงนี้", "c1_2"),
            ]),
            ("F", "พี่บ่าว! หยุดเคี้ยวเดี๋ยวนี้! เสียงขนมดังเข้าคลิปชัดแจ๋วเลย!", [
                ("พี่บ่าว! หยุดเคี้ยวเดี๋ยวนี้!", "พี่บ่าว หยุดเคี้ยวเดี๋ยวนี้", "c2_1"),
                ("เสียงขนมดังเข้าคลิปชัดแจ๋ว!", "เสียงขนมดังเข้าคลิปชัดแจ๋ว", "c2_2"),
            ]),
            ("M", "อ้าว น้องนุ้ยถือไมค์อยู่คนเดียว เสียงพี่บ่าวเข้าได้ไงครับ!", [
                ("อ้าว น้องนุ้ยถือไมค์คนเดียว", "อ้าว น้องนุ้ยถือไมค์คนเดียว", "c3_1"),
                ("เสียงพี่บ่าวเข้าได้ไงครับ!", "เสียงพี่บ่าวเข้าได้ไงครับ", "c3_2"),
            ]),
            ("F", "เบอะบะจริงนิ! ในกล่อง GoChek S24 มีไมค์คู่สองตัว!", [
                ("เบอะบะจริงนิ! GoChek S24", "เบอะบะจริงนิ GoChek S24", "c4_1"),
                ("ในกล่องให้ไมค์คู่มา 2 ตัว!", "ในกล่องให้ไมค์คู่มา 2 ตัว", "c4_2"),
            ]),
            ("F", "อีกตัวหนีบอยู่ที่คอเสื้อพี่บ่าว อัดพร้อมกันสองคนชัดแจ๋ว!", [
                ("อีกตัวหนีบอยู่คอเสื้อพี่บ่าว", "อีกตัวหนีบอยู่คอเสื้อพี่บ่าว", "c5_1"),
                ("อัดพร้อมกัน 2 คนชัดแจ๋ว!", "อัดพร้อมกัน 2 คนชัดแจ๋ว", "c5_2"),
            ]),
            ("M", "มิน่าล่ะ เสียงกรอบขนมชัดระดับเอเอสเอ็มอาร์เลยครับ", [
                ("มิน่าล่ะ เสียงกรอบขนม", "มิน่าล่ะ เสียงกรอบขนม", "c6_1"),
                ("ชัดระดับ ASMR เลยครับ!", "ชัดระดับ ASMR เลยครับ", "c6_2"),
            ]),
            ("M", "ใครอยากได้ไมค์คู่สองตัวสุดคุ้ม กดตะกร้าเหลืองซ้ายล่างครับ", [
                ("ไมค์คู่ 2 ตัวสุดคุ้ม!", "ไมค์คู่ 2 ตัวสุดคุ้ม", "c7_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c7_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างครับ", "ซ้ายล่างครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov5-plug",
        "media_starts": [14.0, 29.0, 56.0, 82.0, 100.0, 108.0],
        "headlines": [
            ("POV: อัดคลิปให้เมียครึ่งชั่วโมง", "แต่เพิ่งนึกได้ว่า<br>ลืมเปิดบลูทูธ!"),
            ("พี่บ่าวเหงื่อแตก...", "คิดว่าเสียง<br>ไม่เข้าแน่ๆ!"),
            ("รอดตายหวุดหวิด!", "เสียบตูดมือถือปุ๊บ<br>ใช้ได้เลย!"),
            ("Plug & Play ไม่ต้องง้อแอป", "GoChek Ultra S24<br>ต่ออัตโนมัติ!"),
            ("ชาร์จมือถือไปพร้อมอัดคลิปได้", "มีพอร์ต Type-C<br>ข้างตัวรับสัญญาณ"),
            ("บทสรุปไมค์ช่วยชีวิตพี่บ่าว", "ใช้ง่ายจนคนซื่อบื้อ<br>ก็ไม่พลาด!"),
        ],
        "turns": [
            ("M", "น้องนุ้ย พี่บ่าวขอโทษ ลืมต่อบลูทูธไมค์ให้ เสียงไม่เข้าแน่เลย", [
                ("น้องนุ้ย พี่บ่าวขอโทษที", "น้องนุ้ย พี่บ่าวขอโทษที", "c0_1"),
                ("ลืมต่อบลูทูธไมค์ให้ครับ!", "ลืมต่อบลูทูธไมค์ให้ครับ", "c0_2"),
            ]),
            ("F", "ว่าพรือนะพี่บ่าว! นี่น้องนุ้ยแหลงจนคอแห้งไปครึ่งชั่วโมงแล้วนะ!", [
                ("ว่าพรือนะพี่บ่าว!", "ว่าพรือนะพี่บ่าว", "c1_1"),
                ("น้องนุ้ยแหลงจนคอแห้งแล้วนะ!", "น้องนุ้ยแหลงจนคอแห้งแล้วนะ", "c1_2"),
            ]),
            ("F", "เดี๋ยวก่อน... อ้าว เสียงเข้าครบทุกคำเลยนิ ชัดแจ๋วด้วย!", [
                ("เดี๋ยวก่อน... อ้าว!", "เดี๋ยวก่อน อ้าว", "c2_1"),
                ("เสียงเข้าครบทุกคำเลยนิ!", "เสียงเข้าครบทุกคำเลยนิ", "c2_2"),
            ]),
            ("M", "จริงเหรอน้องนุ้ย! ไม่ได้ต่อบลูทูธแล้วเสียงเข้าได้ไงครับ!", [
                ("จริงเหรอน้องนุ้ย!", "จริงเหรอน้องนุ้ย", "c3_1"),
                ("ไม่ต่อบลูทูธเสียงเข้าได้ไง!", "ไม่ต่อบลูทูธเสียงเข้าได้ไง", "c3_2"),
            ]),
            ("F", "ก็ไมค์ GoChek S24 ไม่ต้องต่อบลูทูธ ไม่ต้องลงแอปไงล่ะ!", [
                ("ก็ไมค์ GoChek S24", "ก็ไมค์ GoChek S24", "c4_1"),
                ("ไม่ต้องต่อบลูทูธ ไม่ต้องลงแอป!", "ไม่ต้องต่อบลูทูธ ไม่ต้องลงแอป", "c4_2"),
            ]),
            ("F", "เสียบตูดมือถือปุ๊บติดปั๊บ แถมเสียบชาร์จมือถือพร้อมกันได้เลย!", [
                ("เสียบตูดมือถือปุ๊บติดปั๊บ!", "เสียบตูดมือถือปุ๊บติดปั๊บ", "c5_1"),
                ("ชาร์จมือถือพร้อมกันได้เลย!", "ชาร์จมือถือพร้อมกันได้เลย", "c5_2"),
            ]),
            ("M", "รอดตายหวุดหวิด ขอบคุณระบบเสียบปุ๊บติดปั๊บจริงๆ ครับ", [
                ("พี่บ่าวรอดตายหวุดหวิด!", "พี่บ่าวรอดตายหวุดหวิด", "c6_1"),
                ("เสียบปุ๊บติดปั๊บช่วยชีวิตไว้!", "เสียบปุ๊บติดปั๊บช่วยชีวิตไว้", "c6_2"),
            ]),
            ("M", "ใครอยากได้ไมค์ใช้ง่ายไม่ต้องตั้งค่า กดตะกร้าเหลืองซ้ายล่างครับ", [
                ("ไมค์ใช้ง่ายไม่ต้องตั้งค่า!", "ไมค์ใช้ง่ายไม่ต้องตั้งค่า", "c7_1"),
                ("พิกัดไมค์อยู่ข้างล่างครับ", "พิกัดไมค์อยู่ข้างล่างครับ", "c7_2"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างครับ", "ซ้ายล่างครับ", "leftdown"),
        ],
    },
]


def call_single_speaker_tts(lines: list[str], voice_name: str, style_desc: str, out_wav: Path, key_offset: int = 0):
    """Call Gemini TTS with a SINGLE prebuiltVoiceConfig so the speaker voice is 100% locked and never swaps."""
    api_keys = get_gemini_api_keys()
    numbered = "\n\n".join(f"{line}" for line in lines)
    prompt = f"""[Voice style: {style_desc}
Pronunciation rule: Speak clear, lively, natural Thai with Southern Thai couple charm ("พี่บ่าว" and "น้องนุ้ย").
Leave a clean 0.8 second silence pause between each paragraph.]

{numbered}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            },
        },
    }

    models = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
    for model_name in models:
        for i in range(len(api_keys)):
            key = api_keys[(i + key_offset) % len(api_keys)]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    b64_audio = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                    pcm_bytes = base64.b64decode(b64_audio)
                    with wave.open(str(out_wav), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(pcm_bytes)
                    print(f"    [Single-TTS OK] {voice_name} -> {out_wav.parent.name}/{out_wav.name} ({model_name})", flush=True)
                    return
            except Exception as e:
                print(f"    [Single-TTS retry] {voice_name} {model_name} key#{(i + key_offset) % len(api_keys) + 1}: {e}", flush=True)
                time.sleep(1.2)
    raise RuntimeError(f"Failed Single-TTS for {out_wav}")


def split_into_n_segments(raw_wav: Path, n_expected: int, weights: list[int]) -> tuple[int, list[np.ndarray]]:
    with wave.open(str(raw_wav), "rb") as wf:
        sr = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    win = int(0.02 * sr)
    n_wins = len(audio) // win
    frames = audio[: n_wins * win].reshape(n_wins, win).astype(np.float32) / 32768.0
    rms = np.sqrt(np.mean(frames**2, axis=1))
    db = 20 * np.log10(rms + 1e-7)

    is_speech = db > -38.0
    islands = []
    in_seg = False
    s0 = 0
    for i, sp in enumerate(is_speech):
        if sp and not in_seg:
            in_seg = True
            s0 = i
        elif not sp and in_seg:
            if i + 10 < len(is_speech) and np.any(is_speech[i : i + 10]):
                continue
            in_seg = False
            if (i - s0) * 0.02 >= 0.12:
                islands.append((max(0.0, s0 * 0.02 - 0.02), min(len(audio) / sr, i * 0.02 + 0.03)))
    if in_seg:
        islands.append((max(0.0, s0 * 0.02 - 0.02), len(audio) / sr))

    if len(islands) < n_expected:
        t_start = islands[0][0] if islands else 0.0
        t_end = islands[-1][1] if islands else len(audio) / sr
        tot_w = sum(weights)
        cur = t_start
        islands = []
        for w in weights:
            nxt = cur + (t_end - t_start) * (w / tot_w)
            islands.append((round(cur, 3), round(nxt, 3)))
            cur = nxt
    else:
        while len(islands) > n_expected:
            tot_dur = sum(b - a for a, b in islands)
            tot_w = sum(weights)
            best_idx = 0
            best_score = float("inf")
            for idx in range(len(islands) - 1):
                gap = islands[idx + 1][0] - islands[idx][1]
                merged_dur = islands[idx + 1][1] - islands[idx][0]
                target_idx = min(n_expected - 1, int(idx * n_expected / len(islands)))
                expected_dur = tot_dur * (weights[target_idx] / tot_w)
                score = gap * 3.0 + max(0.0, merged_dur - expected_dur * 1.4)
                if score < best_score:
                    best_score = score
                    best_idx = idx
            islands[best_idx] = (islands[best_idx][0], islands[best_idx + 1][1])
            islands.pop(best_idx + 1)

    chunks = [audio[max(0, int(a * sr)) : min(len(audio), int(b * sr))] for a, b in islands]
    return sr, chunks


def align_words_in_waveform(samples: np.ndarray, sr: int, words: list[str], seg_offset: float) -> list[dict]:
    dur = len(samples) / sr
    if len(words) == 1:
        return [{"w": words[0], "s": round(seg_offset, 3), "e": round(seg_offset + dur, 3)}]

    hop = max(1, int(0.01 * sr))
    n_hops = max(1, len(samples) // hop)
    env = np.sqrt(np.mean(samples[: n_hops * hop].reshape(n_hops, hop) ** 2, axis=1)) + 1e-4
    cum_energy = np.cumsum(env)
    cum_energy = cum_energy / cum_energy[-1]

    weights = [max(2, len(w.replace(" ", ""))) for w in words]
    total_w = sum(weights)
    cum_w = 0
    out = []
    cur_s = 0.0
    for idx, (w, wt) in enumerate(zip(words, weights)):
        cum_w += wt
        if idx == len(words) - 1:
            nxt_t = dur
        else:
            target_frac = cum_w / total_w
            hop_idx = int(np.searchsorted(cum_energy, target_frac))
            nxt_t = round(min(dur - 0.03, max(cur_s + 0.06, (hop_idx / n_hops) * dur)), 3)
        out.append({
            "w": w,
            "s": round(seg_offset + cur_s, 3),
            "e": round(seg_offset + nxt_t, 3),
        })
        cur_s = nxt_t
    return out


def generate_tts_for_clip(args):
    spec, clip_idx = args
    cid = spec["id"]
    clip_dir = HERE / cid
    clip_dir.mkdir(parents=True, exist_ok=True)
    turns = spec["turns"]
    full_turns = []
    for idx, (spk, tts_line, word_tuples) in enumerate(turns):
        if idx == len(turns) - 1:
            full_turns.append((spk, tts_line, word_tuples + spec["cta_words"]))
        else:
            full_turns.append((spk, tts_line, word_tuples))

    f_lines = [t[1] for t in full_turns if t[0] == "F"]
    m_lines = [t[1] for t in full_turns if t[0] == "M"]

    f_raw_wav = clip_dir / "female_aoede_nui.wav"
    m_raw_wav = clip_dir / "male_puck_nui.wav"

    if not f_raw_wav.exists():
        call_single_speaker_tts(
            f_lines,
            voice_name="Aoede",
            style_desc="Cute, bright, energetic young Southern Thai girlfriend named น้องนุ้ย (สาวใต้เสียงใส น่ารักแต่ดุ พูดจังหวะกระชับชัดเจน)",
            out_wav=f_raw_wav,
            key_offset=clip_idx * 2,
        )
    if not m_raw_wav.exists():
        call_single_speaker_tts(
            m_lines,
            voice_name="Puck",
            style_desc="Playful, flustered, good-natured Southern Thai boyfriend named พี่บ่าว (พี่บ่าวคนซื่อ น้ำเสียงผู้ชายชัดเจน ตกใจฮาๆ)",
            out_wav=m_raw_wav,
            key_offset=clip_idx * 2 + 1,
        )


def assemble_clip(spec: dict):
    cid = spec["id"]
    clip_dir = HERE / cid
    out_vo = STUDIO / "assets" / "clips" / cid / "vo.wav"
    out_vo.parent.mkdir(parents=True, exist_ok=True)

    turns = spec["turns"]
    full_turns = []
    for idx, (spk, tts_line, word_tuples) in enumerate(turns):
        if idx == len(turns) - 1:
            full_turns.append((spk, tts_line, word_tuples + spec["cta_words"]))
        else:
            full_turns.append((spk, tts_line, word_tuples))

    f_indices = [i for i, (spk, _, _) in enumerate(full_turns) if spk == "F"]
    m_indices = [i for i, (spk, _, _) in enumerate(full_turns) if spk == "M"]

    f_weights = [sum(len(w[1].replace(" ", "")) for w in full_turns[i][2]) for i in f_indices]
    m_weights = [sum(len(w[1].replace(" ", "")) for w in full_turns[i][2]) for i in m_indices]

    f_raw_wav = clip_dir / "female_aoede_nui.wav"
    m_raw_wav = clip_dir / "male_puck_nui.wav"

    raw_sr_f, f_chunks = split_into_n_segments(f_raw_wav, len(f_indices), f_weights)
    raw_sr_m, m_chunks = split_into_n_segments(m_raw_wav, len(m_indices), m_weights)

    turn_chunks = {}
    for idx, chunk in zip(f_indices, f_chunks):
        turn_chunks[idx] = (raw_sr_f, chunk)
    for idx, chunk in zip(m_indices, m_chunks):
        turn_chunks[idx] = (raw_sr_m, chunk)

    tmp_dir = clip_dir / "_tmp_segs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_sr = 48000
    tempo = 1.32
    gap_sec = 0.06
    gap_samples = np.zeros(int(gap_sec * out_sr), dtype=np.int16)

    combined_mono = []
    all_words = []
    cur_time = 0.0

    for idx, (spk, _, word_tuples) in enumerate(full_turns):
        raw_sr, chunk = turn_chunks[idx]
        in_wav = tmp_dir / f"turn_in_{idx:02d}.wav"
        out_wav = tmp_dir / f"turn_out_{idx:02d}.wav"
        with wave.open(str(in_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(raw_sr)
            wf.writeframes(chunk.tobytes())

        if spk == "F":
            pitch = 1.10
            adj_tempo = round(tempo / pitch, 5)
            af = f"asetrate={int(raw_sr * pitch)},aresample={out_sr},atempo={adj_tempo},highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.0"
        else:
            af = f"atempo={tempo},highpass=f=95"
            if cid == "goc01-pov-32s" and idx == 3:
                af += ",highpass=f=240,lowpass=f=5500,volume=1.15"

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(in_wav), "-af", af, "-ar", str(out_sr), "-ac", "1", str(out_wav)],
            check=True,
            capture_output=True,
        )

        with wave.open(str(out_wav), "rb") as wf:
            seg_pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

        seg_float = seg_pcm.astype(np.float32) / 32768.0
        seg_dur = len(seg_pcm) / out_sr
        spoken_list = [w[1] for w in word_tuples]
        aligned = align_words_in_waveform(seg_float, out_sr, spoken_list, cur_time)
        all_words.extend(aligned)

        combined_mono.append(seg_pcm)
        combined_mono.append(gap_samples)
        cur_time += seg_dur + gap_sec

    full_mono = np.concatenate(combined_mono)
    pre_norm_wav = tmp_dir / "pre_norm.wav"
    with wave.open(str(pre_norm_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(out_sr)
        wf.writeframes(full_mono.tobytes())

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(pre_norm_wav), "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", str(out_sr), "-ac", "2", str(out_vo)],
        check=True,
        capture_output=True,
    )

    total_dur = round(len(full_mono) / out_sr, 3)
    (clip_dir / "vo_meta.json").write_text(json.dumps({"duration": total_dur}, indent=2), encoding="utf-8")
    (clip_dir / "whisper_words.json").write_text(json.dumps(all_words, ensure_ascii=False, indent=2), encoding="utf-8")

    clauses = []
    left_cap_ids = []
    right_cap_ids = []
    for idx, (spk, _, word_tuples) in enumerate(turns):
        clauses.append((True, word_tuples))
        cap_id = f"cap{idx:02d}"
        if spk == "F":
            left_cap_ids.append(cap_id)
        else:
            right_cap_ids.append(cap_id)
    clauses.append((False, spec["cta_words"]))

    def make_sfx(c):
        res = []
        for idx, (spk, _, word_tuples) in enumerate(turns):
            first_cue = word_tuples[0][2]
            t_cue = c[first_cue]
            if spk == "F":
                res.append(("msg_recv.mp3", round(t_cue + 0.01, 3), 0.5, 0.28))
            else:
                res.append(("msg_send.mp3", round(t_cue + 0.01, 3), 0.45, 0.28))
        t4_cue = turns[4][2][0][2]
        t6_cue = turns[6][2][0][2]
        res.append(("ding.wav", round(c[t4_cue] + 0.2, 3), 0.6, 0.28))
        res.append(("punch.mp3", round(c[t6_cue] + 0.15, 3), 0.45, 0.32))
        res.append(("cash_register.mp3", round(c["cart"], 3), 0.9, 0.38))
        return res

    html_path = STUDIO / "compositions" / f"{cid}.html"
    html_path.write_text("<!-- CAPTIONS:BEGIN --><!-- CAPTIONS:END --><!-- VO:BEGIN --><!-- VO:END --><!-- SFX:BEGIN --><!-- SFX:END -->", encoding="utf-8")
    cues = build(clip_dir, clauses, make_sfx, caption_stop="cart", gaps=[])

    n_t = len(turns)
    cut1 = round(cues[turns[1][2][0][2]], 2)
    cut2 = round(cues[turns[2][2][0][2]], 2)
    cut3 = round(cues[turns[4][2][0][2]], 2)
    cut4 = round(cues[turns[min(n_t - 3, 5)][2][0][2]], 2)
    cut5 = round(cues[turns[n_t - 2][2][0][2]], 2)
    cta_start = round(cues["cart"], 2)
    tot = cues["total"]

    shots = [
        (0.0, round(cut1, 2)),
        (cut1, round(cut2 - cut1, 2)),
        (cut2, round(cut3 - cut2, 2)),
        (cut3, round(cut4 - cut3, 2)),
        (cut4, round(cut5 - cut4, 2)),
        (cut5, round(tot - cut5, 2)),
    ]
    beats = [
        (0.0, round(cut1, 2)),
        (cut1, round(cut2 - cut1, 2)),
        (cut2, round(cut3 - cut2, 2)),
        (cut3, round(cut4 - cut3, 2)),
        (cut4, round(cut5 - cut4, 2)),
        (cut5, round(cta_start - cut5, 2)),
    ]
    cta_dur = round(tot - cta_start, 2)

    left_sel = ",\n      ".join(f"#{x}" for x in left_cap_ids)
    left_before = ",\n      ".join(f"#{x}::before" for x in left_cap_ids)
    left_in = ",\n      ".join(f"#{x} .cap-in" for x in left_cap_ids)
    left_w = ",\n      ".join(f"#{x} .cap-in .w" for x in left_cap_ids)
    left_w_first = ",\n      ".join(f"#{x} .cap-in .w:first-child" for x in left_cap_ids)
    left_in_before = ",\n      ".join(f"#{x} .cap-in::before" for x in left_cap_ids)
    left_after = ",\n      ".join(f"#{x}::after" for x in left_cap_ids)

    right_sel = ",\n      ".join(f"#{x}" for x in right_cap_ids)
    right_before = ",\n      ".join(f"#{x}::before" for x in right_cap_ids)
    right_in = ",\n      ".join(f"#{x} .cap-in" for x in right_cap_ids)
    right_w = ",\n      ".join(f"#{x} .cap-in .w" for x in right_cap_ids)
    right_w_first = ",\n      ".join(f"#{x} .cap-in .w:first-child" for x in right_cap_ids)
    right_in_before = ",\n      ".join(f"#{x} .cap-in::before" for x in right_cap_ids)
    right_after = ",\n      ".join(f"#{x}::after" for x in right_cap_ids)

    left_js_list = ", ".join(f'"{x}"' for x in left_cap_ids)
    m_starts = spec["media_starts"]
    hl = spec["headlines"]

    html_content = f"""<!doctype html>
<html lang="th">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/kit.css" />
    <script src="assets/clips/{cid}/timing.js"></script>
    <script src="kit/kit.js"></script>
    <style>
      .cyan {{
        color: #00f2fe;
      }}
      /* Top Hook & Scene Headlines — Large, Clear Multi-Line Centered Layout */
      .scene-sub {{
        top: 135px;
        left: 60px !important;
        right: 60px !important;
        font-size: 54px;
        line-height: 1.22;
        white-space: normal !important;
        color: var(--paper);
      }}
      .scene-title {{
        top: 215px;
        left: 60px !important;
        right: 60px !important;
        font-size: 80px;
        line-height: 1.18;
        white-space: normal !important;
      }}

      /* ============================================================================
         STACKED LINE MESSENGER CHAT BUBBLES (1 Short Clause = 1 Separate Bubble Box!)
         If a turn has 2+ phrases, each phrase is its own separate bubble stacked below!
         ============================================================================ */
      .cap {{
        display: flex !important;
        left: 36px !important;
        right: 36px !important;
        top: 1245px !important;
        align-items: flex-start !important;
        text-shadow: none !important;
      }}
      .cap-in {{
        position: relative;
        display: flex !important;
        flex-direction: column !important;
        gap: 12px !important;
        max-width: 760px !important;
        padding: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
      }}
      .cap-in .w {{
        display: block !important;
        width: fit-content !important;
        max-width: 740px !important;
        padding: 16px 28px !important;
        font-size: 40px !important;
        font-weight: 700;
        line-height: 1.28 !important;
        white-space: nowrap !important;
        color: #111111 !important;
        text-shadow: none !important;
        border-radius: 26px;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.35);
      }}

      /* FEMALE (น้องนุ้ย) — LEFT STACKED WHITE LINE BUBBLES */
      {left_sel} {{
        justify-content: flex-start !important;
      }}
      {left_before} {{
        content: "น";
        flex: 0 0 70px;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff9eb5, #ff5277);
        color: #ffffff;
        font-size: 38px;
        font-weight: 700;
        line-height: 70px;
        text-align: center;
        margin-right: 14px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
      }}
      {left_in} {{
        align-items: flex-start !important;
      }}
      {left_w} {{
        background: #ffffff;
        text-align: left !important;
      }}
      {left_w_first} {{
        border-radius: 6px 26px 26px 26px;
      }}
      {left_in_before} {{
        content: "น้องนุ้ย";
        position: absolute;
        top: -42px;
        left: 4px;
        font-size: 30px;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}
      {left_after} {{
        content: "18:05";
        align-self: flex-end;
        margin-left: 12px;
        margin-bottom: 4px;
        font-size: 24px;
        color: rgba(255, 255, 255, 0.92);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}

      /* MALE (พี่บ่าว) — RIGHT STACKED GREEN LINE BUBBLES */
      {right_sel} {{
        justify-content: flex-end !important;
      }}
      {right_before} {{
        content: "อ่านแล้ว\\A 18:05";
        white-space: pre;
        align-self: flex-end;
        margin-right: 12px;
        margin-bottom: 4px;
        font-size: 23px;
        line-height: 1.2;
        text-align: right;
        color: rgba(255, 255, 255, 0.95);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
      }}
      {right_in} {{
        align-items: flex-end !important;
      }}
      {right_w} {{
        background: #8de07a;
        text-align: left !important;
      }}
      {right_w_first} {{
        border-radius: 26px 6px 26px 26px;
      }}
      {right_in_before} {{
        content: "พี่บ่าว";
        position: absolute;
        top: -42px;
        right: 4px;
        font-size: 30px;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}
      {right_after} {{
        content: "บ";
        flex: 0 0 70px;
        width: 70px;
        height: 70px;
        border-radius: 50%;
        background: linear-gradient(135deg, #60a5fa, #2563eb);
        color: #ffffff;
        font-size: 38px;
        font-weight: 700;
        line-height: 70px;
        text-align: center;
        margin-left: 14px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
      }}

      /* CLEAN FINAL CTA — Large, Punchy Multi-Line Centered Layout */
      #cta-1 {{
        top: 220px;
        left: 60px !important;
        right: 60px !important;
        font-size: 108px;
        line-height: 1.12;
        white-space: normal !important;
      }}
      #cta-sub {{
        top: 360px;
        left: 60px !important;
        right: 60px !important;
        font-size: 72px;
        line-height: 1.24;
        white-space: normal !important;
        color: var(--paper);
      }}
      #cta-sub .sub-line2 {{
        display: block;
        font-size: 64px;
        color: #00f2fe;
        margin-top: 10px;
      }}
      #k-arrow {{
        left: 0;
        top: 0;
        width: 1080px;
        height: 1920px;
      }}
      #k-arrow path {{
        fill: none;
        stroke: var(--volt);
        stroke-width: 22;
        stroke-linecap: round;
        stroke-linejoin: round;
        filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.85));
      }}
      #cta-tag {{
        left: 260px;
        top: 1290px;
        font-size: 98px;
      }}

      /* WATERMARK: BOTTOM-ALIGNED, NO BLACK BOX */
      #wm {{
        left: 0 !important;
        right: 0 !important;
        top: auto !important;
        bottom: 26px !important;
        width: 100% !important;
        height: auto !important;
        text-align: center !important;
        z-index: 20;
      }}
      #wm span {{
        position: static !important;
        display: inline-block !important;
        transform: none !important;
        background: transparent !important;
        padding: 0 !important;
        border-radius: 0 !important;
        font-size: 28px !important;
        color: rgba(255, 255, 255, 0.78) !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85) !important;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{cid}" data-start="0" data-duration="{tot}" data-width="1080" data-height="1920">
      <!-- 100% CRISP REAL PRODUCT FOOTAGE SHOTS -->
      <div class="cam" id="c0"><div class="kb" id="k0" data-layout-allow-overflow=""><video id="v0" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[0][0]}" data-duration="{shots[0][1]}" data-media-start="{m_starts[0]}" data-track-index="0"></video></div></div>
      <div class="cam" id="c1"><div class="kb" id="k1" data-layout-allow-overflow=""><video id="v1" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[1][0]}" data-duration="{shots[1][1]}" data-media-start="{m_starts[1]}" data-track-index="0"></video></div></div>
      <div class="cam" id="c2"><div class="kb" id="k2" data-layout-allow-overflow=""><video id="v2" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[2][0]}" data-duration="{shots[2][1]}" data-media-start="{m_starts[2]}" data-track-index="0"></video></div></div>
      <div class="cam" id="c3"><div class="kb" id="k3" data-layout-allow-overflow=""><video id="v3" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[3][0]}" data-duration="{shots[3][1]}" data-media-start="{m_starts[3]}" data-track-index="0"></video></div></div>
      <div class="cam" id="c4"><div class="kb" id="k4" data-layout-allow-overflow=""><video id="v4" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[4][0]}" data-duration="{shots[4][1]}" data-media-start="{m_starts[4]}" data-track-index="0"></video></div></div>
      <div class="cam" id="c5"><div class="kb" id="k5" data-layout-allow-overflow=""><video id="v5" class="clip" src="assets/goc01/footage.mp4" muted playsinline data-start="{shots[5][0]}" data-duration="{shots[5][1]}" data-media-start="{m_starts[5]}" data-track-index="0"></video></div></div>

      <!-- CLEAN TOP HEADLINES (Fitted inside Safe Zone) -->
      <div class="beat clip" id="b-hook" data-start="{beats[0][0]}" data-duration="{beats[0][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[0][0]}</div>
        <div class="t center volt scene-title" id="t-hook">{hl[0][1]}</div>
      </div>

      <div class="beat clip" id="b-proof" data-start="{beats[1][0]}" data-duration="{beats[1][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[1][0]}</div>
        <div class="t center hot scene-title" id="t-proof">{hl[1][1]}</div>
      </div>

      <div class="beat clip" id="b-rap" data-start="{beats[2][0]}" data-duration="{beats[2][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[2][0]}</div>
        <div class="t center volt scene-title" id="t-rap">{hl[2][1]}</div>
      </div>

      <div class="beat clip" id="b-hero" data-start="{beats[3][0]}" data-duration="{beats[3][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[3][0]}</div>
        <div class="t center cyan scene-title" id="t-hero">{hl[3][1]}</div>
      </div>

      <div class="beat clip" id="b-steal" data-start="{beats[4][0]}" data-duration="{beats[4][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[4][0]}</div>
        <div class="t center hot scene-title" id="t-steal">{hl[4][1]}</div>
      </div>

      <div class="beat clip" id="b-payoff" data-start="{beats[5][0]}" data-duration="{beats[5][1]}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center scene-sub">{hl[5][0]}</div>
        <div class="t center volt scene-title" id="t-payoff">{hl[5][1]}</div>
      </div>

      <!-- CLEAN FINAL CTA -->
      <div class="beat clip" id="b-cta" data-start="{cta_start}" data-duration="{cta_dur}" data-track-index="2">
        <div class="scrim top"></div>
        <div class="t center volt" id="cta-1">กดตะกร้าเหลือง</div>
        <div class="t center" id="cta-sub">GoChek Ultra S24<span class="sub-line2">ของแท้ • ประกันศูนย์</span></div>
        <svg class="fx" id="k-arrow" viewBox="0 0 1080 1920">
          <path id="k-shaft" d="M 330 620 C 180 850 120 1160 160 1420" />
          <path id="k-head" d="M 80 1340 L 160 1430 L 250 1350" />
        </svg>
        <div class="t volt" id="cta-tag">ซ้ายล่าง</div>
      </div>

      <!-- CAPTIONS:BEGIN -->
      <!-- CAPTIONS:END -->

      <div id="flash"></div>
      <div id="wm"><span>สงวนลิขสิทธิ์ช่อง rizanntry ห้ามคัดลอก/ดัดแปลง</span></div>

      <!-- VO:BEGIN -->
      <!-- VO:END -->
      <audio id="bgm" src="assets/shared/bgm_lofi.wav" data-start="0" data-duration="{tot}" data-track-index="11" data-volume="0.04" data-carve="0.25" data-carve-targets="vo0"></audio>
      <!-- SFX:BEGIN -->
      <!-- SFX:END -->
    </div>

    <script>
      const T = window.TIMING.cues;
      const tl = gsap.timeline({{ paused: true }});
      const $ = (s) => document.querySelector(s);
      const flash = HF.flash(tl);
      const pop = (sel, t, from = {{ scale: 0, rotation: -4 }}, ease = "back.out(2.0)", dur = 0.32) =>
        tl.fromTo(sel, {{ opacity: 0, ...from }}, {{ opacity: 1, scale: 1, rotation: 0, x: 0, y: 0, duration: dur, ease }}, t);

      const SHOTS = [
        [{shots[0][0]}, {shots[0][1]}, 1.04, 1.14],
        [{shots[1][0]}, {shots[1][1]}, 1.06, 1.16],
        [{shots[2][0]}, {shots[2][1]}, 1.06, 1.18],
        [{shots[3][0]}, {shots[3][1]}, 1.08, 1.18],
        [{shots[4][0]}, {shots[4][1]}, 1.05, 1.15],
        [{shots[5][0]}, {shots[5][1]}, 1.04, 1.14],
      ];
      SHOTS.forEach(([s, d, z0, z1], i) => {{
        tl.fromTo(`#k${{i}}`, {{ scale: z0 }}, {{ scale: z1, duration: d, ease: "none" }}, s);
        if (i > 0) tl.fromTo(`#c${{i}}`, {{ scale: 1.12 }}, {{ scale: 1, duration: 0.28, ease: "expo.out" }}, s);
      }});

      pop("#t-hook", 0.08, {{ y: -30, rotation: 0 }}, "power3.out", 0.28);
      pop("#t-proof", {shots[1][0]}, {{ scale: 1.3, rotation: -2 }}, "power4.out", 0.28);
      pop("#t-rap", {shots[2][0]}, {{ scale: 1.3, rotation: 2 }}, "power4.out", 0.28);
      pop("#t-hero", {shots[3][0]}, {{ y: -30, rotation: 0 }}, "power3.out", 0.28);
      pop("#t-steal", {shots[4][0]}, {{ scale: 1.4, rotation: -3 }}, "back.out(2.2)", 0.28);
      pop("#t-payoff", {shots[5][0]}, {{ y: -30, rotation: 0 }}, "power3.out", 0.28);

      flash(T.cart, 0.35, 0.2);
      pop("#cta-1", T.cart, {{ scale: 1.5, rotation: 0 }}, "power4.out", 0.28);
      pop("#cta-sub", T.cart + 0.1, {{ y: 24, rotation: 0 }}, "expo.out", 0.25);
      const sl = HF.dash($("#k-shaft"));
      const hl = HF.dash($("#k-head"));
      tl.fromTo("#k-shaft", {{ strokeDashoffset: sl }}, {{ strokeDashoffset: 0, duration: 0.35, ease: "power2.inOut" }}, T.cart + 0.12);
      tl.fromTo("#k-head", {{ strokeDashoffset: hl }}, {{ strokeDashoffset: 0, duration: 0.14, ease: "power2.out" }}, T.cart + 0.44);
      pop("#cta-tag", T.cart + 0.22, {{ x: -60, rotation: 0 }}, "expo.out", 0.25);

      const leftIds = new Set([{left_js_list}]);
      document.querySelectorAll(".cap").forEach((cap) => {{
        const t0 = Number(cap.dataset.start);
        const fromX = leftIds.has(cap.id) ? -42 : 42;
        tl.fromTo(
          cap,
          {{ x: fromX, y: 20, opacity: 0 }},
          {{ x: 0, y: 0, opacity: 1, duration: 0.22, ease: "power3.out" }},
          t0
        );
        const words = [...cap.querySelectorAll(".w")];
        words.forEach((w, i) => {{
          const s = Number(w.dataset.s);
          if (i > 0) {{
            tl.set(w, {{ opacity: 0 }}, t0);
          }}
          tl.fromTo(
            w,
            {{ opacity: 0, y: 18, scale: 0.9 }},
            {{ opacity: 1, y: 0, scale: 1, color: "#d90429", duration: 0.22, ease: "back.out(1.8)", immediateRender: false }},
            s
          );
          if (i + 1 < words.length) {{
            tl.set(w, {{ color: "#111111" }}, Number(words[i + 1].dataset.s));
          }}
        }});
      }});

      window.__timelines["{cid}"] = tl;
    </script>
  </body>
</html>
"""
    html_path.write_text(html_content, encoding="utf-8")
    build(clip_dir, clauses, make_sfx, caption_stop="cart", gaps=[])


def main():
    print("=== Step 1: Generating Single-Speaker Female (น้องนุ้ย=Aoede) & Male (พี่บ่าว=Puck) TTS ===", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(generate_tts_for_clip, [(spec, i) for i, spec in enumerate(CLIPS_SPEC)]))

    print("=== Step 2: Assembling Stacked LINE Chat Bubbles for all 6 clips ===", flush=True)
    for idx, spec in enumerate(CLIPS_SPEC):
        print(f"  Assembling {idx + 1}/6: {spec['id']}", flush=True)
        assemble_clip(spec)
    print("ALL 6 POV CLIPS REBUILT WITH น้องนุ้ย & พี่บ่าว + STACKED BUBBLES!", flush=True)


if __name__ == "__main__":
    main()


