"""Generate all 5 new POV Couple Sitcom clips (ฮาดุหหห vs นาซิ) for GoChek Ultra S24:
1. goc01-pov1-anc  : ตอน เงียบเกินไปจนเมียระแวง! (ANC 90%)
2. goc01-pov2-wall : ตอน แอบซ่อนกล่องพัสดุหลังกำแพง 2 ชั้น ก็ไม่รอด! (50m Through-Wall)
3. goc01-pov3-bat  : ตอน รอเมียแบตหมด... แต่ไมค์ดันอึด 35 ชั่วโมง! (35h Battery Case)
4. goc01-pov4-dual : ตอน เมียอัดคลิปรีวิวสวยๆ แต่ผัวแอบเคี้ยวขนมเข้าไมค์ตัวที่ 2! (Dual Mic ASMR)
5. goc01-pov5-plug : ตอน ลืมเปิดบลูทูธ... อ้าว เสียบปุ๊บใช้ได้เลย! (Plug & Play + Pass-through Charge)
"""
import base64
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
        "id": "goc01-pov1-anc",
        "media_starts": [12.0, 26.0, 44.0, 76.0, 92.0, 108.0],
        "headlines": [
            ("POV: โทรคุยกับเมียริมถนน", "แต่ไมค์ตัดเสียงดีเกินไป!"),
            ("ตลาดนัดหรือห้องแอร์?!", "เงียบกริบจนเมียระแวง!"),
            ("ไม่ได้หนีเที่ยวครับที่รัก!", "เปิดโหมดตัดเสียงไว้เฉยๆ!"),
            ("ตัวต้นเหตุความเงียบ", "GoChek Ultra S24 (ANC 90%)"),
            ("ตัดเสียงรถริมถนนเกลี้ยง!", "กดปุ่มเดียวเงียบสนิท"),
            ("บทสรุปพ่อบ้านซื่อบื้อ", "ต้องเปิดเสียงแม่ค้าเป็นพยาน!"),
        ],
        "turns": [
            # (speaker: "F" or "M", tts_line, [(display, spoken, cue_name), ...])
            ("F", "นาซิ! ตอนนี้อยู่ไหน แหลงมาเดี๋ยวนี้!", [
                ("นาซิ", "นาซิ", "c0_1"),
                ("ตอนนี้อยู่ไหน", "ตอนนี้อยู่ไหน", "c0_2"),
                ("แหลงมาเดี๋ยวนี้", "แหลงมาเดี๋ยวนี้", "c0_3"),
            ]),
            ("M", "เดินซื้อแกงอยู่ตลาดนัดริมถนนครับที่รัก", [
                ("เดินซื้อแกง", "เดินซื้อแกง", "c1_1"),
                ("อยู่ตลาดนัดริมถนน", "อยู่ตลาดนัดริมถนน", "c1_2"),
                ("ครับที่รัก", "ครับที่รัก", "c1_3"),
            ]),
            ("F", "ขี้หกทั้งเพ! ตลาดนัดริมถนนที่ไหน เงียบกริบยังกะอยู่ในห้องแอร์!", [
                ("ขี้หกทั้งเพ", "ขี้หกทั้งเพ", "c2_1"),
                ("ตลาดนัดริมถนนที่ไหน", "ตลาดนัดริมถนนที่ไหน", "c2_2"),
                ("เงียบกริบยังกะอยู่ในห้องแอร์", "เงียบกริบยังกะอยู่ในห้องแอร์", "c2_3"),
            ]),
            ("F", "แอบหนีเที่ยวไหน บอกมาเดี๋ยวนี้เลยนะ!", [
                ("แอบหนีเที่ยวไหน", "แอบหนีเที่ยวไหน", "c3_1"),
                ("บอกมาเดี๋ยวนี้เลยนะ", "บอกมาเดี๋ยวนี้เลยนะ", "c3_2"),
            ]),
            ("M", "โถ่ที่รัก เค้าอยู่ตลาดจริงๆ แต่เสียบไมค์ GoChek Ultra S24 ค้างไว้", [
                ("โถ่ที่รัก", "โถ่ที่รัก", "c4_1"),
                ("เค้าอยู่ตลาดจริงๆ", "เค้าอยู่ตลาดจริงๆ", "c4_2"),
                ("แต่เสียบไมค์", "แต่เสียบไมค์", "c4_3"),
                ("GoChek Ultra S24", "GoChek Ultra S24", "c4_4"),
                ("ค้างไว้", "ค้างไว้", "c4_5"),
            ]),
            ("M", "ชิปอัจฉริยะมันตัดเสียงรถมอเตอร์ไซค์ออกเกลี้ยง 90% เลยครับ!", [
                ("ชิปอัจฉริยะ", "ชิปอัจฉริยะ", "c5_1"),
                ("มันตัดเสียงรถออกเกลี้ยง", "มันตัดเสียงรถออกเกลี้ยง", "c5_2"),
                ("90% เลยครับ", "90% เลยครับ", "c5_3"),
            ]),
            ("F", "ตัดเสียงเนียนเกินไปแล้วนิ! กดปิดโหมดตัดเสียงเดี๋ยวนี้ กูจะฟังเสียงแม่ค้า!", [
                ("ตัดเสียงเนียนเกินไปแล้วนิ", "ตัดเสียงเนียนเกินไปแล้วนิ", "c6_1"),
                ("กดปิดโหมดตัดเสียงเดี๋ยวนี้", "กดปิดโหมดตัดเสียงเดี๋ยวนี้", "c6_2"),
                ("กูจะฟังเสียงแม่ค้า", "กูจะฟังเสียงแม่ค้า", "c6_3"),
            ]),
            ("M", "เกือบบ้านแตกเพราะไมค์เทพเกิน ใครอยากได้ไมค์ตัดเสียงขั้นเทพ กดตะกร้าเหลืองซ้ายล่างครับ", [
                ("เกือบบ้านแตกเพราะไมค์เทพเกิน", "เกือบบ้านแตกเพราะไมค์เทพเกิน", "c7_1"),
                ("ใครอยากได้ไมค์ตัดเสียงขั้นเทพ", "ใครอยากได้ไมค์ตัดเสียงขั้นเทพ", "c7_2"),
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
            ("POV: แอบซ่อนพัสดุหลังบ้าน", "ห่างไป 2 ห้อง มีกำแพงกั้น!"),
            ("คิดว่าเมียไม่ได้ยิน...", "แต่ลืมถอดไมค์ที่ปกเสื้อ!"),
            ("ใบเสร็จสามพันห้า!", "เสียงชัดทะลุกำแพงปูน 2 ชั้น!"),
            ("ส่งสัญญาณไกล 50 เมตร", "GoChek Ultra S24 ทะลุกำแพง!"),
            ("ดูดเสียงกระซิบชัดแจ๋ว", "หนีไปมุมไหนของบ้านก็ไม่รอด!"),
            ("บทสรุปพ่อบ้านสายซ่อนงบ", "โดนยึดทั้งของเล่น ยึดทั้งไมค์!"),
        ],
        "turns": [
            ("M", "แอบแกะกล่องของเล่นในห้องเก็บของดีกว่า บอกฮาดุหหหไปว่าอันละสองร้อยพอ", [
                ("แอบแกะกล่องของเล่น", "แอบแกะกล่องของเล่น", "c0_1"),
                ("ในห้องเก็บของดีกว่า", "ในห้องเก็บของดีกว่า", "c0_2"),
                ("บอกฮาดุหหหว่าอันละสองร้อยพอ", "บอกฮาดุหหหว่าอันละสองร้อยพอ", "c0_3"),
            ]),
            ("F", "สองร้อยบ้านไหนนิ! ในใบเสร็จเขียนอยู่สามพันห้า!", [
                ("สองร้อยบ้านไหนนิ", "สองร้อยบ้านไหนนิ", "c1_1"),
                ("ในใบเสร็จเขียนอยู่สามพันห้า", "ในใบเสร็จเขียนอยู่สามพันห้า", "c1_2"),
            ]),
            ("M", "ฮะ! ที่รักอยู่ตั้งหน้าบ้าน ได้ยินเสียงเค้าทะลุกำแพงปูนสองชั้นได้ไงเนี่ย!", [
                ("ฮะ ที่รักอยู่ตั้งหน้าบ้าน", "ฮะ ที่รักอยู่ตั้งหน้าบ้าน", "c2_1"),
                ("ได้ยินทะลุกำแพงปูนสองชั้น", "ได้ยินทะลุกำแพงปูนสองชั้น", "c2_2"),
                ("ได้ไงเนี่ย", "ได้ไงเนี่ย", "c2_3"),
            ]),
            ("F", "ก็มึงหนีบไมค์ไว้ที่คอเสื้อ! เสียงกระซิบซ่อนงบชัดทะลุกำแพงมาเข้ามือถือกูเต็มสองรูหูเลย!", [
                ("ก็มึงหนีบไมค์ไว้ที่คอเสื้อ", "ก็มึงหนีบไมค์ไว้ที่คอเสื้อ", "c3_1"),
                ("เสียงกระซิบซ่อนงบ", "เสียงกระซิบซ่อนงบ", "c3_2"),
                ("ชัดทะลุกำแพงมาเต็มสองรูหูเลย", "ชัดทะลุกำแพงมาเต็มสองรูหูเลย", "c3_3"),
            ]),
            ("M", "ลืมไปเลยว่าไมค์ GoChek Ultra S24 มันส่งสัญญาณไกลตั้ง 50 เมตร", [
                ("ลืมไปเลยว่าไมค์", "ลืมไปเลยว่าไมค์", "c4_1"),
                ("GoChek Ultra S24", "GoChek Ultra S24", "c4_2"),
                ("ส่งสัญญาณไกลตั้ง 50 เมตร", "ส่งสัญญาณไกลตั้ง 50 เมตร", "c4_3"),
            ]),
            ("M", "เดินทะลุกำแพงไปหลังบ้าน สัญญาณยังไม่หลุดสักแอะ!", [
                ("เดินทะลุกำแพงไปหลังบ้าน", "เดินทะลุกำแพงไปหลังบ้าน", "c5_1"),
                ("สัญญาณยังไม่หลุดสักแอะ", "สัญญาณยังไม่หลุดสักแอะ", "c5_2"),
            ]),
            ("F", "ดีมาก! วันนี้ยึดทั้งของเล่น ยึดทั้งไมค์ ได้แรงอก!", [
                ("ดีมาก วันนี้ยึดทั้งของเล่น", "ดีมาก วันนี้ยึดทั้งของเล่น", "c6_1"),
                ("ยึดทั้งไมค์ ได้แรงอก", "ยึดทั้งไมค์ ได้แรงอก", "c6_2"),
            ]),
            ("M", "พ่อบ้านคนไหนไม่อยากโป๊ะ เช็กไมค์ก่อนนะครับ ส่วนพิกัดไมค์อยู่ตะกร้าเหลืองซ้ายล่างครับ", [
                ("พ่อบ้านคนไหนไม่อยากโป๊ะ", "พ่อบ้านคนไหนไม่อยากโป๊ะ", "c7_1"),
                ("เช็กไมค์ก่อนนะครับ", "เช็กไมค์ก่อนนะครับ", "c7_2"),
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
            ("POV: ช่วยเมียอัดคลิปตั้งแต่เช้า", "รอเมื่อไหร่ไมค์จะแบตหมด!"),
            ("ผ่านไป 8 ชั่วโมงเต็ม...", "ทำไมเมียยังมีแรงบ่นต่อ?!"),
            ("แลเคสชาร์จซะก่อน!", "แบตยังเหลือเต็มเปี่ยม!"),
            ("เคสชาร์จอัจฉริยะ 35 ชม.", "GoChek Ultra S24 แบตโคตรอึด!"),
            ("ชาร์จเก็บในเคสได้ตลอดวัน", "ไลฟ์สดยาวๆ ไม่มีสะดุด"),
            ("บทสรุปพ่อบ้านสายอดทน", "แบตไมค์อึดพอๆ กับแรงเมีย!"),
        ],
        "turns": [
            ("M", "ช่วยฮาดุหหหอัดคลิปมาตั้งแต่เช้าแล้ว เมื่อไหร่ไมค์จะแบตหมดสักที จะได้พักหูแล้วเรา", [
                ("ช่วยฮาดุหหหอัดคลิปตั้งแต่เช้า", "ช่วยฮาดุหหหอัดคลิปตั้งแต่เช้า", "c0_1"),
                ("เมื่อไหร่ไมค์จะแบตหมดสักที", "เมื่อไหร่ไมค์จะแบตหมดสักที", "c0_2"),
                ("จะได้พักหูแล้วเรา", "จะได้พักหูแล้วเรา", "c0_3"),
            ]),
            ("F", "แอบบ่นไหรอีกนาซิ! ฝันไปเถอะว่าแบตจะหมดง่ายๆ!", [
                ("แอบบ่นไหรอีกนาซิ", "แอบบ่นไหรอีกนาซิ", "c1_1"),
                ("ฝันไปเถอะว่าแบตจะหมดง่ายๆ", "ฝันไปเถอะว่าแบตจะหมดง่ายๆ", "c1_2"),
            ]),
            ("F", "แลเคสชาร์จซะก่อน เก็บเข้าเคสทีเดียว ชาร์จเต็มไวทันใจ!", [
                ("แลเคสชาร์จซะก่อน", "แลเคสชาร์จซะก่อน", "c2_1"),
                ("เก็บเข้าเคสทีเดียว", "เก็บเข้าเคสทีเดียว", "c2_2"),
                ("ชาร์จเต็มไวทันใจ", "ชาร์จเต็มไวทันใจ", "c2_3"),
            ]),
            ("M", "โห อัดคลิปมาทั้งวัน แบตในเคสยังไม่ยุบเลยเหรอที่รัก!", [
                ("โห อัดคลิปมาทั้งวัน", "โห อัดคลิปมาทั้งวัน", "c3_1"),
                ("แบตในเคสยังไม่ยุบเลยเหรอที่รัก", "แบตในเคสยังไม่ยุบเลยเหรอที่รัก", "c3_2"),
            ]),
            ("F", "รุ่นนี้ GoChek Ultra S24 แบตอึดรวมเคสชาร์จตั้ง 35 ชั่วโมงเต็ม!", [
                ("รุ่นนี้ GoChek Ultra S24", "รุ่นนี้ GoChek Ultra S24", "c4_1"),
                ("แบตอึดรวมเคสชาร์จ", "แบตอึดรวมเคสชาร์จ", "c4_2"),
                ("35 ชั่วโมงเต็ม", "35 ชั่วโมงเต็ม", "c4_3"),
            ]),
            ("F", "อัดคลิปขายของหรือบ่นมึงข้ามวันข้ามคืน แบตก็ไม่หมดนิ!", [
                ("อัดคลิปขายของ", "อัดคลิปขายของ", "c5_1"),
                ("หรือบ่นมึงข้ามวันข้ามคืน", "หรือบ่นมึงข้ามวันข้ามคืน", "c5_2"),
                ("แบตก็ไม่หมดนิ", "แบตก็ไม่หมดนิ", "c5_3"),
            ]),
            ("M", "คนออกแบบไมค์รุ่นนี้ แบตอึดพอๆ กับแรงแฟนสาวใต้เลยครับ", [
                ("คนออกแบบไมค์รุ่นนี้", "คนออกแบบไมค์รุ่นนี้", "c6_1"),
                ("แบตอึดพอๆ กับแรงแฟนสาวใต้เลย", "แบตอึดพอๆ กับแรงแฟนสาวใต้เลย", "c6_2"),
            ]),
            ("M", "ใครสายไลฟ์สดหรือถ่ายคลิปยาวๆ กดตะกร้าเหลืองซ้ายล่างเลยครับ", [
                ("ใครสายไลฟ์สดหรือถ่ายคลิปยาวๆ", "ใครสายไลฟ์สดหรือถ่ายคลิปยาวๆ", "c7_1"),
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
            ("POV: เมียกำลังอัดคลิปรีวิวสวยๆ", "แต่ผัวแอบกินขนมหลังกล้อง!"),
            ("เสียงเคี้ยวกร๊อบแกร๊บแทรก!", "ดังชัดระดับ ASMR!"),
            ("หลุดมาดสาวหวานทันที!", "ในกล่องมีไมค์คู่ 2 ตัว!"),
            ("1 กล่องได้ไมค์ถึง 2 ตัว", "GoChek Ultra S24 คุ้มเกินราคา!"),
            ("รับเสียงคมชัดระดับสตูดิโอ", "สัมภาษณ์คู่หรือทำ ASMR ก็เป๊ะ"),
            ("บทสรุปพ่อบ้านสายกิน", "โดนสั่งห้ามเคี้ยวขนมเวลาอัดคลิป!"),
        ],
        "turns": [
            ("F", "สวัสดีค่าทุกคน วันนี้ฮาดุจะมารีวิวสกินแคร์ตัวโปรดนะคะ", [
                ("สวัสดีค่าทุกคน", "สวัสดีค่าทุกคน", "c0_1"),
                ("วันนี้ฮาดุจะมารีวิว", "วันนี้ฮาดุจะมารีวิว", "c0_2"),
                ("สกินแคร์ตัวโปรดนะคะ", "สกินแคร์ตัวโปรดนะคะ", "c0_3"),
            ]),
            ("M", "ง่ำๆ กร๊อบแกร๊บ อร่อยจังเลยขนมถุงนี้", [
                ("ง่ำๆ กร๊อบแกร๊บ", "ง่ำๆ กร๊อบแกร๊บ", "c1_1"),
                ("อร่อยจังเลยขนมถุงนี้", "อร่อยจังเลยขนมถุงนี้", "c1_2"),
            ]),
            ("F", "นาซิ! หยุดเคี้ยวเดี๋ยวนี้! เสียงเคี้ยวขนมมึงดังเข้าคลิปชัดระดับเอเอสเอ็มอาร์เลยนิ!", [
                ("นาซิ หยุดเคี้ยวเดี๋ยวนี้", "นาซิ หยุดเคี้ยวเดี๋ยวนี้", "c2_1"),
                ("เสียงเคี้ยวขนมมึงดังเข้าคลิป", "เสียงเคี้ยวขนมมึงดังเข้าคลิป", "c2_2"),
                ("ชัดระดับ ASMR เลยนิ", "ชัดระดับ ASMR เลยนิ", "c2_3"),
            ]),
            ("M", "อ้าว ก็ที่รักถือไมค์อยู่คนเดียว เสียงเค้าเข้าไปได้ไงล่ะครับ!", [
                ("อ้าว ก็ที่รักถือไมค์อยู่คนเดียว", "อ้าว ก็ที่รักถือไมค์อยู่คนเดียว", "c3_1"),
                ("เสียงเค้าเข้าไปได้ไงล่ะครับ", "เสียงเค้าเข้าไปได้ไงล่ะครับ", "c3_2"),
            ]),
            ("F", "เบอะบะจริงนิ! ในกล่อง GoChek Ultra S24 มันให้ไมค์คู่มาสองตัว!", [
                ("เบอะบะจริงนิ ในกล่อง", "เบอะบะจริงนิ ในกล่อง", "c4_1"),
                ("GoChek Ultra S24", "GoChek Ultra S24", "c4_2"),
                ("มันให้ไมค์คู่มา 2 ตัว", "มันให้ไมค์คู่มา 2 ตัว", "c4_3"),
            ]),
            ("F", "แล้วอีกตัวมันหนีบอยู่ที่คอเสื้อมึง อัดพร้อมกันสองคนชัดแจ๋วเลย!", [
                ("แล้วอีกตัวหนีบอยู่ที่คอเสื้อมึง", "แล้วอีกตัวหนีบอยู่ที่คอเสื้อมึง", "c5_1"),
                ("อัดพร้อมกันสองคนชัดแจ๋วเลย", "อัดพร้อมกันสองคนชัดแจ๋วเลย", "c5_2"),
            ]),
            ("M", "มิน่าล่ะ เสียงกรอบขนมชัดยังกะนั่งเคี้ยวข้างหูคนดู", [
                ("มิน่าล่ะ เสียงกรอบขนมชัด", "มิน่าล่ะ เสียงกรอบขนมชัด", "c6_1"),
                ("ยังกะนั่งเคี้ยวข้างหูคนดู", "ยังกะนั่งเคี้ยวข้างหูคนดู", "c6_2"),
            ]),
            ("M", "ใครอยากได้ไมค์คู่สองตัวสุดคุ้ม กดตะกร้าเหลืองซ้ายล่างเลยครับ", [
                ("ใครอยากได้ไมค์คู่ 2 ตัวสุดคุ้ม", "ใครอยากได้ไมค์คู่ 2 ตัวสุดคุ้ม", "c7_1"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างเลยครับ", "ซ้ายล่างเลยครับ", "leftdown"),
        ],
    },
    {
        "id": "goc01-pov5-plug",
        "media_starts": [14.0, 29.0, 56.0, 82.0, 100.0, 108.0],
        "headlines": [
            ("POV: อัดคลิปให้เมียครึ่งชั่วโมง", "แต่เพิ่งนึกได้ว่าลืมเปิดบลูทูธ!"),
            ("พ่อบ้านเหงื่อแตก...", "คิดว่าเสียงไม่เข้าแน่ๆ!"),
            ("รอดตายหวุดหวิด!", "เสียบตูดมือถือปุ๊บ ใช้ได้เลย!"),
            ("Plug & Play ไม่ต้องง้อแอป", "GoChek Ultra S24 เชื่อมต่ออัตโนมัติ!"),
            ("ชาร์จมือถือไปพร้อมอัดคลิปได้", "มีพอร์ต Type-C ข้างตัวรับสัญญาณ"),
            ("บทสรุปไมค์ช่วยชีวิตพ่อบ้าน", "ใช้ง่ายจนคนซื่อบื้อก็ไม่พลาด!"),
        ],
        "turns": [
            ("M", "ที่รัก เค้าขอโทษที เมื่อกี้ลืมกดเชื่อมบลูทูธไมค์ให้ สงสัยที่พูดมาครึ่งชั่วโมงเสียงไม่เข้าแน่เลย", [
                ("ที่รัก เค้าขอโทษที", "ที่รัก เค้าขอโทษที", "c0_1"),
                ("เมื่อกี้ลืมเชื่อมบลูทูธไมค์ให้", "เมื่อกี้ลืมเชื่อมบลูทูธไมค์ให้", "c0_2"),
                ("สงสัยเสียงไม่เข้าแน่เลย", "สงสัยเสียงไม่เข้าแน่เลย", "c0_3"),
            ]),
            ("F", "ว่าพรือนะนาซิ! นี่กูแหลงจนคอแห้งไปครึ่งชั่วโมงแล้วนะ!", [
                ("ว่าพรือนะนาซิ", "ว่าพรือนะนาซิ", "c1_1"),
                ("นี่กูแหลงจนคอแห้ง", "นี่กูแหลงจนคอแห้ง", "c1_2"),
                ("ไปครึ่งชั่วโมงแล้วนะ", "ไปครึ่งชั่วโมงแล้วนะ", "c1_3"),
            ]),
            ("F", "เดี๋ยวก่อน... อ้าว เสียงเข้าครบทุกคำเลยนิ ชัดแจ๋วด้วย!", [
                ("เดี๋ยวก่อน อ้าว", "เดี๋ยวก่อน อ้าว", "c2_1"),
                ("เสียงเข้าครบทุกคำเลยนิ", "เสียงเข้าครบทุกคำเลยนิ", "c2_2"),
                ("ชัดแจ๋วด้วย", "ชัดแจ๋วด้วย", "c2_3"),
            ]),
            ("M", "จริงเหรอที่รัก! ทำไมไม่ได้ต่อบลูทูธแล้วเสียงเข้าล่ะครับ!", [
                ("จริงเหรอที่รัก", "จริงเหรอที่รัก", "c3_1"),
                ("ทำไมไม่ต่อบลูทูธแล้วเสียงเข้าล่ะ", "ทำไมไม่ต่อบลูทูธแล้วเสียงเข้าล่ะ", "c3_2"),
            ]),
            ("F", "ก็ไมค์ GoChek Ultra S24 มันไม่ต้องต่อบลูทูธ ไม่ต้องลงแอปไงล่ะ!", [
                ("ก็ไมค์ GoChek Ultra S24", "ก็ไมค์ GoChek Ultra S24", "c4_1"),
                ("ไม่ต้องต่อบลูทูธ ไม่ต้องลงแอป", "ไม่ต้องต่อบลูทูธ ไม่ต้องลงแอป", "c4_2"),
            ]),
            ("F", "เสียบตัวรับเข้าตูดมือถือปุ๊บ ไฟเขียวติดปั๊บ แถมเสียบสายชาร์จมือถือไปพร้อมกันได้เลย!", [
                ("เสียบตูดมือถือปุ๊บ ไฟเขียวติดปั๊บ", "เสียบตูดมือถือปุ๊บ ไฟเขียวติดปั๊บ", "c5_1"),
                ("แถมเสียบชาร์จมือถือพร้อมกันได้เลย", "แถมเสียบชาร์จมือถือพร้อมกันได้เลย", "c5_2"),
            ]),
            ("M", "รอดตายหวุดหวิด ขอบคุณคนคิดระบบเสียบปุ๊บติดปั๊บจริงๆ ครับ", [
                ("รอดตายหวุดหวิด", "รอดตายหวุดหวิด", "c6_1"),
                ("ขอบคุณระบบเสียบปุ๊บติดปั๊บจริงๆ", "ขอบคุณระบบเสียบปุ๊บติดปั๊บจริงๆ", "c6_2"),
            ]),
            ("M", "ใครอยากได้ไมค์ใช้ง่ายไม่ต้องตั้งค่า กดตะกร้าเหลืองซ้ายล่างเลยครับ", [
                ("ใครอยากได้ไมค์ใช้ง่ายไม่ต้องตั้งค่า", "ใครอยากได้ไมค์ใช้ง่ายไม่ต้องตั้งค่า", "c7_1"),
            ]),
        ],
        "cta_words": [
            ("กดตะกร้าเหลือง", "กดตะกร้าเหลือง", "cart"),
            ("ซ้ายล่างเลยครับ", "ซ้ายล่างเลยครับ", "leftdown"),
        ],
    },
]


def call_gemini_multi_tts(turns: list[tuple], out_raw_wav: Path, key_offset: int = 0):
    api_keys = get_gemini_api_keys()
    lines = []
    for spk, text, _ in turns:
        name = "Haduh" if spk == "F" else "Nasi"
        lines.append(f"{name}: {text}")
    dialogue_str = "\n".join(lines)

    prompt = f"""[Scene: Viral TikTok Sitcom Couple POV in Thailand.
Characters:
- Haduh (Female, cute, bright, high-spirited Southern Thai girlfriend, scolding fast, expressive, playful)
- Nasi (Male, clumsy, flustered, good-natured boyfriend, expressive comedic timing)
Pacing: Snappy, clear pause between each speaker turn.]

Read the following Thai dialogue with expressive acting:

{dialogue_str}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "multiSpeakerVoiceConfig": {
                    "speakerVoiceConfigs": [
                        {
                            "speaker": "Haduh",
                            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}},
                        },
                        {
                            "speaker": "Nasi",
                            "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}},
                        },
                    ]
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
                    with wave.open(str(out_raw_wav), "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(24000)
                        wf.writeframes(pcm_bytes)
                    print(f"  [TTS OK] {out_raw_wav.parent.name} via {model_name}")
                    return
            except Exception as e:
                print(f"  [TTS retry] {model_name} key#{(i + key_offset) % len(api_keys) + 1}: {e}")
                time.sleep(1.5)
    raise RuntimeError(f"Failed TTS for {out_raw_wav}")


def detect_speech_islands(raw_audio: np.ndarray, sr: int, n_turns: int, turn_weights: list[int]) -> list[tuple[float, float]]:
    """Detect all acoustic speech islands in raw_audio and group them into exactly n_turns turn intervals."""
    win = int(0.02 * sr)
    n_wins = len(raw_audio) // win
    frames = raw_audio[: n_wins * win].reshape(n_wins, win).astype(np.float32) / 32768.0
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
            if i + 12 < len(is_speech) and np.any(is_speech[i : i + 12]):
                continue
            in_seg = False
            if (i - s0) * 0.02 >= 0.14:
                islands.append((max(0.0, s0 * 0.02 - 0.02), min(len(raw_audio) / sr, i * 0.02 + 0.03)))
    if in_seg:
        islands.append((max(0.0, s0 * 0.02 - 0.02), len(raw_audio) / sr))

    if len(islands) < n_turns:
        # Fallback: split total active range proportionally
        t_start = islands[0][0] if islands else 0.0
        t_end = islands[-1][1] if islands else len(raw_audio) / sr
        tot_w = sum(turn_weights)
        cur = t_start
        res = []
        for w in turn_weights:
            nxt = cur + (t_end - t_start) * (w / tot_w)
            res.append((round(cur, 3), round(nxt, 3)))
            cur = nxt
        return res

    # If more islands than n_turns, merge adjacent islands with smallest silence gap or best weight match
    # until len(islands) == n_turns
    while len(islands) > n_turns:
        # Compute gaps between consecutive islands, weighted by how small the merged duration is vs target weight
        tot_dur = sum(b - a for a, b in islands)
        tot_w = sum(turn_weights)
        best_idx = 0
        best_score = float("inf")
        for idx in range(len(islands) - 1):
            gap = islands[idx + 1][0] - islands[idx][1]
            merged_dur = islands[idx + 1][1] - islands[idx][0]
            # Approximate target turn index
            target_idx = min(n_turns - 1, int(idx * n_turns / len(islands)))
            expected_dur = tot_dur * (turn_weights[target_idx] / tot_w)
            score = gap * 2.5 + max(0.0, merged_dur - expected_dur * 1.35)
            if score < best_score:
                best_score = score
                best_idx = idx
        islands[best_idx] = (islands[best_idx][0], islands[best_idx + 1][1])
        islands.pop(best_idx + 1)

    return islands


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


def process_clip(spec: dict, clip_idx: int):
    cid = spec["id"]
    clip_dir = HERE / cid
    clip_dir.mkdir(parents=True, exist_ok=True)
    out_vo = STUDIO / "assets" / "clips" / cid / "vo.wav"
    out_vo.parent.mkdir(parents=True, exist_ok=True)

    raw_wav = clip_dir / "raw_gemini_vo.wav"
    turns = spec["turns"]
    # Append CTA words to the last turn's spoken words for alignment
    full_turns = []
    for idx, (spk, tts_line, word_tuples) in enumerate(turns):
        if idx == len(turns) - 1:
            full_turns.append((spk, tts_line, word_tuples + spec["cta_words"]))
        else:
            full_turns.append((spk, tts_line, word_tuples))

    if not raw_wav.exists():
        call_gemini_multi_tts(full_turns, raw_wav, key_offset=clip_idx)

    with wave.open(str(raw_wav), "rb") as wf:
        raw_sr = wf.getframerate()
        raw_audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    turn_weights = [sum(len(w[1].replace(" ", "")) for w in wt) for _, _, wt in full_turns]
    islands = detect_speech_islands(raw_audio, raw_sr, len(full_turns), turn_weights)

    tmp_dir = clip_dir / "_tmp_segs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out_sr = 48000
    tempo = 1.34
    gap_sec = 0.06
    gap_samples = np.zeros(int(gap_sec * out_sr), dtype=np.int16)

    combined_mono = []
    all_words = []
    cur_time = 0.0

    for idx, ((t0, t1), (spk, _, word_tuples)) in enumerate(zip(islands, full_turns)):
        s0 = max(0, int(t0 * raw_sr))
        s1 = min(len(raw_audio), int(t1 * raw_sr))
        chunk = raw_audio[s0:s1]

        in_wav = tmp_dir / f"in_{idx:02d}.wav"
        out_wav = tmp_dir / f"out_{idx:02d}.wav"
        with wave.open(str(in_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(raw_sr)
            wf.writeframes(chunk.tobytes())

        if spk == "F":
            # Aoede is already a bright female voice; lift +1.5 semitones (1.09x) + sweet presence EQ
            pitch = 1.12
            adj_tempo = round(tempo / pitch, 5)
            af = f"asetrate={int(raw_sr * pitch)},aresample={out_sr},atempo={adj_tempo},highpass=f=140,equalizer=f=3500:t=q:w=1.2:g=3.5"
        else:
            af = f"atempo={tempo}"

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

    # Build CLAUSES and SFX
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
        # Situational highlight SFX on product reveal (turn 4) & climax (turn 6) & CTA
        t4_cue = turns[4][2][0][2]
        t6_cue = turns[6][2][0][2]
        res.append(("ding.wav", round(c[t4_cue] + 0.25, 3), 0.6, 0.28))
        res.append(("punch.mp3", round(c[t6_cue] + 0.15, 3), 0.45, 0.32))
        res.append(("cash_register.mp3", round(c["cart"], 3), 0.9, 0.38))
        return res

    # Write initial HTML placeholder so build() can compute cues first
    html_path = STUDIO / "compositions" / f"{cid}.html"
    html_path.write_text("<!-- CAPTIONS:BEGIN --><!-- CAPTIONS:END --><!-- VO:BEGIN --><!-- VO:END --><!-- SFX:BEGIN --><!-- SFX:END -->", encoding="utf-8")
    cues = build(clip_dir, clauses, make_sfx, caption_stop="cart", gaps=[])

    # Compute 6 shot boundaries based on real turn start times
    cut1 = round(cues[turns[1][2][0][2]], 2)
    cut2 = round(cues[turns[2][2][0][2]], 2)
    cut3 = round(cues[turns[4][2][0][2]], 2)
    cut4 = round(cues[turns[5][2][0][2]], 2)
    cut5 = round(cues[turns[6][2][0][2]], 2)
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
    left_in_before = ",\n      ".join(f"#{x} .cap-in::before" for x in left_cap_ids)
    left_after = ",\n      ".join(f"#{x}::after" for x in left_cap_ids)

    right_sel = ",\n      ".join(f"#{x}" for x in right_cap_ids)
    right_before = ",\n      ".join(f"#{x}::before" for x in right_cap_ids)
    right_in = ",\n      ".join(f"#{x} .cap-in" for x in right_cap_ids)
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
      .scene-sub {{
        top: 175px;
        font-size: 52px;
        color: var(--paper);
      }}
      .scene-title {{
        top: 245px;
        font-size: 92px;
        line-height: 1.15;
      }}

      /* AUTHENTIC LINE MESSENGER CHAT BUBBLES AT BOTTOM */
      .cap {{
        display: flex !important;
        left: 44px !important;
        right: 44px !important;
        top: 1310px !important;
        align-items: flex-start !important;
        text-shadow: none !important;
      }}
      .cap-in {{
        position: relative;
        max-width: 680px !important;
        padding: 24px 32px !important;
        font-size: 48px !important;
        font-weight: 700;
        line-height: 1.34 !important;
        color: #111111 !important;
        text-shadow: none !important;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
      }}
      .cap-in .w {{
        color: #111111;
        text-shadow: none !important;
        padding: 0 3px;
        border-radius: 10px;
      }}

      /* FEMALE (ฮาดุหหห) — LEFT INCOMING LINE BUBBLE */
      {left_sel} {{
        justify-content: flex-start !important;
      }}
      {left_before} {{
        content: "ฮ";
        flex: 0 0 78px;
        width: 78px;
        height: 78px;
        border-radius: 50%;
        background: linear-gradient(135deg, #ff9eb5, #ff5277);
        color: #ffffff;
        font-size: 42px;
        font-weight: 700;
        line-height: 78px;
        text-align: center;
        margin-right: 18px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
      }}
      {left_in} {{
        background: #ffffff;
        border-radius: 6px 34px 34px 34px;
        text-align: left !important;
      }}
      {left_in_before} {{
        content: "ฮาดุหหห";
        position: absolute;
        top: -44px;
        left: 4px;
        font-size: 32px;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}
      {left_after} {{
        content: "18:05";
        align-self: flex-end;
        margin-left: 14px;
        margin-bottom: 6px;
        font-size: 26px;
        color: rgba(255, 255, 255, 0.92);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}

      /* MALE (นาซิ) — RIGHT OUTGOING LINE GREEN BUBBLE */
      {right_sel} {{
        justify-content: flex-end !important;
      }}
      {right_before} {{
        content: "อ่านแล้ว\\A 18:05";
        white-space: pre;
        align-self: flex-end;
        margin-right: 14px;
        margin-bottom: 6px;
        font-size: 25px;
        line-height: 1.2;
        text-align: right;
        color: rgba(255, 255, 255, 0.95);
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.85);
      }}
      {right_in} {{
        background: #8de07a;
        border-radius: 34px 6px 34px 34px;
        text-align: left !important;
      }}
      {right_in_before} {{
        content: "นาซิ";
        position: absolute;
        top: -44px;
        right: 4px;
        font-size: 32px;
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 3px 10px rgba(0, 0, 0, 0.85);
        white-space: nowrap;
      }}
      {right_after} {{
        content: "น";
        flex: 0 0 78px;
        width: 78px;
        height: 78px;
        border-radius: 50%;
        background: linear-gradient(135deg, #60a5fa, #2563eb);
        color: #ffffff;
        font-size: 42px;
        font-weight: 700;
        line-height: 78px;
        text-align: center;
        margin-left: 18px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
      }}

      /* CLEAN FINAL CTA (No Cluttered Boxes) */
      #cta-1 {{
        top: 340px;
        font-size: 112px;
      }}
      #cta-sub {{
        top: 475px;
        font-size: 68px;
        color: var(--paper);
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
        font-size: 104px;
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

      <!-- CLEAN TOP HEADLINES -->
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
        <div class="t center" id="cta-sub">GoChek Ultra S24 • ของแท้ประกันศูนย์</div>
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
      pop("#t-proof", {shots[1][0]}, {{ scale: 1.4, rotation: -2 }}, "power4.out", 0.28);
      pop("#t-rap", {shots[2][0]}, {{ scale: 1.4, rotation: 2 }}, "power4.out", 0.28);
      pop("#t-hero", {shots[3][0]}, {{ y: -30, rotation: 0 }}, "power3.out", 0.28);
      pop("#t-steal", {shots[4][0]}, {{ scale: 1.6, rotation: -3 }}, "back.out(2.2)", 0.28);
      pop("#t-payoff", {shots[5][0]}, {{ y: -30, rotation: 0 }}, "power3.out", 0.28);

      flash(T.cart, 0.35, 0.2);
      pop("#cta-1", T.cart, {{ scale: 1.6, rotation: 0 }}, "power4.out", 0.28);
      pop("#cta-sub", T.cart + 0.1, {{ y: 24, rotation: 0 }}, "expo.out", 0.25);
      const sl = HF.dash($("#k-shaft"));
      const hl = HF.dash($("#k-head"));
      tl.fromTo("#k-shaft", {{ strokeDashoffset: sl }}, {{ strokeDashoffset: 0, duration: 0.35, ease: "power2.inOut" }}, T.cart + 0.12);
      tl.fromTo("#k-head", {{ strokeDashoffset: hl }}, {{ strokeDashoffset: 0, duration: 0.14, ease: "power2.out" }}, T.cart + 0.44);
      pop("#cta-tag", T.cart + 0.22, {{ x: -60, rotation: 0 }}, "expo.out", 0.25);

      const leftIds = new Set([{left_js_list}]);
      document.querySelectorAll(".cap").forEach((cap) => {{
        const t0 = Number(cap.dataset.start);
        const fromX = leftIds.has(cap.id) ? -48 : 48;
        tl.fromTo(
          cap,
          {{ x: fromX, y: 28, scale: 0.9, opacity: 0 }},
          {{ x: 0, y: 0, scale: 1, opacity: 1, duration: 0.26, ease: "back.out(1.8)" }},
          t0
        );
        const words = [...cap.querySelectorAll(".w")];
        words.forEach((w, i) => {{
          const s = Number(w.dataset.s);
          tl.set(w, {{ color: "#d90429", backgroundColor: "rgba(255, 230, 0, 0.65)" }}, s);
          tl.fromTo(
            w,
            {{ scale: 1 }},
            {{ scale: 1.08, duration: 0.08, ease: "power2.out", yoyo: true, repeat: 1, immediateRender: false }},
            s
          );
          if (i + 1 < words.length) {{
            tl.set(w, {{ color: "#111111", backgroundColor: "transparent" }}, Number(words[i + 1].dataset.s));
          }}
        }});
      }});

      window.__timelines["{cid}"] = tl;
    </script>
  </body>
</html>
"""
    html_path.write_text(html_content, encoding="utf-8")
    # Re-run build() to inject CAPTIONS, VO, and SFX into the full HTML
    build(clip_dir, clauses, make_sfx, caption_stop="cart", gaps=[])


def main():
    for idx, spec in enumerate(CLIPS_SPEC):
        print(f"=== Building Clip {idx + 1}/5: {spec['id']} ===")
        process_clip(spec, idx)
    print("ALL 5 POV CLIPS BUILT SUCCESSFULLY!")


if __name__ == "__main__":
    main()
