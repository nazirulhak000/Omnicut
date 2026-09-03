import React, { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { Play, Pause, Eye } from 'lucide-react';
import { toMediaUrl } from '../lib/mediaUrl';
import {
  buildSegments, totalDuration as totalDurationOf, getDrawPlan as planAt
} from '../lib/timelineMath';

const CANVAS_W = 540;
const CANVAS_H = 960;
// How far a clip's decoded currentTime may drift from the wall-clock-derived
// target before we force a reseek. Hidden <video> elements were measured
// decoding at ~3-7x real time in this environment (Chromium doesn't pace
// paint/compositor work the same way for off-screen media) -- an
// independent clock plus periodic resync keeps playback at real speed
// regardless of how fast the browser is willing to decode.
const RESYNC_THRESHOLD = 0.15;

/**
 * CSS filter that approximates video_editor.py's per-clip `eq`. ffmpeg's
 * brightness is an additive offset (-0.3..0.3) while canvas brightness is a
 * multiplier, so it is mapped to 1 + b -- close enough to judge a grade by,
 * and the rendered file is still the source of truth.
 */
function clipFilter(clip) {
  if (!clip) return 'none';
  const parts = [];
  const b = clip.brightness ?? 0;
  const c = clip.contrast ?? 1;
  const sat = clip.saturation ?? 1;
  if (Math.abs(b) > 1e-3) parts.push(`brightness(${(1 + b).toFixed(3)})`);
  if (Math.abs(c - 1) > 1e-3) parts.push(`contrast(${c.toFixed(3)})`);
  if (Math.abs(sat - 1) > 1e-3) parts.push(`saturate(${sat.toFixed(3)})`);
  return parts.length ? parts.join(' ') : 'none';
}

function drawVideoFrame(ctx, video, clip) {
  if (!video || !video.videoWidth || video.readyState < 2) return false;
  const rotation = Number(clip?.rotation || 0) % 360;
  const isRotated90or270 = rotation === 90 || rotation === 270;
  const vw = isRotated90or270 ? video.videoHeight : video.videoWidth;
  const vh = isRotated90or270 ? video.videoWidth : video.videoHeight;
  const vRatio = vw / vh, cRatio = CANVAS_W / CANVAS_H;
  let sx, sy, sw, sh;
  if (vRatio > cRatio) {
    sh = vh; sw = vh * cRatio; sy = 0; sx = (vw - sw) / 2;
  } else {
    sw = vw; sh = vw / cRatio; sx = 0; sy = (vh - sh) / 2;
  }

  // Zoom crops into that cover-fit rect; pan slides it across the room the
  // zoom left, the same -1..1 mapping frame_geometry() uses in video_editor.py.
  const zoom = Math.min(3, Math.max(1, clip?.zoom || 1));
  if (zoom > 1.001) {
    const zw = sw / zoom, zh = sh / zoom;
    const roomX = sw - zw, roomY = sh - zh;
    const panX = Math.min(1, Math.max(-1, clip?.pan_x || 0));
    const panY = Math.min(1, Math.max(-1, clip?.pan_y || 0));
    sx += (roomX / 2) * (1 + panX);
    sy += (roomY / 2) * (1 + panY);
    sw = zw; sh = zh;
  }

  const mirror = !!clip?.mirror;
  if (mirror || rotation !== 0) {
    ctx.save();
    ctx.translate(CANVAS_W / 2, CANVAS_H / 2);
    if (mirror) ctx.scale(-1, 1);
    if (rotation !== 0) ctx.rotate((rotation * Math.PI) / 180);

    if (rotation === 90) {
      const rawSx = sy;
      const rawSy = video.videoHeight - (sx + sw);
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), Math.min(video.videoWidth, sh), Math.min(video.videoHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 270) {
      const rawSx = video.videoWidth - (sy + sh);
      const rawSy = sx;
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), Math.min(video.videoWidth, sh), Math.min(video.videoHeight, sw), -CANVAS_H / 2, -CANVAS_W / 2, CANVAS_H, CANVAS_W);
    } else if (rotation === 180) {
      const rawSx = video.videoWidth - (sx + sw);
      const rawSy = video.videoHeight - (sy + sh);
      ctx.drawImage(video, Math.max(0, rawSx), Math.max(0, rawSy), sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    } else {
      ctx.drawImage(video, sx, sy, sw, sh, -CANVAS_W / 2, -CANVAS_H / 2, CANVAS_W, CANVAS_H);
    }
    ctx.restore();
  } else {
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, CANVAS_W, CANVAS_H);
  }
  return true;
}

// Mirrors the .ass style the renderer burns: CAPTION_POSITIONS in
// subtitle_engine.py puts the block at the bottom (margin 420 of 1920),
// centre, or top (margin 260). Same fractions here so the preview does not
// promise a placement the file will not have.
const CAPTION_Y = { bottom: 1 - 420 / 1920, middle: 0.5, top: 260 / 1920 };
const CAPTION_COLORS = { white: '#fff', yellow: '#FFE600' };

/**
 * Wraps Thai and English text into natural lines based on canvas width,
 * preventing horizontal font squeezing/compression.
 */
function wrapCanvasText(text, ctx, maxW) {
  if (!text) return [];
  const rawParas = String(text).replace(/\\N/g, '\n').split('\n');
  const resultLines = [];

  for (const para of rawParas) {
    const trimmed = para.trim();
    if (!trimmed) continue;

    if (ctx.measureText(trimmed).width <= maxW) {
      resultLines.push(trimmed);
      continue;
    }

    // Tokenize using Intl.Segmenter if available, fallback to whitespace
    let tokens = [];
    if (typeof Intl !== 'undefined' && Intl.Segmenter) {
      try {
        const segmenter = new Intl.Segmenter(['th', 'en'], { granularity: 'word' });
        tokens = Array.from(segmenter.segment(trimmed)).map(s => s.segment);
      } catch (e) {
        tokens = trimmed.split(/(\s+)/);
      }
    } else {
      tokens = trimmed.split(/(\s+)/);
    }

    // Glue Thai grammatical prefixes so they never hang alone at the end of a line
    const THAI_PREFIXES = new Set(['ผู้', 'การ', 'ความ', 'นัก', 'ชาว', 'จาก']);
    const gluedTokens = [];
    for (let i = 0; i < tokens.length; i++) {
      const tok = tokens[i];
      if (THAI_PREFIXES.has(tok) && i + 1 < tokens.length) {
        gluedTokens.push(tok + tokens[i + 1]);
        i++;
      } else {
        gluedTokens.push(tok);
      }
    }
    tokens = gluedTokens;

    // Check if 2 balanced lines fit nicely
    const totalW = ctx.measureText(trimmed).width;
    if (totalW <= maxW * 1.95 && tokens.length > 2) {
      const targetMid = totalW / 2;
      let accumW = 0;
      let bestIdx = 1;
      let bestDiff = 999999;
      for (let i = 0; i < tokens.length - 1; i++) {
        accumW += ctx.measureText(tokens[i]).width;
        const diff = Math.abs(accumW - targetMid);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestIdx = i + 1;
        }
      }
      const l1 = tokens.slice(0, bestIdx).join('').trim();
      const l2 = tokens.slice(bestIdx).join('').trim();
      if (ctx.measureText(l1).width <= maxW * 1.05 && ctx.measureText(l2).width <= maxW * 1.05) {
        resultLines.push(l1, l2);
        continue;
      }
    }

    // Multi-line wrap
    let currentLine = '';
    for (const w of tokens) {
      const test = currentLine + w;
      if (ctx.measureText(test).width > maxW && currentLine.trim().length > 0) {
        resultLines.push(currentLine.trim());
        currentLine = w.trimStart();
      } else {
        currentLine = test;
      }
    }
    if (currentLine.trim()) {
      resultLines.push(currentLine.trim());
    }
  }

  return resultLines.length > 0 ? resultLines : [text];
}

const KINETIC_COLOR_MAP = {
  '#FFE600': [ // 🟡 Neon Yellow (Pain points, prices, deals, primary punch, positive reactions)
    // 1. Physical Discomfort & Pain Points
    'ออฟฟิศซินโดรม', 'ปวดข้อมือ', 'ปวดหลัง', 'ปวดคอ', 'ปวดหัว', 'ปวดไหล่', 'ปวดขา', 'ปวดเมื่อย',
    'ปวดมือ', 'ปวดตัว', 'ปวด', 'เมื่อยล้า', 'เมื่อย', 'ทรมาน', 'เหนื่อยล้า', 'เหนื่อย',
    // 2. Tech & Everyday Frustrations
    'สายพันกัน', 'สายขาด', 'แบตหมดไว', 'แบตเสื่อม', 'กระตุก', 'เครื่องค้าง', 'ค้าง', 'ช้ามาก', 'ช้า',
    'พังง่าย', 'พัง', 'หักง่าย', 'หัก', 'เสียเงินฟรี', 'เสียดายเงิน', 'เสีย', 'หลุดบ่อย', 'หลุด',
    // 3. Beauty, Skin & Personal Care Problems
    'สิวบุก', 'สิวเห่อ', 'สิวขึ้น', 'เป็นสิว', 'รอยสิว', 'รอยดำ', 'รอยแดง', 'หน้ามัน', 'หน้าหมอง', 'หมองคล้ำ',
    'ผิวแห้ง', 'ผิวลอก', 'เหนียวเหนอะหนะ', 'เหนอะหนะ', 'คราบฝังลึก', 'สกปรก', 'กลิ่นอับ', 'เหม็นอับ', 'เหม็น',
    // 4. Fashion, Body & Confidence
    'อึดอัด', 'แน่นพุง', 'พุงยื่น', 'ขาใหญ่', 'ดูอ้วน', 'เชยๆ', 'เชย', 'ล้าสมัย', 'ไม่มั่นใจ', 'ไม่สวย',
    'ปัญหา', 'ยุ่งยาก', 'เสียเวลา', 'เปลืองแรง', 'เปลืองเงิน', 'หงุดหงิด',
    // 5. Price, Deals, Vouchers & E-Commerce CTA
    'ราคาพิเศษ', 'ลดราคา', 'ลดกระหน่ำ', 'ลดแรง', 'ดีลพิเศษ', 'ดีลลับ', 'โปรเด็ด', 'โปรแรง', 'โปรโมชั่น',
    'แฟลชเซล', 'flash sale', 'โค้ดลด', 'โค้ดลับ', 'คูปอง', 'ส่งฟรี', '1 แถม 1', 'หนึ่งแถมหนึ่ง',
    'ของแถม', 'แจกฟรี', 'ฟรี', 'บาท', 'หลักสิบ', 'หลักร้อย', 'ราคาดี', 'ราคาโดน', 'ถูกและดี',
    'ถูกสุดๆ', 'ถูกมาก', 'คุ้มสุดๆ', 'คุ้มค่า', 'คุ้มราคา', 'เกินคุ้ม', 'คุ้ม', 'ประหยัด', 'ตกใจราคา',
    'ตะกร้าส้ม', 'ตะกร้าซ้ายล่าง', 'ตะกร้า', 'ใส่ตะกร้า', 'จิ้มตะกร้า', 'จิ้มเลย', 'จิ้มตรงนี้', 'กดตรงนี้',
    'พิกัดในคอมเมนต์', 'พิกัดในโปรไฟล์', 'พิกัด', 'ปักหมุด', 'อย่ารอ', 'อย่าช้า', 'ช้าหมด',
    'รีบตำ', 'รีบจัด', 'ด่วนเลย', 'ด่วน', 'ต้องมี', 'ของมันต้องมี', 'ขาดไม่ได้',
    // 6. Viral Praise & Reviewer Hype
    'ป้ายยา', 'ตัวท็อป', 'ตัวแม่', 'ยืนหนึ่ง', 'ตัวตึง', 'ของดีบอกต่อ', 'ใช้ดีบอกต่อ', 'ของดี',
    'ดีจริง', 'ดูดีมาก', 'ดีมาก', 'ดีเกินคาด', 'ดีเกินราคา', 'ว้าวมาก', 'ว้าว', 'ตาแตก', 'ตะลึง',
    'สุดปัง', 'ปังมาก', 'จึ้งมาก', 'จึ้ง', 'เลิศมาก', 'เลิศ', 'เอาเรื่อง', 'ของแทร่', 'เปลี่ยนชีวิต',
    'ยกระดับ', 'หลงรักเลย', 'หลงรัก', 'ชอบมาก', 'ติดใจ', 'ไม่ผิดหวัง', 'ไม่จกตา', 'รีวิวจริง',
    'ใช้จริง', 'หมดปัญหา', 'ลืมแบบเก่าไปเลย', 'โคตรดี', 'โคตรคุ้ม', 'ฟินมาก', 'ช็อค', 'น่ารักกว่าในรูป', 'ของที่รอคอย',
    // English Counterparts
    'office syndrome', 'wrist pain', 'back pain', 'neck pain', 'shoulder pain', 'headache', 'leg pain',
    'body pain', 'hand hurts', 'hurts', 'painful', 'pain', 'tight', 'sore', 'exhausted',
    'tiring', 'tired', 'suffering',
    'tangled', 'broken cord', 'dead battery', 'low battery', 'laggy', 'lagging', 'freezing', 'too slow', 'slow',
    'breaks easily', 'broken', 'waste of money', 'waste of time', 'wasted', 'annoying',
    'acne breakout', 'breakouts', 'pimples', 'dark spots', 'redness', 'oily skin', 'dull skin',
    'dry skin', 'peeling skin', 'sticky', 'greasy', 'deep stains', 'dirty', 'bad odor', 'smelly',
    'uncomfortable', 'stuffy', 'bloated', 'tight fit', 'outdated', 'unconfident', 'insecure',
    'problems', 'problem', 'frustrating', 'troublesome', 'not sure',
    'special price', 'huge discount', 'discount', 'special deal', 'secret deal', 'best promo', 'promotion',
    'flash sale', 'promo code', 'voucher', 'coupon', 'free shipping', 'buy 1 get 1', 'bogo',
    'free gift', 'giveaway', 'free', 'baht', 'super cheap', 'cheap', 'affordable', 'best price',
    'best value', 'great value', 'worth every penny', 'worth it', 'save money', 'shocking price',
    'yellow basket', 'orange basket', 'cart', 'add to cart', 'click cart', 'click now', 'click here',
    'pinned link', 'link in bio', 'coordinates', 'don\'t wait', 'don\'t delay', 'almost gone',
    'buy now', 'grab it now', 'hurry up', 'must have', 'essential',
    'holy grail', 'game changer', 'life-changing', 'top tier', 'the best', 'highly recommend',
    'really good', 'looks really good', 'looks good', 'so good', 'very good', 'good', 'exceeded expectations',
    'unbelievable', 'very wow', 'wow', 'mind blowing', 'stunning', 'gorgeous', 'slay',
    'aesthetic', 'next level', 'fell in love', 'obsessed', 'love it', 'no regret', 'won\'t be disappointed',
    'real review', 'tried and tested', 'problem solved', 'insanely good', 'super worth it', 'so satisfying',
    'much cuter', 'long-awaited', 'recommend'
  ],
  '#00E5FF': [ // 🔵 Electric Cyan (Features, tech, ergonomics, certifications, comfort)
    // 1. Tech, Gadgets & Hardware
    'Logitech Wave Keys', 'Logitech', 'Wave Keys', 'คีย์บอร์ดในฝัน', 'คีย์บอร์ด', 'ไร้สาย', 'บลูทูธ',
    'แม่เหล็ก', 'แรงดูดสูง', 'ดูดแน่น', '540 องศา', '360 องศา', 'ชาร์จไว', 'ฟาสชาร์จ', '66W', '100W',
    'แบตอึด', 'แบตทน', 'ทนทาน', 'แข็งแรง', 'ประกันศูนย์', 'ของแท้', 'แท้ 100%', 'จอสวย', 'จอลื่น',
    '120Hz', 'คมชัด', 'กล้องชัด', 'เสียงดี', 'เบสแน่น', 'ตัดเสียงรบกวน', 'กันน้ำ', 'ชิปเร็ว',
    'ลื่นไหล', 'ไม่สะดุด', 'เชื่อมต่อง่าย', 'เสียบปุ๊บติดปั๊บ', 'พกพาสะดวก', 'น้ำหนักเบา', 'กะทัดรัด',
    'ปรับระดับได้', 'พับเก็บได้', 'ประหยัดพื้นที่', 'ประกอบง่าย', 'ใช้งานง่าย',
    // 2. Ergonomics, Comfort, Softness & Apparel
    'สรีรศาสตร์', 'เมมโมรี่โฟม', 'ที่รองข้อมือ', 'พิมพ์สบาย', 'นั่งสบาย', 'นอนสบาย', 'ใส่สบาย',
    'สบายมาก', 'นุ่มสบาย', 'สบายมือ', 'สบายหลัง', 'สบายตา', 'สบายตัว', 'สบาย', 'นุ่มนิ่ม', 'นุ่มฟู',
    'นุ่มมาก', 'นุ่มๆ', 'นุ่ม', 'ยืดหยุ่น', 'สัมผัสนุ่ม', 'ไม่ระคายเคือง', 'ไม่บาดผิว', 'ทรงสวย',
    'ทรงเป๊ะ', 'พอดีตัว', 'เข้ารูป', 'ทิ้งตัวสวย', 'พรางหุ่น', 'เก็บพุง', 'ระบายอากาศ', 'ไม่อับชื้น',
    'ไม่ร้อน', 'เย็นสบาย', 'มินิมอล', 'ดีไซน์แบบคลื่นๆ', 'แบบคลื่นๆ', 'คลื่น', 'ดีไซน์สวย',
    // 3. Skincare, Beauty & Quality Efficacy
    'ผิวฉ่ำวาว', 'ผิวฉ่ำน้ำ', 'ผิวฉ่ำ', 'หน้าใส', 'ผิวเนียน', 'ผิวกระจก', 'ผิวนุ่มเด้ง', 'หน้าเด็ก',
    'ซึมไว', 'ซึมเร็ว', 'แห้งไว', 'บางเบา', 'ไม่เหนอะหนะ', 'คุมมัน', 'ผิวกระชับ', 'รูขุมขนกระชับ',
    'กลิ่นหอม', 'หอมละมุน', 'หอมฟุ้ง', 'ติดทน', 'ติดทนนาน', 'ไม่ติดแมสก์', 'กันเหงื่อ', 'กันน้ำกันเหงื่อ',
    'ปกปิดเนียน', 'กลบเนียน', 'ไม่วอก', 'ไม่ลอย', 'อ่อนโยน', 'แพ้ง่ายใช้ได้', 'สารสกัดธรรมชาติ',
    'ออร์แกนิก', 'พรีเมียมสุดๆ', 'พรีเมียม', 'หรูหรา', 'ดูแพง', 'สะอาดหมดจด', 'ฆ่าเชื้อ', 'กรองฝุ่น',
    'รับรอง', 'ผู้เชี่ยวชาญ', 'แพทย์ผิวหนัง', 'สุขภาพดี', 'ปลอดภัย',
    // English Counterparts
    'logitech wave keys', 'wave keys', 'logitech', 'dream keyboard', 'keyboard', 'wireless', 'bluetooth',
    'magnetic', 'strong magnet', '540 degrees', '360 degrees', 'fast charging', 'quick charge', '66w', '100w',
    'long battery', 'battery life', 'durable', 'sturdy', 'warranty', 'genuine', 'authentic', 'smooth screen',
    '120hz', 'crystal clear', 'sharp camera', 'great sound', 'deep bass', 'noise cancelling', 'waterproof',
    'fast chip', 'ultra smooth', 'easy connect', 'plug and play', 'portable', 'lightweight', 'compact',
    'adjustable', 'foldable', 'space saving', 'easy to assemble', 'easy to use',
    'ergonomic', 'ergonomics', 'memory foam', 'wrist rest', 'typing comfortable', 'sit comfortably',
    'comfortable fit', 'comfortable', 'comfy', 'super comfy', 'soft and comfy', 'extra soft', 'pillow soft',
    'very soft', 'soft', 'flexible', 'gentle touch', 'non-irritating', 'flattering fit',
    'perfect fit', 'slim fit', 'tummy control', 'breathable', 'airy', 'cool and fresh',
    'minimalist', 'minimal', 'wavy design', 'wavy', 'sleek design', 'beautiful design',
    'glass skin', 'glowy skin', 'glowing skin', 'clear skin', 'smooth skin', 'bouncy skin', 'youthful',
    'fast absorbing', 'quick absorb', 'quick drying', 'lightweight texture', 'non-sticky', 'non-greasy', 'oil control',
    'firming', 'pore tightening', 'nice scent', 'pleasant smell', 'long lasting', 'transfer-proof', 'sweat-proof',
    'water resistant', 'full coverage', 'natural finish', 'no white cast', 'gentle formula', 'sensitive skin friendly',
    'natural extracts', 'organic', 'very premium', 'premium', 'luxury', 'looks expensive',
    'deep clean', 'antibacterial', 'hepa filter', 'certified', 'experts', 'expert',
    'dermatologist', 'healthy', 'safe'
  ],
  '#FF3B30': [ // 🔴 Alert Red (Urgency, warnings)
    'อย่าเพิ่งซื้อ', 'อย่าเพิ่ง', 'หยุดก่อน', 'หยุดดูคลิปนี้', 'ฟังทางนี้', 'เตือนภัย', 'เตือน',
    'ระวังของปลอม', 'ระวัง', 'อันตราย', 'เสี่ยง', 'ห้ามทำ', 'อย่าหาทำ', 'อย่าพลาด',
    'ห้ามพลาด', 'ห้ามเลื่อนผ่าน', 'ของปลอมระบาด', 'ซื้อผิดรุ่น', 'ดูให้จบ', 'ข้อเสีย', 'สิ่งที่ควรรู้',
    // English Counterparts
    'don\'t buy yet', 'don\'t buy', 'stop scrolling', 'wait a minute', 'listen to this', 'urgent warning', 'warning',
    'beware of fake', 'beware', 'danger', 'risky', 'don\'t do this', 'don\'t miss out',
    'don\'t miss', 'watch till the end', 'counterfeit', 'fake products', 'cons', 'must know',
    'look at this', 'watch this', 'warn', 'stop'
  ]
};

function parseKineticSegments(text, defaultColor = '#FFFFFF', colorHint = null, customKeywords = []) {
  if (!text) return [];

  // Tier 1: Check for explicit user / AI markers like *keyword* or [keyword]
  const markerRegex = /(\*([^*]+)\*|\[([^\]]+)\])/;
  if (markerRegex.test(text)) {
    const chosenColor = colorHint || '#FFE600';
    const segments = [];
    let lastIdx = 0;
    const re = /(\*([^*]+)\*|\[([^\]]+)\])/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > lastIdx) {
        segments.push({ text: text.slice(lastIdx, m.index), color: defaultColor });
      }
      const kw = m[2] || m[3];
      segments.push({ text: kw, color: chosenColor });
      lastIdx = m.index + m[0].length;
    }
    if (lastIdx < text.length) {
      segments.push({ text: text.slice(lastIdx), color: defaultColor });
    }
    return segments;
  }

  const lowerText = text.toLowerCase();
  const matches = [];

  // Prioritize colorHint group first to ensure 1:1 cross-language color synchronization
  const colors = Object.keys(KINETIC_COLOR_MAP);
  const colorOrder = colorHint && colors.includes(colorHint)
    ? [colorHint, ...colors.filter(c => c !== colorHint)]
    : colors;

  for (const color of colorOrder) {
    let keywords = KINETIC_COLOR_MAP[color] || [];
    if (color === '#00E5FF' && customKeywords && customKeywords.length > 0) {
      keywords = [...customKeywords, ...keywords];
    }
    const sorted = [...keywords].sort((a, b) => b.length - a.length);
    for (const kw of sorted) {
      const lowerKw = kw.toLowerCase();
      let matchIdx = -1;
      let matchLen = kw.length;

      if (/[^\u0000-\u007F]/.test(kw)) {
        // Thai text matching
        matchIdx = text.indexOf(kw);
      } else {
        // English case-insensitive word matching
        const escaped = lowerKw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(?:^|[^a-zA-Z0-9])${escaped}(?:$|[^a-zA-Z0-9])`, 'i');
        const match = lowerText.match(regex);
        if (match) {
          const matchedSub = match[0];
          const offset = matchedSub.toLowerCase().indexOf(lowerKw);
          matchIdx = match.index + offset;
          matchLen = lowerKw.length;
        }
      }

      if (matchIdx !== -1) {
        const end = matchIdx + matchLen;
        const overlaps = matches.some(m => Math.max(matchIdx, m.start) < Math.min(end, m.end));
        if (!overlaps) {
          matches.push({ start: matchIdx, end, color });
          break; // exactly 1 match per color category
        }
      }
    }
  }

  if (matches.length === 0) {
    return [{ text, color: defaultColor }];
  }

  matches.sort((a, b) => a.start - b.start);

  const segments = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) {
      segments.push({ text: text.slice(cursor, m.start), color: defaultColor });
    }
    segments.push({ text: text.slice(m.start, m.end), color: m.color });
    cursor = m.end;
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), color: defaultColor });
  }
  return segments;
}

function drawCaption(ctx, cues, t, style = {}) {
  const cue = cues.find(c => t >= c.start && t < c.end);
  if (!cue || !cue.text) return;
  const cueScale = Number(cue.scale) || 1.0;
  const globalScale = Math.min(2.5, Math.max(0.5, style.captionScale ?? 1));
  const effectiveScale = Math.min(3.0, Math.max(0.4, globalScale * cueScale));
  // 100% (effectiveScale=1.0) calibrated to exactly 26px on 540w (matches Image 2 perfectly)
  const baseFs = Math.round(CANVAS_W * 0.048); // 26px on 540w
  const fontSize = Math.max(14, Math.round(baseFs * effectiveScale));
  
  let fontFam = "'Kanit', sans-serif";
  let fontWeight = '900';
  if (style.fontName === 'IBMPlex' || style.fontName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
    fontWeight = '700';
  } else if (style.fontName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
    fontWeight = '800';
  }

  ctx.save();
  ctx.font = `${fontWeight} ${fontSize}px ${fontFam}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  
  // Crisp outline + punchy shadow matching libass
  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 3;
  ctx.shadowOffsetX = 2;
  ctx.shadowOffsetY = 3;
  
  ctx.strokeStyle = '#000000';
  ctx.lineWidth = Math.round(fontSize * 0.20);
  ctx.lineJoin = 'round';
  ctx.miterLimit = 2;
  
  const maxLineW = CANVAS_W * 0.86;
  const thaiLines = wrapCanvasText(cue.text, ctx, maxLineW);
  const thaiLineH = Math.round(fontSize * 1.15);

  // Stacked bilingual English subtitle
  let enLines = [];
  const enFontSize = Math.round(fontSize * 0.68);
  const enLineH = Math.round(enFontSize * 1.25);
  if (cue.translation && !cue.translation.includes('Error 500')) {
    ctx.font = `700 ${enFontSize}px ${fontFam}`;
    enLines = wrapCanvasText(cue.translation, ctx, CANVAS_W * 0.86);
  }

  // Vertical layout calculations to keep entire block centered at caption Y
  const thaiBlockH = thaiLines.length * thaiLineH;
  const enGap = enLines.length > 0 ? Math.round(fontSize * 0.22) : 0;
  const enBlockH = enLines.length * enLineH;
  const totalBlockH = thaiBlockH + enGap + enBlockH;

  const targetCenterY = CANVAS_H * (CAPTION_Y[style.captionPosition] ?? CAPTION_Y.bottom);
  const thaiStartY = targetCenterY - (totalBlockH / 2) + (thaiLineH / 2);

  // Synchronized Bilingual Kinetic Highlighting
  const primaryColor = CAPTION_COLORS[style.captionColor] || '#FFFFFF';
  const enDefaultColor = '#EAEAEA';

  let activeKineticColor = null;
  let parsedThaiLines = thaiLines.map((line) => {
    const segs = parseKineticSegments(line, primaryColor);
    const matched = segs.find(s => s.color !== primaryColor);
    if (matched) activeKineticColor = matched.color;
    return segs;
  });

  let parsedEnLines = [];
  if (enLines.length > 0) {
    let enMatchedColor = null;
    parsedEnLines = enLines.map((line) => {
      const segs = parseKineticSegments(line, enDefaultColor, activeKineticColor);
      const matched = segs.find(s => s.color !== enDefaultColor);
      if (matched) enMatchedColor = matched.color;
      return segs;
    });

    // If Thai had no match initially, but English matched a color, re-parse Thai with English's color
    if (!activeKineticColor && enMatchedColor) {
      parsedThaiLines = thaiLines.map(line => parseKineticSegments(line, primaryColor, enMatchedColor));
    }
  }

  // Draw Thai lines
  thaiLines.forEach((line, idx) => {
    const lineY = thaiStartY + (idx * thaiLineH);
    const segments = parsedThaiLines[idx] || [{ text: line, color: primaryColor }];

    ctx.font = `${fontWeight} ${fontSize}px ${fontFam}`;
    const segmentWidths = segments.map(seg => ctx.measureText(seg.text).width);
    const totalLineW = segmentWidths.reduce((sum, w) => sum + w, 0);

    // Pass 1: Outline / Stroke with crisp shadow
    ctx.textAlign = 'left';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = Math.round(fontSize * 0.20);
    ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
    ctx.shadowBlur = 3;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 3;

    let curX = (CANVAS_W - totalLineW) / 2;
    segments.forEach((seg, sIdx) => {
      ctx.strokeText(seg.text, curX, lineY);
      curX += segmentWidths[sIdx];
    });

    // Pass 2: Color fills (sharp contrast without doubled shadow)
    ctx.shadowColor = 'transparent';
    curX = (CANVAS_W - totalLineW) / 2;
    segments.forEach((seg, sIdx) => {
      ctx.fillStyle = seg.color;
      ctx.fillText(seg.text, curX, lineY);
      curX += segmentWidths[sIdx];
    });
  });

  // Draw English lines (stacked underneath) with matching kinetic color highlighting
  if (enLines.length > 0) {
    ctx.font = `700 ${enFontSize}px ${fontFam}`;
    const enStartY = thaiStartY + (thaiLines.length - 1) * thaiLineH + (thaiLineH / 2) + enGap + (enLineH / 2);

    enLines.forEach((line, idx) => {
      const lineY = enStartY + (idx * enLineH);
      const segments = parsedEnLines[idx] || [{ text: line, color: enDefaultColor }];
      const segmentWidths = segments.map(seg => ctx.measureText(seg.text).width);
      const totalLineW = segmentWidths.reduce((sum, w) => sum + w, 0);

      // Pass 1: Outline / Stroke with soft shadow
      ctx.textAlign = 'left';
      ctx.strokeStyle = '#000000';
      ctx.lineWidth = Math.round(enFontSize * 0.18);
      ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
      ctx.shadowBlur = 3;
      ctx.shadowOffsetX = 1.5;
      ctx.shadowOffsetY = 2;

      let curX = (CANVAS_W - totalLineW) / 2;
      segments.forEach((seg, sIdx) => {
        ctx.strokeText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });

      // Pass 2: Color fills (sharp contrast without doubled shadow)
      ctx.shadowColor = 'transparent';
      curX = (CANVAS_W - totalLineW) / 2;
      segments.forEach((seg, sIdx) => {
        ctx.fillStyle = seg.color;
        ctx.fillText(seg.text, curX, lineY);
        curX += segmentWidths[sIdx];
      });
    });
  }

  ctx.restore();
}

function drawSticker(ctx, img, t, style = {}) {
  if (!img || !img.complete || !img.naturalWidth) return;
  const startTime = style.startTime ?? 0.5;
  if (t < startTime) return;

  const scale = Math.min(2, Math.max(0.4, style.scale ?? 1));
  const baseW = 380;
  const w = Math.round(baseW * scale);
  const h = Math.round(w * (img.naturalHeight / img.naturalWidth));

  let x = CANVAS_W - w - 40;
  let y = 140;
  const pos = style.position || 'top_right';
  if (pos === 'top_left') {
    x = 40; y = 140;
  } else if (pos === 'bottom_right') {
    x = CANVAS_W - w - 40; y = CANVAS_H - h - 420;
  } else if (pos === 'bottom_left') {
    x = 40; y = CANVAS_H - h - 420;
  } else if (pos === 'top_center') {
    x = Math.round((CANVAS_W - w) / 2); y = 140;
  } else if (pos === 'bottom_center') {
    x = Math.round((CANVAS_W - w) / 2); y = CANVAS_H - h - 420;
  }

  const elapsed = t - startTime;
  const alpha = Math.min(1, Math.max(0, elapsed / 0.3));
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.drawImage(img, x, y, w, h);
  ctx.restore();
}

/**
 * 3-tier hook banner preview: brand (largest) / model (mid) / label
 * (smallest), mirroring subtitle_engine.py's generate_ass hook composition
 * (tier scale %s, HOOK_COMFORTABLE_LINES shrink, gradient backdrop) so what
 * plays here matches what Apply's ffmpeg render actually burns -- an
 * approximation on animation easing (this canvas fades alpha, the .ass pops
 * scale in), not on layout or which text shows where.
 */
function drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration = 3.5, fontName = 'Kanit', accentColor = '#FFE600') {
  if ((!hookBrand && !hookModel && !hookLabel) || t > hookDuration) return;

  let fontFam = "'Kanit', sans-serif";
  if (fontName === 'IBMPlex' || fontName === 'IBM Plex Sans Thai') {
    fontFam = "'IBM Plex Sans Thai', sans-serif";
  } else if (fontName === 'Prompt') {
    fontFam = "'Prompt', sans-serif";
  }

  let alpha = 1;
  if (t < 0.2) alpha = t / 0.2;
  if (t > hookDuration - 0.3) alpha = Math.max(0, (hookDuration - t) / 0.3);

  const baseFontSize = Math.round(CANVAS_W * 0.052 * 1.64);
  // Same tier percentages as hook_tier_specs in subtitle_engine.py.
  const tierSpecs = [
    { text: (hookBrand || '').trim().toUpperCase(), sizePct: 130, color: '#FFFFFF' },
    { text: (hookModel || '').trim(), sizePct: 100, color: accentColor },
    { text: (hookLabel || '').trim(), sizePct: 58, color: '#E0E0E0' },
  ].filter((tier) => tier.text);
  if (!tierSpecs.length) return;

  const maxW = CANVAS_W * 0.85;
  const x = CANVAS_W / 2;

  ctx.save();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';

  // Pass 1: wrap each tier at its OWN font size before measuring line count.
  const wrapped = [];
  for (const tier of tierSpecs) {
    const tierFs = Math.max(10, Math.round((baseFontSize * tier.sizePct) / 100));
    ctx.font = `900 ${tierFs}px ${fontFam}`;
    for (const line of wrapCanvasText(tier.text, ctx, maxW)) {
      wrapped.push({ line, fontSize: tierFs, color: tier.color });
    }
  }

  // Pass 2: same HOOK_COMFORTABLE_LINES=4 shrink as the backend, so a long
  // brand/model that wraps twice doesn't crowd the sticker badge (top-right,
  // y=140) instead of just overflowing unbounded.
  const shrink = Math.max(0.7, Math.min(1, 4 / wrapped.length));

  // Gradient backdrop -- mirrors video_editor.py's geq overlay (dark at the
  // top of the frame, fading to transparent by ~25% down), same alpha
  // envelope as the text so it fades out alongside the banner, not after.
  const gradH = Math.round(CANVAS_H * 0.25);
  const grad = ctx.createLinearGradient(0, 0, 0, gradH);
  grad.addColorStop(0, `rgba(0,0,0,${0.75 * alpha})`);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, CANVAS_W, gradH);

  ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
  ctx.shadowBlur = 10;
  ctx.shadowOffsetX = 3;
  ctx.shadowOffsetY = 4;
  ctx.strokeStyle = '#000000';
  ctx.lineJoin = 'round';
  ctx.miterLimit = 2;
  ctx.globalAlpha = alpha;

  let y = 130; // ~HookHeader's ASS MarginV=260 of 1920, scaled to this 960-tall canvas
  const lineGap = 1.15;
  for (const { line, fontSize, color } of wrapped) {
    const scaledFs = Math.max(10, Math.round(fontSize * shrink));
    ctx.font = `900 ${scaledFs}px ${fontFam}`;
    ctx.lineWidth = Math.round(scaledFs * 0.22);
    ctx.strokeText(line, x, y, maxW);
    ctx.fillStyle = color;
    ctx.fillText(line, x, y, maxW);
    y += scaledFs * lineGap;
  }
  ctx.restore();
}

/**
 * Plays `clips` back-to-back as one continuous sequence in a single canvas
 * (approximate preview -- real output only comes from Apply's ffmpeg
 * render, per this project's "accurate render, willing to wait" choice).
 * Segment timing math (fade eats FADE_DURATION of overlap) mirrors
 * video_editor.py's has_fade branch so what plays here lines up with what
 * Apply produces.
 *
 * The global playhead is driven by an independent performance.now() clock,
 * not by trusting a <video> element's own playback rate -- see
 * RESYNC_THRESHOLD's comment for why.
 */
function SequencePlayer({ clips, cues = [], hookBrand = '', hookModel = '', hookLabel = '', hookDuration = 3.0, audioUrl = null, compact = false, onPlayhead, onDurations, captionStyle = {}, stickerStyle = {} }, ref) {
  const canvasRef = useRef(null);
  const videoElsRef = useRef({});
  const audioElRef = useRef(null);
  const rafRef = useRef(null);
  const clockRef = useRef({ startWall: 0, startT: 0 });
  const stickerImgRef = useRef(null);

  const [durations, setDurations] = useState({});
  const [metadataReady, setMetadataReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const playheadRef = useRef(0);
  const prevActiveClipIdRef = useRef(null);

  const captionKey = `${captionStyle.captionPosition}:${captionStyle.captionColor}:${captionStyle.captionScale}:${captionStyle.fontName}:${hookBrand}:${hookModel}:${hookLabel}:${hookDuration}`;
  const cuesKey = (cues || []).map(c => `${c._uid || c.id}:${c.start}:${c.end}:${c.text}:${c.translation}:${c.scale || 1}`).join(';;');
  const stickerKey = `${stickerStyle.badge}:${stickerStyle.position}:${stickerStyle.scale}:${stickerStyle.startTime}`;
  const clipKey = clips.map(c => `${c.id}:${c.source_path}:${c.trim_start}:${c.trim_end}:${c.transition_in}:${c.transition_duration}:${c.brightness}:${c.contrast}:${c.saturation}:${c.zoom}:${c.pan_x}:${c.pan_y}:${c.mirror}:${c.rotation}`).join('|');

  useEffect(() => {
    if (!stickerStyle?.badge || !stickerStyle?.stickers?.length) {
      stickerImgRef.current = null;
      renderAt(playheadRef.current);
      return;
    }
    const found = stickerStyle.stickers.find((s) => 
      s.name === stickerStyle.badge || 
      s.id === stickerStyle.badge || 
      s.path === stickerStyle.badge ||
      (s.name && stickerStyle.badge && s.name.toLowerCase() === String(stickerStyle.badge).toLowerCase())
    );
    if (found?.img_url) {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.src = found.img_url;
      img.onload = () => {
        stickerImgRef.current = img;
        renderAt(playheadRef.current);
      };
    } else {
      stickerImgRef.current = null;
      renderAt(playheadRef.current);
    }
  }, [stickerStyle.badge, stickerStyle.stickers]);

  // Load real duration for every clip up front -- segment timing needs it
  // (a clip with trim_end === null trims to "the source's own end").
  useEffect(() => {
    setMetadataReady(false);
    setIsPlaying(false);
    setPlayhead(0);
    let cancelled = false;

    const waits = clips.map(c => new Promise((resolve) => {
      const v = videoElsRef.current[c.id];
      if (!v) return resolve();
      if (v.readyState >= 1) return resolve();
      const onLoaded = () => { v.removeEventListener('loadedmetadata', onLoaded); resolve(); };
      v.addEventListener('loadedmetadata', onLoaded);
    }));

    Promise.all(waits).then(() => {
      if (cancelled) return;
      const d = {};
      clips.forEach(c => { d[c.id] = videoElsRef.current[c.id]?.duration || 0; });
      setDurations(d);
      setMetadataReady(true);
      onDurations?.(d);
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clipKey]);

  const segments = useMemo(
    () => (metadataReady ? buildSegments(clips, durations) : []),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [clipKey, metadataReady, durations]
  );

  const totalDuration = totalDurationOf(segments);
  playheadRef.current = playhead;

  const getDrawPlan = (t) => planAt(segments, t);

  const renderAt = (t) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!ctx || !segments.length) return;
    const plan = getDrawPlan(t);
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
    plan.forEach(({ seg, alpha }) => {
      const video = videoElsRef.current[seg.clip.id];
      if (!video) return;
      ctx.globalAlpha = alpha;
      ctx.filter = clipFilter(seg.clip);
      drawVideoFrame(ctx, video, seg.clip);
    });
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration, captionStyle.fontName, captionStyle.captionColor || '#FFE600');
    drawCaption(ctx, cues, t, captionStyle);
    drawSticker(ctx, stickerImgRef.current, t, stickerStyle);
  };

  useEffect(() => {
    renderAt(playheadRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segments, captionKey, stickerKey, cuesKey]);

  const lastNotifyRef = useRef(0);

  useEffect(() => {
    if (!isPlaying || segments.length === 0) return;

    const tick = () => {
      // Audio Master Clock: Lock subtitle and video frames directly to the audio element's playback
      const audio = audioElRef.current;
      let t;
      if (audio && audio.src && !audio.paused && !audio.ended && audio.currentTime > 0) {
        t = audio.currentTime;
      } else {
        t = clockRef.current.startT + (performance.now() - clockRef.current.startWall) / 1000;
      }

      if (t >= totalDuration) {
        Object.values(videoElsRef.current).forEach(v => v?.pause());
        audioElRef.current?.pause();
        setPlayhead(totalDuration);
        onPlayhead?.(totalDuration);
        renderAt(totalDuration);
        setIsPlaying(false);
        return;
      }

      // Keep Audio Element in check if it fell behind/drifted
      if (audio && audio.src && !audio.paused && Math.abs(audio.currentTime - t) > 0.3) {
        audio.currentTime = t;
      }

      const plan = getDrawPlan(t);
      const neededIds = new Set(plan.map(p => p.seg.clip.id));

      // 1. Lookahead Pre-Roll: Pre-seek upcoming clips 0.8s - 1.2s in advance so they
      // have their first frame decoded and cached in memory before the cut boundary.
      const upcomingSeg = segments.find(s => s.segStart > t && s.segStart <= t + 1.2);
      if (upcomingSeg) {
        const nextV = videoElsRef.current[upcomingSeg.clip.id];
        const nextStart = upcomingSeg.clip.trim_start || 0;
        if (nextV && nextV.paused && !nextV.seeking) {
          if (Math.abs(nextV.currentTime - nextStart) > 0.08) {
            nextV.currentTime = nextStart;
          }
        }
      }

      // 2. Play active clips & compensate drift smoothly via playbackRate (slew rate)
      // rather than aggressive currentTime seeking which stalls the decoder pipeline.
      plan.forEach(({ seg, localTime }) => {
        const v = videoElsRef.current[seg.clip.id];
        if (!v) return;
        if (v.paused) {
          // If already near localTime from pre-roll, start immediately without seek!
          if (Math.abs(v.currentTime - localTime) > 0.12) {
            v.currentTime = localTime;
          }
          v.playbackRate = 1.0;
          v.play().catch(() => {});
        } else {
          const drift = v.currentTime - localTime;
          if (Math.abs(drift) > 0.4) {
            // Large drift (after scrub or tab resume) -> hard seek
            v.currentTime = localTime;
            v.playbackRate = 1.0;
          } else if (drift < -0.04) {
            // Video is slightly trailing behind -> accelerate 6% to catch up smoothly
            v.playbackRate = 1.06;
          } else if (drift > 0.04) {
            // Video is slightly ahead -> slow down 6% to let master clock catch up
            v.playbackRate = 0.94;
          } else {
            if (v.playbackRate !== 1.0) v.playbackRate = 1.0;
          }
        }
      });

      // 3. Pause video elements no longer in the plan
      Object.entries(videoElsRef.current).forEach(([id, v]) => {
        if (v && !v.paused && !neededIds.has(id)) {
          v.playbackRate = 1.0;
          v.pause();
        }
      });

      // 4. Glitch-Protected Double-Buffered Rendering
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (ctx) {
        let framePainted = false;
        plan.forEach(({ seg, alpha }) => {
          const video = videoElsRef.current[seg.clip.id];
          if (!video) return;

          // If incoming video is still actively seeking to its cut point,
          // hold the outgoing clip's frame to eliminate any flash or random frame stutter
          if (video.seeking && prevActiveClipIdRef.current && prevActiveClipIdRef.current !== seg.clip.id) {
            const prevV = videoElsRef.current[prevActiveClipIdRef.current];
            const prevSeg = segments.find(s => s.clip.id === prevActiveClipIdRef.current);
            if (prevV && prevSeg && prevV.readyState >= 2 && !prevV.seeking) {
              if (!framePainted) ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
              ctx.globalAlpha = 1;
              ctx.filter = clipFilter(prevSeg.clip);
              drawVideoFrame(ctx, prevV, prevSeg.clip);
              framePainted = true;
              return;
            }
          }

          if (video.readyState >= 2 && !video.seeking) {
            if (!framePainted) ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);
            ctx.globalAlpha = alpha;
            ctx.filter = clipFilter(seg.clip);
            drawVideoFrame(ctx, video, seg.clip);
            framePainted = true;
            prevActiveClipIdRef.current = seg.clip.id;
          }
        });

        ctx.globalAlpha = 1;
        ctx.filter = 'none';
        drawHookHeader(ctx, hookBrand, hookModel, hookLabel, t, hookDuration, captionStyle.fontName, captionStyle.captionColor || '#FFE600');
        drawCaption(ctx, cues, t, captionStyle);
        drawSticker(ctx, stickerImgRef.current, t, stickerStyle);
      }

      setPlayhead(t);
      const now = performance.now();
      if (!lastNotifyRef.current || now - lastNotifyRef.current > 50) {
        lastNotifyRef.current = now;
        onPlayhead?.(t);
      }
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, segments, cues, totalDuration]);

  const togglePlay = () => {
    if (!segments.length) return;
    if (isPlaying) {
      Object.values(videoElsRef.current).forEach(v => v?.pause());
      audioElRef.current?.pause();
      setIsPlaying(false);
    } else {
      const startT = playhead >= totalDuration ? 0 : playhead;
      clockRef.current = { startWall: performance.now(), startT };
      if (audioElRef.current) {
        audioElRef.current.currentTime = startT;
        audioElRef.current.play().catch(() => {});
      }
      setPlayhead(startT);
      onPlayhead?.(startT);
      setIsPlaying(true);
    }
  };

  const seekTo = (t) => {
    const maxDur = totalDuration || 999999;
    const clamped = Math.max(0, Math.min(maxDur, t));
    Object.values(videoElsRef.current).forEach(v => v?.pause());
    if (audioElRef.current) {
      audioElRef.current.currentTime = clamped;
    }
    setPlayhead(clamped);
    playheadRef.current = clamped;
    onPlayhead?.(clamped);
    clockRef.current = { startWall: performance.now(), startT: clamped };

    const plan = getDrawPlan(clamped);
    plan.forEach(({ seg, localTime }) => {
      const v = videoElsRef.current[seg.clip.id];
      if (v) {
        v.currentTime = localTime;
      }
    });

    renderAt(clamped); // immediate draw; onSeeked will repaint crisp frame when decoded
  };

  useImperativeHandle(ref, () => ({
    seekTo,
    seek: seekTo,        // callers use both names

    play: () => { if (!isPlaying) togglePlay(); },
    pause: () => { if (isPlaying) togglePlay(); },
    toggle: togglePlay,
    isPlaying: () => isPlaying,
  }));

  const handleScrubInput = (e) => {
    if (isPlaying) {
      audioElRef.current?.pause();
      setIsPlaying(false);
    }
    seekTo(parseFloat(e.target.value));
  };

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-center gap-2">
      {/* Hidden audio element for voiceover + BGM playback */}
      {audioUrl && (
        <audio
          ref={audioElRef}
          src={toMediaUrl(audioUrl)}
          preload="auto"
          playsInline
        />
      )}

      {/* Hidden decode elements -- one per clip, always mounted so metadata
          loads and pre-seek/pre-play can happen ahead of a cut/fade.
          Kept technically visible (1px, off-screen, opacity near 0) rather
          than display:none, which lets Chromium decode well past real-time
          since nothing paces it against the compositor (measured ~3-7x) --
          the wall-clock playhead above already corrects for any remaining
          drift, this just keeps it small. */}
      <div className="absolute -left-[9999px] top-0 w-px h-px overflow-hidden opacity-0" aria-hidden="true">
        {clips.map((c) => (
          <video
            key={c.id}
            ref={(el) => { if (el) videoElsRef.current[c.id] = el; }}
            src={toMediaUrl(c.source_path)}
            preload="auto"
            muted
            playsInline
            onLoadedData={() => { if (!isPlaying) renderAt(playheadRef.current); }}
            onSeeked={() => { if (!isPlaying) renderAt(playheadRef.current); }}
          />
        ))}
      </div>

      {/* Stage. This wrapper is the one that flexes: it takes whatever height
          the transport row leaves over, and the 9:16 box inside sizes itself
          against that. Sizing the 9:16 box directly off the column made it
          claim the full height and push the transport row off the pane. */}
      <div className="flex min-h-0 w-full flex-1 items-center justify-center">
        <div
          className="relative overflow-hidden rounded-2xl border border-[#363430] bg-black shadow-2xl"
          style={{ height: '100%', width: 'auto', aspectRatio: '9/16', maxWidth: '100%' }}
        >
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            className="absolute inset-0 h-full w-full"
          />
          {!metadataReady && clips.length > 0 && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/70 text-xs font-bold text-[#9C968F] backdrop-blur-sm">
              กำลังโหลดวิดีโอ...
            </div>
          )}
          {clips.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-[#6B6660]">
              เพิ่มคลิปเข้าไทม์ไลน์เพื่อดูพรีวิว
            </div>
          )}
          {metadataReady && clips.length > 0 && (
            <button
              onClick={togglePlay}
              className="group absolute inset-0 flex cursor-pointer items-center justify-center bg-black/0 transition-colors hover:bg-black/20"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-black/60 text-white opacity-0 shadow-lg transition-all group-hover:bg-[#D97757] group-hover:opacity-100">
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </div>
            </button>
          )}
        </div>
      </div>

      {metadataReady && clips.length > 0 && (
        <>
          {/* Compact mode has no scrub bar, so the button + timecode would
              otherwise sit far left of a centred preview. */}
          <div className={`flex w-full flex-shrink-0 items-center gap-2 pt-1 ${compact ? 'justify-center' : ''}`}>
            <button
              onClick={togglePlay}
              className="w-8 h-8 rounded-xl bg-[#D97757] text-white flex items-center justify-center flex-shrink-0 cursor-pointer hover:bg-[#C2683D] transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D97757]"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
            </button>
            {!compact && (
              <input
                type="range" min={0} max={totalDuration || 0} step={0.01}
                value={playhead}
                onChange={handleScrubInput}
                className="flex-1 accent-[#D97757]"
              />
            )}
            <span className="text-xs font-mono text-[#9C968F] w-20 text-right flex-shrink-0 font-bold">
              {playhead.toFixed(1)}s / {totalDuration.toFixed(1)}s
            </span>
          </div>
          {!compact && (
            <p className="flex flex-shrink-0 items-center gap-1 text-sm text-[#9C968F]">
              <Eye className="w-3.5 h-3.5 text-[#9C968F]" /> พรีวิวรวมทั้ง sequence แบบประมาณ (ฟอนต์/สีจริงยึดผลจาก Apply เท่านั้น)
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default forwardRef(SequencePlayer);
