import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen, Rocket, Layers, Scissors, FolderDown, Palette, BarChart3, Settings,
  PlayCircle, CheckCircle2, AlertTriangle, ChevronDown, ArrowRight, Clock,
  FolderOpen, Sparkles, FileText, Music, MessageSquareText,
  MonitorPlay, CircleHelp, Search, Circle, Bot, Cpu,
} from 'lucide-react';
import { PageHeader } from './ui';

// ── เมนูที่ 8: คู่มือใช้งานในโปรแกรม ──
// อธิบายโฟลว์หลัก + วิธีใช้ละเอียดเมนูเสริม Gadget Media และทุกเมนู 0-7 ในหน้าเดียว เน้นอ่านง่าย
const MENU_GUIDE = [
  { id: 'flow', no: '1', icon: Rocket, color: 'text-rose-400', chip: 'bg-rose-500/10 text-rose-300 border-rose-500/30' },
  { id: 'tracker', no: '2', icon: Layers, color: 'text-cyan-300', chip: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30' },
  { id: 'editor', no: '3', icon: Scissors, color: 'text-purple-400', chip: 'bg-purple-500/10 text-purple-300 border-purple-500/30' },
  { id: 'gallery', no: '4', icon: FolderDown, color: 'text-emerald-400', chip: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' },
  { id: 'assets', no: '5', icon: Palette, color: 'text-amber-400', chip: 'bg-amber-500/10 text-amber-300 border-amber-500/30' },
  { id: 'analytics', no: '6', icon: BarChart3, color: 'text-cyan-300', chip: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30' },
  { id: 'settings', no: '7', icon: Settings, color: 'text-slate-300', chip: 'bg-slate-500/10 text-slate-300 border-slate-500/30' },
];

const FLOW_STEPS = [
  { no: '1', title: 'เตรียมสินค้า', desc: 'ใส่ลิงก์หรือชื่อสินค้า ดึงชื่อ จุดขาย และสเปก', menu: 'เมนู 1', tab: 'flow', icon: Rocket, grad: 'from-rose-500/25 to-rose-500/5' },
  { no: '2', title: 'สร้างสคริปต์', desc: 'AI เขียน Hook 3 วิ + บทรีวิว + CTA ปิดท้าย', menu: 'เมนู 1', tab: 'flow', icon: FileText, grad: 'from-rose-500/25 to-orange-500/5' },
  { no: '3', title: 'เสียงพากย์', desc: 'Gemini Flash TTS เสียงไทยคมชัด (ค่าเริ่มต้น Fenrir ชายสตรองพรีเมียม) ฟังตัวอย่างก่อนใช้จริง', menu: 'เมนู 1', tab: 'flow', icon: Music, grad: 'from-amber-500/25 to-amber-500/5' },
  { no: '4', title: 'ซับไตเติล', desc: 'ตัดคำ Micro-Burst 2-4 คำ ไฮไลต์คำขายสีเหลืองนีออน', menu: 'เมนู 3', tab: 'editor', icon: MessageSquareText, grad: 'from-purple-500/25 to-purple-500/5' },
  { no: '5', title: 'ตัดต่อ', desc: 'ไทม์ไลน์หลายแทร็ก ใส่ B-roll สติกเกอร์ เอฟเฟกต์', menu: 'เมนู 3', tab: 'editor', icon: Scissors, grad: 'from-purple-500/25 to-cyan-500/5' },
  { no: '6', title: 'เรนเดอร์', desc: 'Export 1080x1920 30FPS H.264 พร้อมปก 9:16', menu: 'เมนู 4', tab: 'gallery', icon: MonitorPlay, grad: 'from-emerald-500/25 to-emerald-500/5' },
  { no: '7', title: 'โพสต์', desc: 'ส่งเข้ามือถือหรือ Auto-Post ขึ้น TikTok พร้อมตะกร้า', menu: 'เมนู 4', tab: 'gallery', icon: PlayCircle, grad: 'from-cyan-500/25 to-cyan-500/5' },
];

const TOC = [
  { href: 'ug-flow', label: 'โฟลว์หลัก 7 ขั้น' },
  { href: 'ug-menus', label: 'วิธีใช้เมนู 0-7 + Gadget' },
  { href: 'ug-quickstart', label: 'คลิปแรกใน 10 นาที' },
  { href: 'ug-status', label: 'สถานะคลิป 4 เฟส' },
  { href: 'ug-folders', label: 'โฟลเดอร์ 00-06' },
  { href: 'ug-checklist', label: 'เช็กลิสต์ก่อนโพสต์' },
  { href: 'ug-trouble', label: 'แก้ปัญหาเบื้องต้น' },
  { href: 'ug-faq', label: 'คำถามพบบ่อย' },
];

const FAQS = [
  { q: 'เปิดโปรแกรมอย่างไร?', a: 'ดับเบิลคลิก start_app.bat ระบบจะเปิด Backend (พอร์ต 8000) และ Frontend (พอร์ต 5173) พร้อมเปิดเบราว์เซอร์ให้อัตโนมัติ ถ้าเปิดเองให้รัน python scripts/api_server.py อีกหน้าต่างรัน cd frontend แล้ว npm run dev' },
  { q: 'เสียงพากย์ไม่ออกต้องทำอย่างไร?', a: 'ค่าเริ่มต้นของระบบคือ Gemini Flash TTS (เสียง Fenrir ชายสตรอง คมเข้ม สไตล์ commercial_premium) ซึ่งต้องต่อเน็ตและตั้ง API Key ให้ครบ ลองกดฟังตัวอย่างเสียงก่อน ถ้าขึ้น Error ลิมิตหรือ quota ระบบจะไม่สลับไป Edge-TTS ให้เอง ให้รอคูลดาวน์แล้วลองใหม่ หรือเลือก Edge-TTS เองในหน้าตัดต่อ พร้อมตรวจระดับเสียง Voice = 1.0 ที่เมนู 3' },
  { q: 'เมนู 0 ผู้ช่วยโปรดิวเซอร์ใช้ทำอะไร?', a: 'เป็นศูนย์บัญชาการรายวัน ดู Daily Mission ว่าควรทำคลิปไหนต่อ ใช้ Pacing Calculator ดูว่าต้องทำอีกกี่คลิปถึงทันเป้า เก็บไอเดียและเรฟลง Idea Vault แล้วกดเพิ่มลง Playbook ได้ในคลิกเดียว ส่งภาพเรฟให้ Gemini Vision วิเคราะห์เป็นสคริปต์ และจด Producer Notes ที่ปักหมุด/แก้ไขได้ โดยซิงก์กับ Quick Ref หน้าโรงถ่าย' },
  { q: 'สไตล์การตัดต่อกับป้ายฮุกเลือกอย่างไร?', a: 'ที่เมนู 1 มีสไตล์การตัดต่อ 10 แบบ (Viral Punch, Clean Tech Review, Tech Product Showcase, Smooth Showcase, Premium Minimal, Flash Deal, Pain Punch, Tech Comparison, Smart Hack, Niche Focus) โดยแต่ละสไตล์ผูกกับป้ายฮุกสีและอนิเมชันแบบ 1 ต่อ 1 เลือกสไตล์แล้วระบบตั้งป้ายฮุกให้อัตโนมัติ พร้อมโชว์ว่าสินค้านี้เคยใช้สไตล์ไหนไปแล้ว' },
  { q: 'Gadget Media ต่างจากโฟลว์ สินค้า → คลิป อย่างไร?', a: 'Gadget Media เป็นเส้นทางงานแยกสำหรับทำวิดีโอสินค้าแกดเจ็ตแบบเจาะลึก 1 สินค้า 1 โปรเจกต์ โดยเดิน 6 ขั้น Brief → Sources → Evidence → Story → Cut → Review และมีไทม์ไลน์กับ Render ของตัวเอง (ไม่ไหลไปปนกับ Global Editor) ส่วนเมนู 1 สินค้า → คลิป เหมาะกับงานรีวิวสั้นที่ใช้ Content Matrix หลายมุมและส่งเข้า Editor รวม' },
  { q: 'TypeSafe AI ใช้ทำอะไร?', a: 'TypeSafe System One (Jev) ช่วยจัดอันดับ Hook ตามคะแนนตรึงคนดู 3 วินาทีแรก (Retention Score) ในหน้า Script Lab และจับคู่ B-roll ให้ตรงกับสิ่งที่เสียงพากย์พูดตลอดทั้งประโยค (Strict Topic Hold) โดยไม่ให้ภาพสลับหนีก่อนพูดจบ ดูสถานะการเชื่อมต่อได้ที่เมนู 7 ตั้งค่าระบบ' },
  { q: 'คีย์ลัดสำคัญในหน้าตัดต่อ (Editor) มีอะไรบ้าง?', a: 'Spacebar เล่น/หยุด, S ตัดแบ่งคลิป, N สลับเปิด/ปิดแม่เหล็ก Magnetic Snap, M สลับโหมดพรีวิว Cutout (ปกติ / ตารางหมากรุก / มาสก์), J/K/L ถอยหลัง/หยุด/เดินหน้า, Ctrl+Z เลิกทำ, Ctrl+S บันทึก และกด ? เพื่อเปิดดูคีย์ลัดทั้งหมด' },
  { q: 'เส้นไกด์และกึ่งกลางจอ Smart Guides ทำงานอย่างไร?', a: 'เมื่อลากสติกเกอร์ ข้อความ หรือฮุกเข้าใกล้กึ่งกลาง Canvas 50% ระบบจะแสดงเส้นไกด์สีฟ้า Crosshair ทั้งแนวตั้งและแนวนอน พร้อม Badge 🎯 กึ่งกลางจอ (Center 50%) ช่วยให้จัดวางคอนเทนต์ได้ตรงกึ่งกลาง Safe Zone 9:16 พอดี' },
  { q: 'ซับขึ้นสระลอยหรือวรรณยุกต์ซ้อน?', a: 'ระบบตัดคำด้วย pythainlp และล็อก Safe Zone ล่าง 420px ไว้แล้ว ถ้ายังเพี้ยนให้ย่อ Burst เหลือ 2-3 คำต่อบรรทัด อย่าใส่จุดไข่ปลา ... ในบทพูดเพราะจะหลุดขึ้นจอ' },
  { q: 'เรนเดอร์นานหรือค้าง?', a: 'ไฟล์ Draft ใช้ 720p ทดสอบก่อน ไฟล์จริงค่อยเรนเดอร์ 1080x1920 ปิดโปรแกรมตัดต่ออื่นเพื่อคืนแรม ตรวจพื้นที่ดิสก์ในเมนู 6 แท็บ Storage ถ้าแคช CapCut บวมให้กด Safe Purge' },
  { q: 'คลิปอยู่เฟสไหนดูที่ไหน?', a: 'ดูที่เมนู 2 แทร็กเกอร์ 4 เฟส: scripted (มีไอเดีย) → in_production (มีโปรเจกต์ในไทม์ไลน์) → rendered (มี MP4 ใน 04_Exports) → posted (โพสต์ขึ้น TikTok แล้ว) สถานะเปลี่ยนตามงานจริงเท่านั้น' },
  { q: 'เอาคลิปเข้ามือถืออย่างไร?', a: 'เปิดเมนู 4 Export Gallery กดปุ่มแชร์เข้ามือถือแล้วสแกน QR ด้วยมือถือวง Wi-Fi เดียวกัน หรือกดปุ่มสแกน QR มือถือในแถบเมนูล่าง' },
];
const MENU_DETAIL = [
  { id: 'gadget', title: 'Gadget Media', sub: 'Product Studio 6 ขั้น + Campaign และ Analytics', points: ['Product Studio ทำงานทีละสินค้า: 1 สินค้า = 1 โปรเจกต์วิดีโอ = 1 มาสเตอร์ที่อนุมัติแล้ว', 'เดินครบ 6 ขั้น Brief (สินค้าและคนดู) → Sources (ไฟล์และสิทธิ์) → Evidence (Claim และหลักฐาน) → Story (เรื่องเล่า 45-60 วิ) → Cut (EDL และ Timeline) → Review (ตรวจ Render อนุมัติ) ขั้นถัดไปจะปลดล็อกเมื่อบันทึกขั้นก่อนหน้าเสร็จ', 'Sources บังคับระบุที่มาและสิทธิ์ของไฟล์ (ถ่ายเอง / แบรนด์อนุญาต / แหล่งอ้างอิง) ก่อนนำมาตัดต่อ', 'Evidence ผูก Claim กับหลักฐาน เพื่อไม่ให้พูดเกินจริงและตรวจย้อนได้', 'Quality Inspector ตรวจไฟล์ Render ก่อนกดอนุมัติเป็น Approved Master', 'แท็บ Campaign และ Analytics วางแผนสล็อตคอนเทนต์ ติดตามความพร้อม และดูผลของแต่ละแคมเปญ'], tip: 'งาน Gadget Media มีไทม์ไลน์และ Render แยกในตัว ไม่ไหลไปปนกับ Global Editor (เมนู 3)' },
  { id: 'producer', title: 'ผู้ช่วยโปรดิวเซอร์', sub: 'ศูนย์บัญชาการรายวัน ไอเดีย เรฟ และโน้ต', points: ['เปิดมาเจอ Daily Mission กับ Spotlight งานที่ควรทำต่อทันที', 'Pacing Calculator บอกว่าต้องทำอีกกี่คลิปถึงทันเป้าที่ตั้งไว้', 'Idea & Ref Vault เก็บไอเดียกับภาพเรฟเร็ว แล้วกดเพิ่มลง Playbook ได้ในคลิกเดียว', 'ส่งภาพเรฟให้ Gemini Vision วิเคราะห์มุมกล้องและอารมณ์ภาพ แล้วสังเคราะห์เป็นสคริปต์ 9:16', 'Producer Notes จด เติม tag ปักหมุด และแก้ไขได้ ซิงก์กับ Quick Ref หน้าโรงถ่าย'], tip: 'เปิดเมนูนี้ก่อนเริ่มงานทุกวัน จะรู้ทันทีว่าควรทำคลิปไหนต่อ' },
  { id: 'flow', title: 'สินค้า → คลิป', sub: 'ดึงสินค้า สร้างมุมขายและ Hook ไวรัล', points: ['วางลิงก์สินค้า ระบบดึงชื่อ จุดขาย และสเปกอัตโนมัติ', 'AI แตกมุมขายหลายมุม เลือกมุมแล้วกดสร้างสคริปต์ Hook 3 วินาที + บทรีวิว + CTA', 'เลือกสไตล์การตัดต่อ 10 แบบ ระบบผูกป้ายฮุกสีและอนิเมชันให้อัตโนมัติ พร้อมโชว์สไตล์ที่เคยใช้แล้ว', 'กดฟังเสียงพากย์ตัวอย่าง เสียงเริ่มต้นคือ Gemini Flash TTS (Fenrir) หรือจะเลือก Edge-TTS Premwadee/Niwat ก็ได้', 'สร้างแผนถ่าย (Shot List) ดูมุมกล้องตามบททีละซีน', 'ปุ่มส่งตัดต่อ เปิดโปรเจกต์ใหม่ในเมนู 3 ทันที'], tip: 'ชื่อแบรนด์และรุ่นคงภาษาอังกฤษเสมอ เช่น Logitech Wave Keys, Bluetooth, USB-C' },
  { id: 'tracker', title: 'แทร็กเกอร์ 4 เฟส', sub: 'ติดตามสถานะคลิปตั้งแต่สคริปต์จนโพสต์', points: ['การ์ดแต่ละใบคือหนึ่งมุมขายของสินค้า เห็นเฟสปัจจุบันชัดเจน', 'กดดูสคริปต์ แผนถ่าย หรือส่งต่อเข้า Editor ได้จากการ์ด', 'คิวโพสต์หลายวันตั้งค่าได้ตั้งแต่ 09:00 / 12:30 / 16:00 / 19:00 / 21:30 และเพิ่มช่วงพิเศษรายวันได้', 'พอกดโพสต์สำเร็จการ์ดย้ายไปเฟส posted เอง'], tip: 'สถานะเปลี่ยนตามงานจริงเท่านั้น ไม่มีปุ่มลัดข้ามเฟส' },
  { id: 'editor', title: 'ตัดต่อ & สร้างคลิป', sub: 'ไทม์ไลน์หลายแทร็ก พรีวิวตรงไฟล์จริง', points: ['เลเยอร์วิดีโอ ซับ สติกเกอร์ เสียง แยกแทร็ก ลาก trim split ได้', 'ซับ Micro-Burst 2-4 คำ ไฮไลต์คำขายอัตโนมัติ อยู่ใน Safe Zone และมีซับสองภาษาที่ตรงกับพรีวิว', 'ป้าย Hook พาดหัวค่าเริ่มต้น 5 วินาที ปรับเวลาได้ 1-8 วิ', 'ตัวเลือกโปรเจกต์มีแท็บกรองอัจฉริยะ [ กำลังตัดต่อ ] / [ ตัดเสร็จแล้ว ] / [ ทั้งหมด ] เปิดมาเริ่มที่ กำลังตัดต่อ', 'Asset Panel โหลดภาพตัวอย่างเป็นคิว ไม่ค้างเมื่อมีคลิปเยอะ และพรีวิวอนิเมชันทันทีเมื่อ hover การ์ดเทมเพลตข้อความ', 'ตัดพื้นหลังหรือแยกตัวสินค้า (Background Isolation) ได้จากในตัว Editor สลับโหมดตรวจ Cutout Mask (ปกติ / ตารางหมากรุก / มาสก์ขาวดำ) ด้วยปุ่ม M', 'ระบบ Magnetic Snap & Smart Guides (ปุ่ม N) ดูดหัวอ่านและขอบคลิป พร้อมเส้นไกด์ Crosshair และ Badge 🎯 กึ่งกลางจอ 50% เมื่อลากจัดวาง', 'ปุ่ม Reroll เปลี่ยนเฉพาะเสียง ซับ BGM หรือวิดีโอโดยไม่เริ่มใหม่', 'ลายน้ำช่อง (@rizanntry) ติดถาวรทั้งในพรีวิวและไฟล์เรนเดอร์ ปิดไม่ได้', 'กดเรนเดอร์ ไฟล์จริง 1080x1920 30FPS ไปเมนู 4 อัตโนมัติ'], tip: 'ภาพพรีวิวกับไฟล์เรนเดอร์ใช้ค่าชุดเดียวกัน เห็นอย่างไรได้ไฟล์อย่างนั้น' },
  { id: 'gallery', title: 'Export Gallery', sub: 'คลังคลิปพร้อมโพสต์และส่งเข้ามือถือ', points: ['คลิปเรนเดอร์เสร็จรวมที่นี่ พร้อมปก 9:16 และแคปชัน', 'กดแชร์เข้ามือถือสแกน QR ดาวน์โหลดไฟล์ MP4', 'กดทำเครื่องหมายโพสต์แล้ว คลิปย้ายไปโฟลเดอร์ Posted', 'เปิดด้วย CapCut PC ต่อเมื่อต้องการแต่งเพิ่ม'], tip: 'ตั้งชื่อไฟล์ YYYYMMDD_ชื่อสินค้า_hookสั้น_vN.mp4 หาไฟล์ง่าย' },
  { id: 'assets', title: 'Media Assets Hub', sub: 'คลังเสียง ฟอนต์ สติกเกอร์ส่วนกลาง', points: ['BGM เพลงประกอบ SFX Whoosh Ding Pop กดฟังก่อนใช้', 'ฟอนต์ไทยมาตรฐาน Kanit Prompt IBM Plex Sans Thai', 'ป้ายรีวิว 3D 6 แบบ PROS CONS WARNING PRO TIP SCORE VERDICT', 'อัปโหลดไฟล์ใหม่หรือลบไฟล์ขยะได้จากหน้านี้'], tip: 'ไฟล์ใน 01_Raw และ 02_Assets คือต้นฉบับ ห้ามลบโดยไม่ยืนยัน' },
  { id: 'analytics', title: 'สถิติ & วิเคราะห์รวม', sub: 'การผลิต ผลงาน TikTok โทเคน พื้นที่ สุขภาพสินค้า', points: ['แท็บ Production ดู Funnel 4 เฟส จุดคอขวด เวลาเฉลี่ย', 'แท็บ Performance ดูผลงาน TikTok ที่ดึงมา แถวไหนไม่เจอคู่กดจับคู่ manual และแจ้งเตือนคลิปปัง 10k+', 'แท็บ Tokens ดูการใช้ AI แยก In/Out/Think รายวัน พร้อมแจ้งเตือนลิมิต/quota', 'แท็บ Storage ดูขนาดโฟลเดอร์ 01-06 และปุ่ม Safe Purge ล้างแคช', 'แท็บ Inventory ดูสินค้าตัวไหนขาดรูป ขาดคลิป พร้อมทำคลิป'], tip: 'Safe Purge ล้างเฉพาะแคช ไม่แตะไฟล์ต้นฉบับ' },
  { id: 'settings', title: 'ตั้งค่าระบบ', sub: 'จอ ฟอนต์ โฟลเดอร์ และความปลอดภัย', points: ['แท็บการแสดงผล ปรับขนาด UI และฟอนต์ไทย 10 แบบ', 'แท็บโฟลเดอร์ เปิดโฟลเดอร์ 00-06 และ CapCut Drafts ได้ทันที', 'แท็บระบบ ตรวจ FFmpeg Gemini Engine และการเชื่อม CapCut', 'สวิตช์ TikTok Auto-Post ปิดเป็นค่าเริ่มต้น เปิดเมื่อพร้อมเท่านั้น'], tip: 'คีย์ลัดกด ? ดูชีตคีย์ลัดทั้งหมด' },
];
const CHECKLIST = [
  'Hook 3 วิแรกหยุดนิ้วได้ ภาพและเสียงสะดุดตาทันที',
  'ซับไทยถูกต้อง ไม่มีสระลอย ไม่ใส่จุดไข่ปลาในบทพูด',
  'พิกัดตะกร้าขึ้นชัดบนจอ และไม่มีราคา ส่วนลด หรือโปรโมชันในคลิป',
  'เสียง Voice ดังชัด BGM และ SFX ไม่กลบเสียงพูด',
  'ข้อความและสติกเกอร์อยู่ใน Safe Zone ไม่โดนปุ่ม TikTok บัง',
  'ปก 9:16 ตัวหนังสืออ่านง่าย สีสะดุดตา',
];
const CHECKLIST_KEY = 'omnicut_guide_checklist_v1';

const TROUBLES = [
  { t: 'เสียงพากย์ไม่ออก', d: 'Gemini TTS ต้องต่อเน็ตและมี API Key ถ้าขึ้นลิมิตให้รอคูลดาวน์หรือเลือก Edge-TTS', tab: 'flow', label: 'เปิดเมนู 1' },
  { t: 'ซับเพี้ยนสระลอย', d: 'ย่อ Burst เหลือ 2-3 คำ อย่าใส่จุดไข่ปลาในบทพูด', tab: 'editor', label: 'เปิดเมนู 3' },
  { t: 'เรนเดอร์ค้าง', d: 'ทดสอบด้วย Draft 720p ก่อน ดูพื้นที่ดิสก์ที่เมนู 6', tab: 'analytics', label: 'เปิดเมนู 6' },
  { t: 'หาไฟล์ไม่เจอ', d: 'คลิปเสร็จอยู่ 04_Exports ปกอยู่ 05_Covers เปิดจากเมนู 7', tab: 'settings', label: 'เปิดเมนู 7' },
];
// ── จบข้อมูล ──
export default function UserGuide({ onNavigate }) {
  const [openFaq, setOpenFaq] = useState([0]);
  const [faqQuery, setFaqQuery] = useState('');
  const [expandedMenus, setExpandedMenus] = useState({});
  const [activeSection, setActiveSection] = useState('ug-flow');
  const [checked, setChecked] = useState(() => {
    try {
      const raw = localStorage.getItem(CHECKLIST_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr.filter((i) => Number.isInteger(i) && i >= 0 && i < CHECKLIST.length) : [];
    } catch { return []; }
  });
  const go = (tab) => { if (onNavigate) onNavigate(tab); };
  const scrollTo = (id) => { try { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch {} };
  // Scrollspy: ไฮไลต์หัวข้อที่อ่านอยู่ตามตำแหน่งเลื่อนจริง
  useEffect(() => {
    const ids = TOC.map((t) => t.href);
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => { if (e.isIntersecting) setActiveSection(e.target.id); });
      },
      { rootMargin: '-30% 0px -60% 0px', threshold: 0 }
    );
    ids.forEach((id) => { const el = document.getElementById(id); if (el) observer.observe(el); });
    return () => observer.disconnect();
  }, []);
  const toggleFaq = (i) => {
    setOpenFaq((prev) => (prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i]));
  };
  const toggleCheck = (i) => {
    setChecked((prev) => {
      const next = prev.includes(i) ? prev.filter((x) => x !== i) : [...prev, i].sort((a, b) => a - b);
      try { localStorage.setItem(CHECKLIST_KEY, JSON.stringify(next)); } catch {}
      return next;
    });
  };
  const resetChecklist = () => {
    setChecked([]);
    try { localStorage.removeItem(CHECKLIST_KEY); } catch {}
  };
  const filteredFaqs = useMemo(() => {
    const q = faqQuery.trim();
    if (!q) return FAQS.map((f, i) => ({ ...f, idx: i }));
    return FAQS.map((f, i) => ({ ...f, idx: i })).filter((f) => (f.q + ' ' + f.a).includes(q));
  }, [faqQuery]);
  const visibleFaqIdx = useMemo(() => new Set(filteredFaqs.map((f) => f.idx)), [filteredFaqs]);
  return (
    <div className="space-y-4 sm:space-y-5 animate-fadeIn pb-24 md:pb-12 max-w-[2200px] mx-auto">
      <PageHeader
        icon={BookOpen}
        eyebrow="User Guide"
        title="คู่มือใช้งาน OmniCut Pro Studio"
        badges={<span className="text-[10px] font-bold px-2 py-0.5 rounded-full border bg-emerald-500/10 text-emerald-300 border-emerald-500/30">อ่านจบทำคลิปแรกได้ทันที</span>}
        actions={(<button onClick={() => go('flow')} className="min-h-[42px] flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white text-xs font-bold cursor-pointer active:scale-95">เริ่มสร้างคลิปแรก<ArrowRight className="w-3.5 h-3.5" /></button>)}
      />
      {/* ── สารบัญลอย: ติดบน + scrollspy ── */}
      <nav className="sticky top-[52px] sm:top-[56px] z-10 bg-[#080B11]/95 backdrop-blur-xl border border-white/[0.08] rounded-2xl px-2.5 py-2 shadow-lg">
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
          {TOC.map((t) => {
            const active = activeSection === t.href;
            return (<button key={t.href} onClick={() => scrollTo(t.href)} className={`flex-shrink-0 px-3.5 py-2 min-h-[38px] flex items-center rounded-full border text-xs font-bold cursor-pointer whitespace-nowrap transition-colors active:scale-95 ${active ? 'bg-[#25F4EE]/15 border-[#25F4EE]/50 text-[#25F4EE]' : 'bg-white/[0.04] hover:bg-[#25F4EE]/15 border-white/[0.08] hover:border-[#25F4EE]/40 text-slate-300 hover:text-[#25F4EE]'}`}>{t.label}</button>);
          })}
        </div>
      </nav>
      <section id="ug-flow" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg scroll-mt-20">
        <div className="flex items-center gap-2.5 mb-1">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#25F4EE]/20 to-[#FE2C55]/20 border border-white/[0.1] flex items-center justify-center"><Sparkles className="w-4 h-4 text-[#25F4EE]" /></div>
          <div><h2 className="text-sm sm:text-base font-black text-white">โฟลว์การทำงานหลัก 7 ขั้น</h2><p className="text-[11px] sm:text-xs text-slate-400">จากสินค้าหนึ่งชิ้น กลายเป็นคลิปพร้อมโพสต์ กดที่การ์ดเพื่อกระโดดไปเมนูนั้นได้เลย</p></div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 2xl:grid-cols-7 gap-2 mt-3 items-start">
          {FLOW_STEPS.map((s) => { const Icon = s.icon; return (
            <div key={s.no} className={`relative rounded-2xl border border-white/[0.08] bg-gradient-to-b ${s.grad} p-3 flex flex-col gap-1 min-h-[108px]`}>
              <div className="flex items-center justify-between"><span className="w-6 h-6 rounded-full bg-black/50 border border-white/[0.15] text-[#25F4EE] text-xs font-black flex items-center justify-center font-mono">{s.no}</span><Icon className="w-5 h-5 text-white/70" /></div>
              <div className="text-[13px] font-black text-white">{s.title}</div>
              <div className="text-[11px] text-slate-300 leading-snug flex-1">{s.desc}</div>
              <button onClick={() => go(s.tab)} title={`เปิด${s.menu}ใช้งานจริง`} className="mt-1 inline-flex items-center gap-1 text-[10px] font-bold text-[#25F4EE] hover:text-white cursor-pointer self-start transition-colors">{s.menu}<ArrowRight className="w-3 h-3" /></button>
            </div> ); })}
        </div>
        <div className="mt-3 flex items-start gap-2 p-3 rounded-xl bg-amber-500/[0.07] border border-amber-500/25"><AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" /><p className="text-[11px] sm:text-xs text-slate-300 leading-relaxed">จำง่าย เริ่มวันดูเมนู 0 สินค้าเข้าเมนู 1 งานค้างดูเมนู 2 ตัดต่อเรนเดอร์ที่เมนู 3 คลิปเสร็จรวมที่เมนู 4 ของส่วนกลางอยู่เมนู 5 ตัวเลขรวมอยู่เมนู 6 มีปัญหามาเมนู 7 ตั้งค่า</p></div>
        <div className="mt-2 flex items-start gap-2 p-3 rounded-xl bg-cyan-500/[0.07] border border-cyan-500/25"><Cpu className="w-4 h-4 text-cyan-300 flex-shrink-0 mt-0.5" /><p className="text-[11px] sm:text-xs text-slate-300 leading-relaxed">งาน Gadget Media ไม่ได้ใช้โฟลว์นี้ ให้เข้าเมนู <span className="font-bold text-cyan-200">Gadget Media</span> แล้วทำตาม 6 ขั้น Brief → Sources → Evidence → Story → Cut → Review โดย 1 สินค้าได้ 1 มาสเตอร์ที่อนุมัติแล้ว</p></div>
      </section>
      <section id="ug-menus" className="scroll-mt-20">
        <h2 className="text-sm sm:text-base font-black text-white px-1">วิธีใช้ละเอียดทุกเมนู กดชื่อเมนูเพื่อกระโดดไปใช้งานจริง</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 2xl:grid-cols-3 gap-2.5 mt-2.5 items-start">
        {MENU_DETAIL.map((m) => { const meta = MENU_GUIDE.find((g) => g.id === m.id); const Icon = meta.icon; const expanded = !!expandedMenus[m.id]; const visible = expanded ? m.points : m.points.slice(0, 3); return (
          <article key={m.id} className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg min-w-0">
            <button onClick={() => go(m.id)} className="w-full flex items-center gap-2.5 text-left cursor-pointer group">
              <div className="w-9 h-9 rounded-xl bg-white/[0.05] border border-white/[0.1] flex items-center justify-center flex-shrink-0"><Icon className={`w-5 h-5 ${meta.color}`} /></div>
              <div className="flex-1 min-w-0"><div className="flex items-center gap-2 flex-wrap"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${meta.chip}`}>{meta.badge || `เมนู ${meta.no}`}</span><span className="text-sm font-black text-white group-hover:text-[#25F4EE]">{m.title}</span></div><p className="text-[11px] text-slate-400 mt-0.5">{m.sub}</p></div>
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-bold text-[#25F4EE]">เปิดเมนู<ArrowRight className="w-3.5 h-3.5" /></span>
            </button>
            <ul className="mt-3 space-y-1.5">
              {visible.map((p, i) => (<li key={i} className="flex items-start gap-2 text-[11px] sm:text-xs text-slate-300 leading-relaxed"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" /><span>{p}</span></li>))}
            </ul>
            {m.points.length > 3 && (
              <button onClick={() => setExpandedMenus((prev) => ({ ...prev, [m.id]: !prev[m.id] }))} className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-[#25F4EE] hover:text-white cursor-pointer transition-colors">{expanded ? 'ย่อลง' : `ดูเพิ่มอีก ${m.points.length - 3} ข้อ`}<ChevronDown className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-180' : ''}`} /></button>
            )}
            <div className="mt-2.5 p-2.5 rounded-xl bg-[#25F4EE]/[0.06] border border-[#25F4EE]/20 text-[11px] text-slate-300 leading-relaxed">เคล็ดลับ {m.tip}</div>
          </article> ); })}
        </div>
      </section>
      <section id="ug-quickstart" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg scroll-mt-20">
        <div className="flex items-center gap-2.5"><div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-rose-500/20 to-[#25F4EE]/20 border border-white/[0.1] flex items-center justify-center"><Clock className="w-4 h-4 text-rose-400" /></div><h2 className="text-sm sm:text-base font-black text-white">คลิปแรกใน 10 นาที ทำตาม 5 ข้อนี้</h2></div>
        <ol className="grid grid-cols-1 lg:grid-cols-2 gap-2 mt-3 items-start">
          {[['นาที 0-2 ใส่สินค้า', 'เปิดเมนู 1 วางลิงก์สินค้า กดดึงข้อมูล ตรวจชื่อ จุดขาย สเปกให้ครบ'], ['นาที 2-4 สร้างสคริปต์', 'เลือกมุมขาย 1 มุม กดสร้างสคริปต์ อ่าน Hook 3 วิแรกว่าหยุดนิ้วคนดูได้ไหม และกดจัดอันดับ Hook ด้วย TypeSafe AI เพื่อดูคะแนนตรึงคนดู'], ['นาที 4-6 ฟังเสียง', 'กดฟังเสียงพากย์ตัวอย่าง ถ้าโอเคกดส่งตัดต่อ ระบบสร้างโปรเจกต์ในเมนู 3 ให้'], ['นาที 6-8 ตรวจพรีวิว', 'ในเมนู 3 กดเล่นพรีวิว ดูซับ ป้าย Hook และ Safe Zone ว่าไม่โดนปุ่ม TikTok บัง'], ['นาที 8-10 เรนเดอร์', 'กดเรนเดอร์ รอไฟล์ 1080x1920 เสร็จที่เมนู 4 แล้วแชร์ QR เข้ามือถือโพสต์ได้เลย']].map(([t, d], i) => (
            <li key={i} className="flex items-start gap-2.5 p-2 rounded-xl bg-white/[0.03] border border-white/[0.06]"><span className="w-6 h-6 rounded-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white text-[11px] font-black flex items-center justify-center flex-shrink-0 font-mono">{i + 1}</span><div className="min-w-0"><div className="text-xs font-bold text-white">{t}</div><div className="text-[11px] text-slate-400 leading-relaxed mt-0.5">{d}</div></div></li>))}
        </ol>
      </section>
      <section id="ug-status" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 sm:p-5 shadow-lg scroll-mt-20">
        <h2 className="text-sm sm:text-base font-black text-white">สถานะคลิป 4 เฟส ดูที่เมนู 2</h2>
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-2 mt-3 items-start">
          {[['scripted', 'ร่างสคริปต์', 'มีไอเดีย มีบท แต่ยังไม่เข้าไทม์ไลน์', 'bg-slate-500/10 text-slate-300 border-slate-500/30'], ['in_production', 'กำลังตัดต่อ', 'มีโปรเจกต์ในไทม์ไลน์ กำลังทำ', 'bg-amber-500/10 text-amber-300 border-amber-500/30'], ['rendered', 'ตัดต่อเสร็จ', 'มีไฟล์ MP4 ใน 04_Exports พร้อมโพสต์', 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'], ['posted', 'โพสต์แล้ว', 'ขึ้น TikTok พร้อมตะกร้าสินค้า', 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30']].map(([code, name, desc, chip]) => (
            <div key={code} className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] min-w-0"><span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border font-mono ${chip}`}>{code}</span><div className="text-xs font-bold text-white mt-1.5">{name}</div><div className="text-[11px] text-slate-400 leading-snug mt-0.5">{desc}</div></div>))}
        </div>
      </section>
      <section id="ug-folders" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg scroll-mt-20">
        <div className="flex items-center gap-2.5"><FolderOpen className="w-4 h-4 text-amber-400" /><h2 className="text-sm sm:text-base font-black text-white">โฟลเดอร์ 00-06 ไฟล์อยู่ไหน</h2></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-1.5 mt-2.5 items-start">
          {[['00_Inbox', 'พักไฟล์ดิบจากมือถือ ยังไม่จัดหมวด'], ['01_Raw', 'ฟุตเทจต้นฉบับแยกตามวันและสินค้า ห้ามลบ'], ['02_Assets', 'เพลง ฟอนต์ SFX สติกเกอร์ส่วนกลาง ห้ามลบ'], ['03_Projects', 'ไฟล์โปรเจกต์และสคริปต์ของแต่ละคลิป'], ['04_Exports', 'คลิปเรนเดอร์เสร็จ Ready_to_post และ Posted'], ['05_Covers', 'ปกคลิป 9:16'], ['06_Archive', 'เก็บสำรองหลังโพสต์ครบ 30 วัน'], ['GadgetMedia/', 'โฟลเดอร์ย่อยของงานแกดเจ็ตใน 01_Raw / 03_Projects / 04_Exports และ _Docs/gadget_media'], ['CapCut Drafts', 'เปิดต่อใน CapCut PC เปิดจากเมนู 7']].map(([n, d]) => (
          <div key={n} className="flex items-start gap-2 p-2 rounded-xl bg-white/[0.03] border border-white/[0.06] min-w-0"><span className="text-[11px] font-bold font-mono text-[#25F4EE] whitespace-nowrap">{n}</span><span className="text-[11px] text-slate-300 leading-snug">{d}</span></div>))}
        </div>
      </section>
      <section id="ug-checklist" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg scroll-mt-20">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <h2 className="text-sm sm:text-base font-black text-white">เช็กลิสต์ก่อนโพสต์ 6 ข้อ</h2>
          <div className="flex items-center gap-2">
            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${checked.length === CHECKLIST.length ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40' : 'bg-white/[0.04] text-slate-300 border-white/[0.1]'}`}>เช็คแล้ว {checked.length}/{CHECKLIST.length}</span>
            {checked.length > 0 && (<button onClick={resetChecklist} className="text-[11px] font-bold text-slate-400 hover:text-white cursor-pointer">ล้าง</button>)}
          </div>
        </div>
        <div className="mt-2.5 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-300 ${checked.length === CHECKLIST.length ? 'bg-gradient-to-r from-emerald-400 to-emerald-300' : 'bg-gradient-to-r from-[#FE2C55] to-[#25F4EE]'}`} style={{ width: `${(checked.length / CHECKLIST.length) * 100}%` }} />
        </div>
        {checked.length === CHECKLIST.length && (<p className="mt-2 text-[11px] font-bold text-emerald-300">ครบ 6 ข้อ พร้อมโพสต์ได้เลย</p>)}
        <ul className="grid grid-cols-1 lg:grid-cols-2 gap-1.5 mt-2.5 items-start">
          {CHECKLIST.map((c, i) => { const done = checked.includes(i); return (
          <li key={i}><button onClick={() => toggleCheck(i)} className={`w-full flex items-start gap-2 p-2 rounded-xl border text-left cursor-pointer transition-colors ${done ? 'bg-emerald-500/[0.08] border-emerald-500/30' : 'bg-white/[0.03] border-white/[0.06] hover:border-white/[0.15]'}`}>{done ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5" /> : <Circle className="w-3.5 h-3.5 text-slate-500 flex-shrink-0 mt-0.5" />}<span className={`text-[11px] sm:text-xs leading-relaxed ${done ? 'text-slate-200 line-through decoration-emerald-500/60' : 'text-slate-300'}`}>{c}</span></button></li> ); })}
        </ul>
      </section>
      <section id="ug-trouble" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg scroll-mt-20">
        <h2 className="text-sm sm:text-base font-black text-white">แก้ปัญหาเบื้องต้น 4 อาการ</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-1.5 mt-2.5 items-start">
          {TROUBLES.map((item) => (
          <div key={item.t} className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/[0.06] min-w-0 flex flex-col gap-1"><div className="text-xs font-bold text-white">{item.t}</div><div className="text-[11px] text-slate-400 leading-snug flex-1">{item.d}</div><button onClick={() => go(item.tab)} className="inline-flex items-center gap-1 text-[10px] font-bold text-[#25F4EE] hover:text-white cursor-pointer self-start transition-colors">{item.label}<ArrowRight className="w-3 h-3" /></button></div>))}
        </div>
      </section>
      <section id="ug-faq" className="bg-[#0B0F19] border border-white/[0.08] rounded-2xl p-4 shadow-lg scroll-mt-20">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2.5"><CircleHelp className="w-4 h-4 text-[#25F4EE]" /><h2 className="text-sm sm:text-base font-black text-white">คำถามพบบ่อย</h2></div>
          <div className="flex items-center gap-1.5">
            <button onClick={() => setOpenFaq(filteredFaqs.map((f) => f.idx))} className="text-[11px] font-bold text-[#25F4EE] hover:text-white cursor-pointer">เปิดทั้งหมด</button>
            <span className="text-slate-600 text-[11px]">/</span>
            <button onClick={() => setOpenFaq([])} className="text-[11px] font-bold text-slate-400 hover:text-white cursor-pointer">ปิดทั้งหมด</button>
          </div>
        </div>
        <div className="relative mt-2.5">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input value={faqQuery} onChange={(e) => setFaqQuery(e.target.value)} placeholder="ค้นหาคำถาม เช่น เสียง ซับ เรนเดอร์" className="w-full pl-9 pr-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] focus:border-[#25F4EE]/50 focus:outline-none text-base sm:text-xs text-slate-200 placeholder:text-slate-500" />
        </div>
        {faqQuery.trim() && (<p className="mt-2 text-[11px] text-slate-400">พบ {filteredFaqs.length} จาก {FAQS.length} คำถาม</p>)}
        {filteredFaqs.length === 0 ? (
          <div className="mt-2.5 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06] text-center">
            <p className="text-xs font-bold text-white">ไม่พบคำถามที่ตรงกับ “{faqQuery.trim()}”</p>
            <p className="mt-1 text-[11px] text-slate-400">ลองค้นด้วยคำอื่น เช่น เสียง ซับ เรนเดอร์ ไฟล์ โพสต์</p>
            <button onClick={() => setFaqQuery('')} className="mt-2 text-[11px] font-bold text-[#25F4EE] hover:text-white cursor-pointer">ล้างคำค้นหา</button>
          </div>
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-1.5 mt-2.5 items-start">
          {filteredFaqs.map((f) => { const open = openFaq.includes(f.idx); return (
            <div key={f.idx} className="rounded-2xl border border-white/[0.08] bg-white/[0.02] overflow-hidden min-w-0">
              <button
                onClick={() => {
                  try { navigator.vibrate?.(10); } catch {}
                  toggleFaq(f.idx);
                }}
                className="w-full min-h-[48px] flex items-center justify-between gap-2 p-3 text-left cursor-pointer active:bg-white/[0.04]"
              >
                <span className="text-xs font-bold text-white leading-snug">{f.q}</span>
                <ChevronDown className={`w-4 h-4 text-[#25F4EE] flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
              </button>
              {open && (<p className="px-3 pb-3 text-[11px] sm:text-xs text-slate-300 leading-relaxed">{f.a}</p>)}
            </div> ); })}
        </div>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <button onClick={() => go('flow')} className="min-h-[44px] flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] text-white text-xs font-bold cursor-pointer active:scale-95">เริ่มสร้างคลิปแรก<ArrowRight className="w-3.5 h-3.5" /></button>
          <button onClick={() => go('settings')} className="min-h-[44px] px-4 py-2.5 rounded-xl bg-white/[0.05] border border-white/[0.1] text-xs font-bold text-slate-200 cursor-pointer active:scale-95">เปิดตั้งค่าระบบ</button>
        </div>
      </section>
    </div>
  );
}
