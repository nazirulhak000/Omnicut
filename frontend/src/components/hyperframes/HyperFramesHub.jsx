import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useChannelDraft } from '../../hooks/useChannelDraft.js';
import { channelLocalStorage } from '../../lib/channelStorage.js';
import {
  Sparkles, Play, Video, ExternalLink, RefreshCw, Clock,
  Flame, Swords, MessageSquare, BarChart3, CheckCircle2,
  AlertCircle, Film, Plus, Send, Info, X, ChevronRight,
  Volume2, Music, Check, ArrowRight, Shuffle, Bot, Cpu, Wand2,
  FileText, Layers, ShieldCheck, HelpCircle
} from 'lucide-react';
import {
  getHyperFramesStatus,
  getHyperFramesStyles,
  getHyperFramesCompositions,
  createHyperFramesClip,
  openHyperFramesStudio,
  getProducts
} from '../../api';
import StylePosterMockup from './StylePosterMockup';
import HyperFramesWorkflow from './HyperFramesWorkflow.jsx';
import { useChannel } from '../../context/ChannelContext.jsx';
import {
  getProductCategoryType,
  getCategoryDisplayName,
  getDynamicPOVScenarios,
  convertAngleToPOVDialogue
} from '../../lib/dynamicPOVScenarios';

// ── Rich Editorial Metas for the 4 Approved Styles ──
const STYLE_EXTRAS = {
  vs_battle: {
    accentBorder: 'hover:border-rose-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(244,63,94,0.18)]',
    tagColor: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) + Upbeat BGM (0.14) + SFX ชก/ดาบ',
    rhythm: [
      { time: '0-3s', label: 'เปิดศึก VS', desc: 'ตัดภาพแบ่ง 2 ฝั่ง ซาวด์เปิดศึก', color: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
      { time: '3-10s', label: 'ยก 1: สปีด', desc: 'ชาร์จเทียบกัน HP บาร์ฝั่งเก่าลด', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
      { time: '10-17s', label: 'ยก 2: อุณหภูมิ', desc: 'วัดความร้อน 58°C vs 34°C', color: 'bg-red-500/20 text-red-300 border-red-500/30' },
      { time: '17-22s', label: 'ยก 3: ราคา', desc: 'เทียบราคาโปรโมชั่นหลักร้อย', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
      { time: '22-25s', label: 'K.O. ตะกร้า', desc: 'K.O. จบศึก ปักตะกร้าเหลือง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  tech_explainer: {
    accentBorder: 'hover:border-cyan-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(6,182,212,0.18)]',
    tagColor: 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) สุขุม + Ambient Tech BGM (0.12)',
    rhythm: [
      { time: '0-4s', label: 'ตั้งคำถาม', desc: 'เปิดข้อสงสัย ทำไมหัวชาร์จแรงไม่ร้อน', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
      { time: '4-15s', label: 'ผ่าโครงสร้าง', desc: 'Exploded View ชิป GaN III', color: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
      { time: '15-28s', label: 'เจาะสเปก', desc: 'เกจวัตต์และระบบระบายความร้อน', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
      { time: '28-35s', label: 'เทสจริง', desc: 'เสียบชาร์จจริง กราฟนิ่งอุณหภูมิต่ำ', color: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
      { time: '35-40s', label: 'สรุปคุ้มค่า', desc: 'เหมาะกับคนใช้หลายอุปกรณ์ ปักตะกร้า', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  meme_pas: {
    accentBorder: 'hover:border-amber-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(245,158,11,0.18)]',
    tagColor: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    audioDetail: 'พากย์ Fenrir (1.0) + มีม SFX แตรลม/Vine Boom + BGM (0.14)',
    rhythm: [
      { time: '0-4s', label: 'ฮุกปัญหาจริง', desc: 'ค่าไฟพุ่ง ปรอทแตก เตือนแล้วนะ', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
      { time: '4-10s', label: 'มีมตกใจ + Pause', desc: 'มีมเหงื่อตก ค้าง 0.8s ดึงสายตา', color: 'bg-orange-500/20 text-orange-300 border-orange-500/30' },
      { time: '10-14s', label: 'หักมุมแตรลม', desc: 'ซาวด์แตรลมเปิดตัวสินค้าแก้ปัญหา', color: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
      { time: '14-38s', label: 'จุดขายคู่มีม', desc: 'ฟีเจอร์เด่น สลับ 1 มีม 1 SFX', color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
      { time: '38-45s', label: 'ปักตะกร้าเหลือง', desc: 'CTA ชี้ตะกร้าเหลืองซ้ายล่าง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  },
  pov_chat: {
    accentBorder: 'hover:border-emerald-500/70',
    accentShadow: 'hover:shadow-[0_0_24px_rgba(16,185,129,0.18)]',
    tagColor: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    audioDetail: 'ไม่มีเสียงพากย์ (ดนตรีสดใส + Sound Effect แชท LINE เด้ง)',
    rhythm: [
      { time: '0-4s', label: 'แชทเด้งเตือน', desc: 'เสียงแชท LINE แฟนบ่นร้อน/แบตหมด', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
      { time: '4-12s', label: 'บทสนทนาดราม่า', desc: 'คนดูอ่านตาม 100% สลับพิมพ์ตอบ', color: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
      { time: '12-20s', label: 'ส่งของแก้ปัญหา', desc: 'ส่งรูป/ลิงก์แกดเจ็ตตัวช่วยเข้าแชท', color: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' },
      { time: '20-25s', label: 'แฟนปลื้มรอดตาย', desc: 'ตอบกลับว่ารอดแล้ว แบตเต็ม/เย็นเจี๊ยบ', color: 'bg-green-500/20 text-green-300 border-green-500/30' },
      { time: '25-28s', label: 'แจกพิกัดในแชท', desc: 'ส่งสติกเกอร์ชี้ตะกร้าเหลืองซ้ายล่าง', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' }
    ]
  }
};

// ── Style Metadata Map for Unique ID Generation ──
const STYLE_SLUG_MAP = {
  meme_pas: { slug: 'meme', dur: 45 },
  tech_explainer: { slug: 'explainer', dur: 40 },
  vs_battle: { slug: 'vs', dur: 25 },
  pov_chat: { slug: 'pov-chat', dur: 28 },
};

// ── Compatibility Matrix between 4 Styles and 10 Product Angles ──
const STYLE_ANGLE_MATCHES = {
  vs_battle: {
    recommendedIndices: [4, 9], // 0-indexed: 4 = เทียบของเดิม vs ของใหม่, 9 = คำนวณความคุ้มค่า
    keywords: ['เทียบ', 'vs', 'เก่า', 'ใหม่', 'คุ้มค่า', 'สู้', 'เดิม'],
    styleRationale: 'สไตล์ VS Battle มีภาษาภาพเป็นเกมต่อสู้ 2 ฝั่ง 3 ยก (Street Fighter HUD) จำเป็นต้องมีเนื้อหาที่เปรียบเทียบชัดเจนระหว่าง 2 สิ่ง',
    recommendedNames: ['Angle 5 (เทียบของเดิม vs ของใหม่)', 'Angle 10 (คำนวณความคุ้มค่าต่อวัน)']
  },
  tech_explainer: {
    recommendedIndices: [1, 5, 7], // 0-indexed: 1 = สเปกเจาะลึก, 5 = ทริกลึก, 7 = เจาะกลุ่มเฉพาะ
    keywords: ['สเปก', 'ชิป', 'ฟังก์ชัน', 'ทริก', 'เจาะลึก', 'ระบบ', 'วัตต์', 'อุณหภูมิ', 'แกดเจ็ต'],
    styleRationale: 'สไตล์ Tech Explainer มีภาษาภาพเป็นพิมพ์เขียววิศวกรรม (Exploded View / ไดอะแกรมชิป) ต้องการเนื้อหาอธิบายเชิงเทคนิค สเปก และข้อเท็จจริง',
    recommendedNames: ['Angle 2 (รีวิวสเปกเจาะลึก)', 'Angle 6 (ทริกลึก / รู้งี้ซื้อนานแล้ว)']
  },
  meme_pas: {
    recommendedIndices: [0, 6, 8, 3], // 0-indexed: 0 = ปัญหาก่อนใช้, 6 = เตือนภัย, 8 = เพื่อนเตือนเพื่อน, 3 = FOMO
    keywords: ['ปัญหา', 'เตือน', 'อย่าเพิ่งซื้อ', 'ท้อ', 'เพื่อน', 'fomo', 'ร้อน', 'แบต', 'ชีวิตเปลี่ยน'],
    styleRationale: 'สไตล์ Meme-PAS ใช้สูตร PAS (Problem-Agitate-Solution) + Meme Pause 0.8s ต้องการปัญหาคนเจอจริง มีมขยี้ความเจ็บปวด แล้วหักมุมเปิดตัวสินค้า',
    recommendedNames: ['Angle 1 (ปัญหาก่อนใช้ vs ชีวิตเปลี่ยน)', 'Angle 7 (เตือนภัยเชิงลบ / อย่าเพิ่งซื้อ!)']
  },
  pov_chat: {
    recommendedIndices: [0, 6, 8],
    keywords: ['แชท', 'แฟน', 'เพื่อน', 'ปัญหา', 'ฉุกเฉิน', 'บ่น'],
    styleRationale: 'สไตล์ POV Chat จำลองหน้าจอแชท LINE ดราม่า 5 บับเบิ้ล ไม่มีเสียงพากย์ เน้นบทสนทนา 2 คนช่วยแก้ปัญหาเฉพาะหน้า',
    recommendedNames: ['พรีเซ็ตบทแชท LINE 4 รูปแบบ (แนะนำสูงสุด)']
  }
};

// ── Note: POV Chat Scenarios are generated dynamically per product via getDynamicPOVScenarios() ──


function generateUniqueClipId(productCode, styleId, existingCompositions = [], seed = 0) {
  const p = (productCode || 'hat01').toLowerCase().trim();
  const meta = STYLE_SLUG_MAP[styleId] || { slug: 'clip', dur: 30 };
  const existingSet = new Set((existingCompositions || []).map((c) => (c.id || '').toLowerCase()));

  const baseId = `${p}-${meta.slug}-${meta.dur}s`;

  if (seed === 0 && !existingSet.has(baseId)) {
    return baseId;
  }

  let version = seed > 0 ? seed + 1 : 2;
  while (version < 100) {
    const candidate = `${baseId}-v${version}`;
    if (!existingSet.has(candidate)) {
      return candidate;
    }
    version += 1;
  }
  return `${baseId}-${Date.now().toString().slice(-4)}`;
}

// ── Smart Script Adapter by Style Blueprint ──
function adaptScriptToStyle(styleId, angle, rawScript, productName) {
  const pName = productName || 'สินค้าตัวนี้';
  const hook = (angle?.hook_title || '').trim();
  const features = (angle?.key_features || '').trim();
  const pain = (angle?.pain_point || '').trim();
  const price = (angle?.price_deal || '').trim();

  if (styleId === 'vs_battle') {
    return `[0-3s เปิดศึก VS]
${hook || `เทียบกันชัดๆ ระหว่างของเดิม VS ${pName} รุ่นใหม่ล่าสุด!`}

[3-10s ยก 1: สปีดความเร็วและประสิทธิภาพ]
ฝั่งเดิมชาร์จช้าอืดอาด หลอดเลือดลดฮวบ! ส่วน ${pName} สปีดเทอร์โบ ชาร์จแป๊บเดียวพลังพุ่งปรี๊ด!

[10-17s ยก 2: อุณหภูมิและความปลอดภัย]
${pain ? `ของเก่าเจอปัญหา ${pain}` : 'ของเก่าร้อนจัดจนน่ากลัว!'} ส่วน ${pName} คุมความร้อนนิ่งสนิท เย็นเจี๊ยบปลอดภัย 100%

[17-22s ยก 3: ราคาและความคุ้มค่า]
${price ? `ดีลเดือด: ${price}` : 'สเปกระดับท็อป แต่ราคาเบาๆ สบายกระเป๋า'} เทียบกันแล้วฝั่งใหม่ชนะขาดลอย!

[22-25s K.O. ตะกร้า]
K.O. จบศึก! พิกัดตะกร้าเหลืองซ้ายล่าง รีบกดก่อนหมดโปร!`;
  }

  if (styleId === 'tech_explainer') {
    return `[0-4s ตั้งคำถามข้อสงสัย]
${hook || `เคยสงสัยไหม ทำไม ${pName} ถึงจ่ายไฟแรงและทำงานได้เสถียรขนาดนี้?`}

[4-15s ผ่าโครงสร้าง Exploded View ชิปเซ็ต]
ความลับอยู่ที่โครงสร้างภายในและชิปรุ่นใหม่ล่าสุด ทำให้สูญเสียพลังงานน้อยลง และกระจายพลังงานได้อย่างแม่นยำ

[15-28s เจาะสเปกวัตต์และระบบความปลอดภัย]
${features || `${pName} มาพร้อมระบบตัดไฟอัตโนมัติ และเซนเซอร์วัดอุณหภูมิแบบเรียลไทม์`}

[28-35s ผลการทดสอบใช้งานจริง]
${pain ? `แก้ปัญหาเรื่อง ${pain} ได้แบบเบ็ดเสร็จ` : 'ทดสอบใช้งานต่อเนื่องหลายชั่วโมง อุณหภูมิผิวยังนิ่งสนิท'} กราฟการทำงานเสถียร 100%

[35-40s สรุปความคุ้มค่าและพิกัด]
สรุปคือตัวจบสำหรับคนที่ต้องการประสิทธิภาพระดับโปร พิกัดตะกร้าเหลืองด้านล่างครับ`;
  }

  if (styleId === 'meme_pas') {
    return `[0-4s ฮุกปัญหาจริง]
${hook || `เตือนแล้วนะ! ใครยังทนทรมานกับปัญหาเดิมๆ อยู่บ้าง?`}

[4-10s มีมตกใจ • Meme Pause 0.8s]
${pain ? `เจอปัญหา ${pain}` : 'รีบจะออกบ้าน แบตดันหมด น้ำตาจะไหล!'} [มีมเหงื่อตก ค้าง 0.8s ดึงสายตา]

[10-14s ซาวด์แตรลมเปิดตัวสินค้า]
[ซาวด์แตรลม] ตัดมาที่ตัวช่วยกู้ชีวิต ${pName}!

[14-38s จุดขายคู่มีม 1 มีม 1 SFX]
${features || 'เสียบปุ๊บ สปีดพุ่งปรี๊ด [SFX วิ่ง] เล็กพริกขี้หนู พกหัวเดียวจบครบทุกเครื่อง'}

[38-45s ปักตะกร้าเหลือง]
${price ? `ราคาโปรโมชั่น: ${price}` : 'พิกัดตะกร้าเหลืองซ้ายล่าง รีบจิ้มก่อนราคาจะปรับขึ้น!'}`;
  }

  if (styleId === 'pov_chat') {
    return convertAngleToPOVDialogue(angle, pName);
  }

  return rawScript || hook || '';
}

export default function HyperFramesHub({ onNavigateToGallery, onOpenGadgetReview }) {
  const channel = useChannel();
  const storage = useMemo(() => channelLocalStorage(), []);
  const [retained] = useState(() => { try { return JSON.parse(storage.getItem('hyperframes_create_draft') || 'null') || {}; } catch { return {}; } });
  const touched = useRef(false);
  const [activeTab, setActiveTab] = useState('styles'); // 'styles' | 'compositions' | 'create'
  const [status, setStatus] = useState(null);
  const [styles, setStyles] = useState([]);
  const [compositions, setCompositions] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);
  const [selectedStyleDetail, setSelectedStyleDetail] = useState(null); // Modal state for style deep dive

  // Form State for creating a new clip
  const [newClipId, setNewClipId] = useState(retained.newClipId || '');
  const [isManualClipId, setIsManualClipId] = useState(retained.isManualClipId || false);
  const [clipSeed, setClipSeed] = useState(0);
  const [selectedProduct, setSelectedProduct] = useState(retained.selectedProduct || '');
  const [selectedStyle, setSelectedStyle] = useState(retained.selectedStyle || 'meme_pas');
  const [selectedAngleId, setSelectedAngleId] = useState(retained.selectedAngleId || '');
  const [selectedScenarioId, setSelectedScenarioId] = useState(retained.selectedScenarioId || '');
  const [scriptText, setScriptText] = useState(retained.scriptText || '');
  const [isCreating, setIsCreating] = useState(false);
  const draftValue = { newClipId: isManualClipId ? newClipId : '', isManualClipId, selectedProduct, selectedStyle, selectedAngleId, selectedScenarioId, scriptText };
  const draft = useChannelDraft(draftValue, {
    save: value => storage.setItem('hyperframes_create_draft', JSON.stringify(value)),
    reset: value => {
      setNewClipId(value.newClipId); setIsManualClipId(value.isManualClipId);
      setSelectedProduct(value.selectedProduct); setSelectedStyle(value.selectedStyle);
      setSelectedAngleId(value.selectedAngleId); setSelectedScenarioId(value.selectedScenarioId); setScriptText(value.scriptText);
    },
  });
  useEffect(() => { if (!touched.current) draft.markSaved(draftValue); }, [selectedProduct, selectedStyle, loading]);

  const loadData = useCallback(async () => {
    try {
      setRefreshing(true);
      setActionError(null);
      const [statusRes, stylesRes, compsRes, prodsRes] = await Promise.all([
        getHyperFramesStatus().catch(() => null),
        getHyperFramesStyles().catch(() => []),
        getHyperFramesCompositions().catch(() => []),
        getProducts().catch(() => ({ products: [] }))
      ]);
      setStatus(statusRes);
      setStyles(Array.isArray(stylesRes) ? stylesRes : (stylesRes?.styles || []));
      const loadedComps = Array.isArray(compsRes) ? compsRes : (compsRes?.compositions || []);
      setCompositions(loadedComps);
      const prodsList = Array.isArray(prodsRes) ? prodsRes : (prodsRes?.products || []);
      setProducts(prodsList);

      if (prodsList.length > 0 && !selectedProduct) {
        const first = prodsList[0];
        const initialVal = (first.product_code || first.id || first.code || 'hat01').toLowerCase();
        setSelectedProduct(initialVal);
      }
    } catch (err) {
      setActionError('ไม่สามารถโหลดข้อมูล HyperFrames ได้ กรุณาลองใหม่อีกครั้ง');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedProduct]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-generate unique clip ID whenever product/style changes or compositions load
  useEffect(() => {
    if (!isManualClipId && selectedProduct && selectedStyle) {
      const generated = generateUniqueClipId(selectedProduct, selectedStyle, compositions, clipSeed);
      setNewClipId(generated);
    }
  }, [selectedProduct, selectedStyle, compositions, clipSeed, isManualClipId]);

  // Find active product object and its angles
  const currentProductObj = useMemo(() => {
    return products.find((p) => {
      const code = (p.product_code || p.id || p.code || '').toLowerCase();
      return code === selectedProduct.toLowerCase();
    });
  }, [products, selectedProduct]);

  // Dynamic POV Scenarios matching current product category and angles
  const activePOVScenarios = useMemo(() => {
    return getDynamicPOVScenarios(currentProductObj);
  }, [currentProductObj]);

  const currentProductCategory = useMemo(() => {
    return getProductCategoryType(currentProductObj);
  }, [currentProductObj]);

  const currentCategoryName = useMemo(() => {
    return getCategoryDisplayName(currentProductCategory);
  }, [currentProductCategory]);

  const availableAngles = useMemo(() => {
    return Array.isArray(currentProductObj?.angles) ? currentProductObj.angles : [];
  }, [currentProductObj]);

  // Categorize Angles into "Recommended for this style" vs "Others"
  const categorizedAngles = useMemo(() => {
    const matchMeta = STYLE_ANGLE_MATCHES[selectedStyle] || { recommendedIndices: [], keywords: [] };
    const recommended = [];
    const others = [];

    availableAngles.forEach((ang, idx) => {
      const isIndexRec = matchMeta.recommendedIndices.includes(idx);
      const combined = `${ang.angle_name || ''} ${ang.hook_title || ''}`.toLowerCase();
      const hasKey = matchMeta.keywords.some((k) => combined.includes(k.toLowerCase()));

      if (isIndexRec || hasKey) {
        recommended.push({ ...ang, originalIndex: idx, isTopMatch: isIndexRec });
      } else {
        others.push({ ...ang, originalIndex: idx, isTopMatch: false });
      }
    });

    return { recommended, others };
  }, [availableAngles, selectedStyle]);

  // Selected angle object
  const activeAngleObj = useMemo(() => {
    if (!selectedAngleId) return null;
    return availableAngles.find((a, idx) => (a.angle_id || a.id || `ang-${idx}`) === selectedAngleId);
  }, [selectedAngleId, availableAngles]);

  // Active angle index
  const activeAngleIndex = useMemo(() => {
    if (!selectedAngleId) return -1;
    return availableAngles.findIndex((a, idx) => (a.angle_id || a.id || `ang-${idx}`) === selectedAngleId);
  }, [selectedAngleId, availableAngles]);

  // Calculate real-time compatibility score and advice
  const compatibilityInfo = useMemo(() => {
    if (selectedStyle === 'pov_chat') {
      const pDisplayName = currentProductObj?.name || selectedProduct.toUpperCase();
      if (selectedScenarioId) {
        return {
          score: 1.0,
          level: 'high',
          tag: '✓ ความเข้ากันได้ 100% (บทแชท LINE ตรงสินค้า)',
          badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
          message: `บทสนทนาจำลอง 2 คนนี้ตรงกับสินค้า ${pDisplayName} (${currentCategoryName}) และหน้าจอ LINE Chat UI อย่างสมบูรณ์แบบ คนดูอ่านตามได้ 100% โดยไม่ต้องพากย์เสียง`
        };
      }
      return {
        score: 0.5,
        level: 'moderate',
        tag: 'ℹ️ สไตล์นี้ไม่มีเสียงพากย์',
        badgeColor: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
        message: `สไตล์ POV Chat เน้นแชท LINE แนะนำให้เลือก "บทแชท LINE สำเร็จรูป (${currentCategoryName})" ด้านบน หรือเลือก Angle แล้วกด "แปลงเป็นแชท LINE"`
      };
    }

    if (!activeAngleObj) {
      return null;
    }

    const matchMeta = STYLE_ANGLE_MATCHES[selectedStyle];
    if (!matchMeta) return null;

    const isRec = matchMeta.recommendedIndices.includes(activeAngleIndex);
    if (isRec) {
      return {
        score: 1.0,
        level: 'high',
        tag: '✓ ความเข้ากันได้ 100% (เนื้อหาและภาษาภาพสอดคล้องกัน)',
        badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        message: `มุมมองนี้มีเนื้อหาตรงกับโครงสร้างของสไตล์ ${selectedStyle === 'vs_battle' ? 'VS Battle' : selectedStyle === 'tech_explainer' ? 'Tech Explainer' : 'Meme-PAS'} พอดีเป๊ะ ตัดแล้วภาพกับเสียงจะไม่ขัดกันแน่นอน`
      };
    }

    const combined = `${activeAngleObj.angle_name || ''} ${activeAngleObj.hook_title || ''}`.toLowerCase();
    const hasKey = matchMeta.keywords.some((k) => combined.includes(k.toLowerCase()));
    if (hasKey) {
      return {
        score: 0.6,
        level: 'moderate',
        tag: 'ℹ️ ความเข้ากันได้ 60% (ประยุกต์ใช้ได้)',
        badgeColor: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
        message: 'มุมมองนี้สามารถนำมาใช้ได้ แต่จังหวะอาจยังไม่ลงล็อกกับไทม์ไลน์ แนะนำให้กดปุ่ม "แปลงบทให้ตรงจังหวะสไตล์" ด้านล่าง'
      };
    }

    return {
      score: 0.25,
      level: 'low',
      tag: '⚠️ เสี่ยงขัดแย้งกับภาพ (ความเข้ากันได้ต่ำ 25%)',
      badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      message: `${matchMeta.styleRationale} แต่ Angle ที่เลือกนี้เป็นอีกโทนหนึ่ง แนะนำให้เลือก ${matchMeta.recommendedNames[0]} หรือกด "แปลงบทให้ตรงจังหวะสไตล์"`
    };
  }, [selectedStyle, activeAngleObj, activeAngleIndex, selectedScenarioId]);

  // Uniqueness check for current input
  const isDuplicateId = useMemo(() => {
    if (!newClipId.trim()) return false;
    return compositions.some((c) => (c.id || '').toLowerCase() === newClipId.trim().toLowerCase());
  }, [newClipId, compositions]);

  const suggestedUniqueId = useMemo(() => {
    return generateUniqueClipId(selectedProduct, selectedStyle, compositions, clipSeed + 1);
  }, [selectedProduct, selectedStyle, compositions, clipSeed]);

  const handleRegenerateId = () => {
    const nextSeed = clipSeed + 1;
    setClipSeed(nextSeed);
    setIsManualClipId(false);
    const regenerated = generateUniqueClipId(selectedProduct, selectedStyle, compositions, nextSeed);
    setNewClipId(regenerated);
  };

  const handleSelectAngle = (angleId) => {
    setSelectedAngleId(angleId);
    if (!angleId) return;
    const ang = availableAngles.find((a, idx) => (a.angle_id || a.id || `ang-${idx}`) === angleId);
    if (ang) {
      const filledText = (ang.script_text || `${ang.hook_title || ''}\n${ang.key_features || ''}`).trim();
      setScriptText(filledText);
    }
  };

  const handleSelectScenario = (scenarioId) => {
    setSelectedScenarioId(scenarioId);
    if (!scenarioId) return;
    const sc = activePOVScenarios.find((s) => s.id === scenarioId);
    if (sc) {
      setScriptText(sc.script);
    }
  };

  // 1-Click Script Adaptation to Current Style
  const handleAdaptScript = () => {
    const pName = currentProductObj?.name || selectedProduct.toUpperCase();
    const adapted = adaptScriptToStyle(selectedStyle, activeAngleObj, scriptText, pName);
    setScriptText(adapted);
    setActionSuccess(`ปรับโครงสร้างบทให้ตรงกับจังหวะไทม์ไลน์ของ ${selectedStyle.toUpperCase()} เรียบร้อยแล้ว`);
    setTimeout(() => setActionSuccess(null), 4000);
  };

  const handleOpenStudio = () => {
    setActionSuccess('กำลังเปิด HyperFrames Studio ในแท็บใหม่...');
    openHyperFramesStudio(3002).catch(() => {});
    setTimeout(() => setActionSuccess(null), 4000);
  };

  const handleCreateClip = async (e) => {
    e.preventDefault();
    if (!newClipId.trim()) {
      setActionError('กรุณาระบุรหัสคลิป (เช่น hat01-meme-45s)');
      return;
    }
    if (isDuplicateId) {
      setActionError(`รหัสคลิป "${newClipId.trim()}" มีอยู่แล้วในคลัง กรุณากดสุ่มรหัสใหม่หรือเปลี่ยนเวอร์ชัน`);
      return;
    }
    try {
      setIsCreating(true);
      setActionError(null);
      setActionSuccess(null);
      const res = await draft.run(() => createHyperFramesClip({
        clip_id: newClipId.trim(),
        product: selectedProduct.toLowerCase(),
        script: scriptText.trim() || undefined,
        style: selectedStyle
      }));
      storage.removeItem('hyperframes_create_draft');
      draft.markSaved({ ...draftValue, newClipId: '', isManualClipId: false, scriptText: '', selectedAngleId: '', selectedScenarioId: '' });
      setActionSuccess(`สร้างดราฟต์สำเร็จ: ${res.clip_id} เปิดแต่งต่อใน Compositions ได้ทันที`);
      setIsManualClipId(false);
      setScriptText('');
      setSelectedAngleId('');
      setSelectedScenarioId('');
      await loadData();
      setActiveTab('compositions');
    } catch (err) {
      setActionError('สร้างคลิปไม่สำเร็จ: ' + (err.friendlyMessage || err.message));
    } finally {
      setIsCreating(false);
    }
  };

  const getStyleIcon = (styleId) => {
    switch (styleId) {
      case 'meme_pas': return <Flame className="w-5 h-5 text-amber-400" />;
      case 'tech_explainer': return <BarChart3 className="w-5 h-5 text-cyan-400" />;
      case 'vs_battle': return <Swords className="w-5 h-5 text-rose-400" />;
      case 'pov_chat': return <MessageSquare className="w-5 h-5 text-emerald-400" />;
      default: return <Sparkles className="w-5 h-5 text-[#25F4EE]" />;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-[#080B11] text-slate-100 p-6 space-y-6">
      <HyperFramesWorkflow key={channel?.channelId || 'main'} products={products}
        channelId={channel?.channelId || 'main'} onOpenGallery={onNavigateToGallery} onOpenGadgetReview={onOpenGadgetReview} />
      <details className="rounded-xl border border-white/10 bg-[#0D111A]">
        <summary className="cursor-pointer px-4 py-3 text-slate-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#25F4EE]">เปิดเครื่องมือเดิมและตัวอย่างสไตล์</summary>
        <div className="space-y-6 border-t border-white/10 p-4">
          <p className="text-slate-400">ส่วนนี้ใช้ดูตัวอย่างสไตล์และเปิด composition เดิมใน Studio ส่วนงานใหม่ที่ส่งออกเข้า Gallery และคิวโพสต์ ให้เริ่มจาก flow ด้านบน ตัวอย่างสไตล์เป็นแนวทางสำหรับ AI ภาพจริงต้องตรวจใน revision ที่ส่งกลับ</p>
      {/* ── Header & Status Bar (OmniCut Pro Studio Branding) ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-[#25F4EE]/10 to-[#FE2C55]/10 border border-[#25F4EE]/20 shadow-[0_0_15px_rgba(37,244,238,0.1)]">
              <Sparkles className="w-6 h-6 text-[#25F4EE]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                HyperFrames Creative Studio
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#FE2C55]/10 text-[#FE2C55] border border-[#FE2C55]/20 font-medium">
                  Web-Animation 9:16
                </span>
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                ตัวอย่างสไตล์และเครื่องมือ Studio เดิมสำหรับงาน Web Animation แนวตั้ง
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Health Pill */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0D111A] border border-white/[0.08] text-xs text-slate-300">
            <span className={`w-2 h-2 rounded-full ${status?.ready ? 'bg-cyan-400' : 'bg-amber-400'}`} />
            <span>{refreshing ? 'กำลังตรวจข้อมูลเครื่องมือเดิม' : status?.ready ? 'พบ dependencies เครื่องมือเดิม' : 'ยังไม่ยืนยันเครื่องมือเดิม'}</span>
          </div>

          <a
            href="http://127.0.0.1:3002/#project/_HyperFrames_Studio"
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleOpenStudio}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-[#FE2C55] to-rose-600 hover:brightness-110 text-white font-semibold text-sm transition-all shadow-md shadow-[#FE2C55]/20"
          >
            <ExternalLink className="w-4 h-4" />
            เปิด HyperFrames Studio
          </a>

          <button
            type="button"
            onClick={loadData}
            disabled={refreshing}
            className="p-2 rounded-lg bg-[#0D111A] border border-white/[0.08] hover:bg-white/[0.05] text-slate-300 transition-colors"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* ── Toast Messages ── */}
      {actionError && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 text-sm animate-in fade-in">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span className="flex-1">{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} className="text-rose-400 hover:text-white">✕</button>
        </div>
      )}
      {actionSuccess && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-200 text-sm animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="flex-1">{actionSuccess}</span>
          <button type="button" onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {/* ── Tab Switcher (Neon Cyan Active Accent) ── */}
      <div className="flex border-b border-white/[0.08] gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('styles')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'styles'
              ? 'border-[#25F4EE] text-[#25F4EE] bg-[#25F4EE]/5 font-semibold'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Flame className="w-4 h-4" />
          4 สไตล์ที่อนุมัติ (Approved Styles)
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('compositions')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'compositions'
              ? 'border-[#25F4EE] text-[#25F4EE] bg-[#25F4EE]/5 font-semibold'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Film className="w-4 h-4" />
          คลังคลิป Compositions ({compositions.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('create')}
          className={`flex items-center gap-2 px-4 py-2.5 font-medium text-sm border-b-2 transition-all ${
            activeTab === 'create'
              ? 'border-[#25F4EE] text-[#25F4EE] bg-[#25F4EE]/5 font-semibold'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <Plus className="w-4 h-4" />
          ดูแบบฟอร์มอ้างอิงเดิม
        </button>
      </div>

      {/* ── Content: Tab 1 (Approved Styles) ── */}
      {activeTab === 'styles' && (
        <div className="space-y-5">
          {/* Channel Golden Rule Banner */}
          <div className="p-4 rounded-xl bg-gradient-to-r from-[#0D111A] via-[#0D111A]/95 to-[#25F4EE]/5 border border-white/[0.08] text-sm text-slate-300 flex items-start gap-3 shadow-md">
            <span className="text-xl">⭐</span>
            <div>
              <span className="font-semibold text-white">กฎเหล็ก 4 สไตล์ไวรัลคุณภาพสูง:</span> ทุกสไตล์คราฟต์ภายใต้แนวคิด
              <span className="text-amber-400 font-medium"> "เหมือนคนตัด ไม่ใช่ AI ตัด"</span> — ห้ามใช้การ์ดมืดๆ ห้าม pill สีฟ้า ห้ามพื้นหลังดำโล่ง และห้ามไอคอนเวกเตอร์วาดเอง ใช้ฉลากจริง วิดีโอจริง มีมจริง จังหวะ Meme Pause 0.8s และ HUD เกมต่อสู้แบบมีชีวิต
            </div>
          </div>

          {/* 4 Approved Styles Showcase Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {(Array.isArray(styles) ? styles : []).map((st) => {
              const extras = STYLE_EXTRAS[st.id] || {
                accentBorder: 'hover:border-slate-700',
                accentShadow: '',
                tagColor: 'bg-white/[0.05] text-slate-300 border-white/[0.1]',
                audioDetail: st.has_voiceover ? 'มีเสียงพากย์ Fenrir (1.0)' : 'ดนตรีล้วน',
                rhythm: []
              };

              return (
                <div
                  key={st.id}
                  className={`p-5 rounded-2xl bg-[#0D111A]/90 border border-white/[0.08] transition-all duration-300 flex flex-col sm:flex-row gap-5 shadow-lg group hover:border-[#25F4EE]/40 ${extras.accentShadow}`}
                >
                  {/* Left Column: 9:16 Visual Poster Frame */}
                  <div className="w-full sm:w-44 md:w-48 shrink-0 flex flex-col items-center gap-2">
                    <StylePosterMockup
                      styleId={st.id}
                      onPreviewClick={() => setSelectedStyleDetail(st)}
                    />
                    <button
                      type="button"
                      onClick={() => setSelectedStyleDetail(st)}
                      className="text-[11px] text-slate-400 hover:text-[#25F4EE] font-medium transition-colors"
                    >
                      เปิดดูตัวอย่างและโครงสร้าง
                    </button>
                  </div>

                  {/* Right Column: Editorial Intelligence & Rhythm */}
                  <div className="flex-1 flex flex-col justify-between space-y-3.5 min-w-0">
                    <div className="space-y-3">
                      {/* Header: Title + Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-lg bg-[#080B11] border border-white/[0.08] shrink-0">
                            {getStyleIcon(st.id)}
                          </div>
                          <div>
                            <h3 className="font-semibold text-white text-base tracking-tight">{st.name}</h3>
                            <p className="text-xs text-slate-400">{st.tagline}</p>
                          </div>
                        </div>
                        <span className={`text-xs px-2.5 py-0.5 rounded-full border font-medium shrink-0 ${extras.tagColor}`}>
                          {st.badge}
                        </span>
                      </div>

                      {/* Visual Beat-by-Beat Timeline Rhythm */}
                      <div className="space-y-1.5">
                        <span className="text-[11px] text-slate-400 font-medium block">
                          สูตรจังหวะการตัด (Beat-by-Beat Timeline):
                        </span>
                        <div className="flex flex-wrap items-center gap-1.5 py-1">
                          {extras.rhythm.map((step, idx) => (
                            <React.Fragment key={idx}>
                              <span
                                className={`px-2 py-0.5 rounded-md text-[11px] font-mono border font-medium cursor-help transition-transform hover:scale-105 ${step.color}`}
                                title={step.desc}
                              >
                                {step.time} {step.label}
                              </span>
                              {idx < extras.rhythm.length - 1 && (
                                <span className="text-slate-600 text-xs">➔</span>
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>

                      {/* Formula Detail Summary */}
                      <div className="p-2.5 rounded-lg bg-[#080B11]/70 border border-white/[0.06] text-xs text-slate-300 leading-relaxed">
                        {st.formula}
                      </div>

                      {/* Specs DNA Bar */}
                      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400 pt-1">
                        <div>
                          <span className="text-slate-500">ความยาว:</span> ~{st.recommended_duration_sec} วินาที
                        </div>
                        <div className="truncate" title={extras.audioDetail}>
                          <span className="text-slate-500">ระบบเสียง:</span> {st.has_voiceover ? 'พากย์ Fenrir (1.0)' : 'ดนตรีล้วน'}
                        </div>
                        <div className="col-span-2 truncate">
                          <span className="text-slate-500">คลิปตัวอย่าง:</span>{' '}
                          <span className="text-[#25F4EE] font-mono text-[11px]">{st.reference}</span>
                        </div>
                      </div>
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="pt-3 border-t border-white/[0.08] flex items-center justify-between gap-2">
                      <span className="text-xs text-emerald-400 font-medium truncate" title={st.pros}>
                        {st.pros}
                      </span>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={() => setSelectedStyleDetail(st)}
                          className="px-3 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs font-medium text-slate-300 border border-white/[0.08] transition-colors"
                        >
                          ดูรายละเอียด
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedStyle(st.id);
                            setActiveTab('create');
                          }}
                          className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-[#25F4EE] to-[#00D2C4] hover:brightness-110 text-xs font-bold text-slate-950 shadow-sm transition-all"
                        >
                          ดูแบบฟอร์มอ้างอิง
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Content: Tab 2 (Compositions Gallery) ── */}
      {activeTab === 'compositions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-400">
              พบ {(Array.isArray(compositions) ? compositions : []).length} รายการในสตูดิโอ (จัดเก็บที่ <code className="text-slate-300">03_Projects/_HyperFrames_Studio/compositions/</code>)
            </p>
            <a
              href="http://127.0.0.1:3002/#project/_HyperFrames_Studio"
              target="_blank"
              rel="noopener noreferrer"
              onClick={handleOpenStudio}
              className="text-xs text-[#25F4EE] hover:brightness-125 flex items-center gap-1 font-medium transition-all"
            >
              เปิดหน้าต่าง HyperFrames Studio Live Preview ↗
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(Array.isArray(compositions) ? compositions : []).map((comp) => {
              return (
                <div
                  key={comp.id}
                  className="p-4 rounded-xl bg-[#0D111A]/90 border border-white/[0.08] hover:border-[#25F4EE]/40 transition-all flex flex-col justify-between space-y-4 shadow-md"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-white text-sm truncate" title={comp.id}>
                        {comp.id}
                      </h3>
                      <span className="text-xs px-2 py-0.5 rounded bg-[#080B11] text-slate-300 font-mono border border-white/[0.08]">
                        {comp.duration}s
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 truncate">
                      สินค้า: <span className="text-[#25F4EE] uppercase font-semibold">{comp.product}</span>
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-slate-500">
                      <span>อัปเดต: {comp.updated_at?.split('T')[0]}</span>
                      {comp.has_vo && <span className="text-[#25F4EE]">• มีเสียงพากย์</span>}
                    </div>
                  </div>

                  <p className="pt-3 border-t border-white/[0.08] text-xs text-slate-400">เปิดตรวจ composition เดิมใน Studio แล้วส่งเป็น revision ผ่าน flow ด้านบนก่อนเรนเดอร์และส่งออก</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Content: Tab 3 (Create New Clip Draft) ── */}
      {activeTab === 'create' && (
        <div className="max-w-3xl space-y-5">
          {/* ── AI Multi-Agent Workflow Explainer Card ── */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-[#0D111A] via-[#080B11] to-[#25F4EE]/5 border border-white/[0.08] space-y-3 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-[#25F4EE]" />
                <span className="text-xs font-bold text-white tracking-wide uppercase">
                  ขั้นตอนร่างงานของเครื่องมือเดิม
                </span>
              </div>
              <span className="text-[11px] text-[#25F4EE] font-mono font-medium">
                แบบอ้างอิงเดิม
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              {/* Step 1: Faster-Whisper */}
              <div className="p-3 rounded-xl bg-[#080B11]/80 border border-white/[0.06] space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/30 flex items-center justify-center font-bold text-[10px]">
                    1
                  </span>
                  <span className="font-semibold text-white">Faster-Whisper</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  การทำ timing ต้องมีเสียงพากย์จริงและตรวจผล ไม่ใช่หลักฐานว่าคลิปพร้อมส่งออก
                </p>
              </div>

              {/* Step 2: Creative AI Agent */}
              <div className="p-3 rounded-xl bg-[#080B11]/80 border border-[#25F4EE]/30 space-y-1 shadow-[0_0_12px_rgba(37,244,238,0.06)]">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[#25F4EE] text-slate-950 flex items-center justify-center font-bold text-[10px]">
                    2
                  </span>
                  <span className="font-semibold text-[#25F4EE]">Creative AI Agent</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">
                  ให้ AI (Antigravity/Claude) เขียนแต่ง CSS โมชั่น หรือกด <kbd className="px-1 py-0.5 rounded bg-white/10 text-white font-mono text-[10px]">⌘K</kbd> ใน Studio จัดเลย์เอาต์สด
                </p>
              </div>

              {/* Step 3: Chrome Headless Renderer */}
              <div className="p-3 rounded-xl bg-[#080B11]/80 border border-white/[0.06] space-y-1">
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-[#FE2C55]/10 text-[#FE2C55] border border-[#FE2C55]/30 flex items-center justify-center font-bold text-[10px]">
                    3
                  </span>
                  <span className="font-semibold text-white">Chrome Headless</span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  งานใหม่เรนเดอร์จาก revision ที่ยอมรับแล้ว ตรวจ MP4 1080x1920 ที่ 30 FPS และยืนยันคลิปจริงก่อนส่งออกเข้า Gallery
                </p>
              </div>
            </div>
          </div>

          {/* ── Form Card ── */}
          <div className="bg-[#0D111A]/90 border border-white/[0.08] p-6 rounded-2xl space-y-6 shadow-xl">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Plus className="w-5 h-5 text-[#25F4EE]" />
                แบบฟอร์มอ้างอิงของเครื่องมือเดิม
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                ใช้ flow ด้านบนเพื่อสร้างงานใหม่ที่ผูกสินค้าและ Angle แบบฟอร์มนี้เก็บไว้ดูแนวทางเดิม และไม่ใช้ส่งงานเข้าคิวโพสต์
              </p>
            </div>

            <form onSubmit={handleCreateClip} onChange={() => { touched.current = true; }} className="space-y-4">
              <fieldset disabled className="contents">
              {/* Clip ID Auto Generator Field */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    รหัสคลิป (Clip ID) *
                  </label>
                  <div className="flex items-center gap-2">
                    {/* Uniqueness Status Pill */}
                    {newClipId.trim() && (
                      isDuplicateId ? (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 font-medium flex items-center gap-1">
                          <AlertCircle className="w-3 h-3" />
                          รหัสซ้ำ มีในคลังแล้ว
                        </span>
                      ) : (
                        <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          รหัสไม่ซ้ำ พร้อมใช้งาน
                        </span>
                      )
                    )}

                    <button
                      type="button"
                      onClick={handleRegenerateId}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 hover:text-[#25F4EE] border border-white/[0.08] transition-colors flex items-center gap-1 cursor-pointer"
                      title="สุ่มรหัสใหม่ที่ไม่ซ้ำ"
                    >
                      <Shuffle className="w-3 h-3" />
                      สุ่มรหัสใหม่
                    </button>
                  </div>
                </div>

                <div className="relative">
                  <input
                    type="text"
                    value={newClipId}
                    onChange={(e) => {
                      setNewClipId(e.target.value);
                      setIsManualClipId(true);
                    }}
                    placeholder="เช่น hat01-meme-45s หรือ ess02-vs-25s-v2"
                    className={`w-full px-3.5 py-2.5 rounded-xl bg-[#080B11] border text-slate-100 text-sm focus:outline-none transition-colors font-mono ${
                      isDuplicateId
                        ? 'border-rose-500/80 focus:border-rose-500'
                        : 'border-white/[0.1] focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE]/40'
                    }`}
                    required
                  />
                </div>

                {isDuplicateId && (
                  <p className="text-xs text-rose-400 mt-1.5 flex items-center gap-1.5">
                    <span>รหัสนี้ถูกใช้งานแล้วในสตูดิโอ</span>
                    <button
                      type="button"
                      onClick={() => {
                        setNewClipId(suggestedUniqueId);
                        setIsManualClipId(false);
                      }}
                      className="text-[#25F4EE] underline hover:no-underline font-mono cursor-pointer"
                    >
                      คลิกเพื่อเปลี่ยนเป็น {suggestedUniqueId}
                    </button>
                  </p>
                )}
              </div>

              {/* Product and Style Selectors */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    สินค้าเป้าหมาย *
                  </label>
                  <select
                    value={selectedProduct}
                    onChange={(e) => {
                      setSelectedProduct(e.target.value);
                      setIsManualClipId(false);
                      setSelectedAngleId('');
                      setSelectedScenarioId('');
                    }}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-sm focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE]/40 focus:outline-none"
                  >
                    <option value="hat01">HAT01 (Hatari T16M1 พัดลมตั้งโต๊ะ)</option>
                    <option value="ess02">ESS02 (Essager 30W/65W หัวชาร์จ GaN)</option>
                    <option value="goc01">GOC01 (Gocomma Fan)</option>
                    {(Array.isArray(products) ? products : []).map((p) => {
                      const code = (p.product_code || p.id || p.code || '').toLowerCase();
                      if (!code || ['hat01', 'ess02', 'goc01'].includes(code)) return null;
                      const displayName = p.name || p.title || p.product_name || code.toUpperCase();
                      return (
                        <option key={p.id || p.code || code} value={code}>
                          {code.toUpperCase()} ({displayName})
                        </option>
                      );
                    })}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    สไตล์ที่ต้องการ *
                  </label>
                  <select
                    value={selectedStyle}
                    onChange={(e) => {
                      setSelectedStyle(e.target.value);
                      setIsManualClipId(false);
                    }}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-sm focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE]/40 focus:outline-none"
                  >
                    <option value="meme_pas">Meme-PAS (รีวิวสายมีม 45s)</option>
                    <option value="tech_explainer">Tech Explainer (สาย Vox เจาะลึก 40s)</option>
                    <option value="vs_battle">VS Battle (สายเกมต่อสู้ 25s)</option>
                    <option value="pov_chat">POV Chat Story (ไม่มีเสียงพากย์ 28s)</option>
                  </select>
                </div>
              </div>

              {/* ── Script Sourcing Tools: Product Angles & LINE Scenarios ── */}
              <div className="p-4 rounded-xl bg-[#080B11]/90 border border-white/[0.08] space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#25F4EE] flex items-center gap-1.5">
                    <Wand2 className="w-3.5 h-3.5" />
                    แหล่งที่มาบทสคริปต์ (Script Sourcing & Smart Match)
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {selectedStyle === 'pov_chat'
                      ? `มี 4 บทแชท LINE แนะนำเฉพาะสินค้า (${currentCategoryName})`
                      : availableAngles.length > 0
                        ? `คลังบท Angle สินค้านี้ ${availableAngles.length} บท (${categorizedAngles.recommended.length} แนะนำตรงสไตล์)`
                        : 'พิมพ์บทเองหรือใช้บทดั้งเดิม'}
                  </span>
                </div>

                {selectedStyle === 'pov_chat' ? (
                  <div className="space-y-3">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-[11px] font-medium text-slate-300">
                          1) เลือกบทแชท LINE แนะนำตรงสินค้า (หมวด: {currentCategoryName})
                        </label>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#25F4EE]/10 text-[#25F4EE] border border-[#25F4EE]/20 font-mono">
                          {activePOVScenarios.length} รูปแบบเฉพาะ {selectedProduct.toUpperCase()}
                        </span>
                      </div>
                      <select
                        value={selectedScenarioId}
                        onChange={(e) => handleSelectScenario(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-lg bg-[#0D111A] border border-white/[0.1] text-xs text-slate-200 focus:border-[#25F4EE] focus:outline-none"
                      >
                        <option value="">-- เลือก Scenario บทแชท LINE เพื่อกรอกลงช่องข้อความ --</option>
                        {activePOVScenarios.map((sc) => (
                          <option key={sc.id} value={sc.id}>
                            💬 [{sc.badge}] {sc.title}
                          </option>
                        ))}
                      </select>
                    </div>

                    {availableAngles.length > 0 && (
                      <div className="pt-2.5 border-t border-white/[0.06] space-y-1.5">
                        <div className="flex items-center justify-between">
                          <label className="block text-[11px] text-slate-400">
                            2) หรือเลือกจาก Angle ของสินค้า ({availableAngles.length} บท) แล้วแปลงเป็นบทแชท LINE 2 คน:
                          </label>
                          {selectedAngleId && (
                            <button
                              type="button"
                              onClick={() => {
                                const pName = currentProductObj?.name || selectedProduct.toUpperCase();
                                const adapted = convertAngleToPOVDialogue(activeAngleObj, pName);
                                setScriptText(adapted);
                                setSelectedScenarioId('');
                                setActionSuccess(`แปลง Angle "${activeAngleObj?.angle_name || ''}" เป็นบทแชท LINE เรียบร้อยแล้ว`);
                                setTimeout(() => setActionSuccess(null), 4000);
                              }}
                              className="text-[11px] font-semibold text-[#25F4EE] hover:brightness-125 flex items-center gap-1 cursor-pointer"
                            >
                              <Wand2 className="w-3 h-3" />
                              แปลงเป็นแชท LINE
                            </button>
                          )}
                        </div>
                        <select
                          value={selectedAngleId}
                          onChange={(e) => {
                            const val = e.target.value;
                            setSelectedAngleId(val);
                            if (val) {
                              const ang = availableAngles.find((a, idx) => (a.angle_id || a.id || `ang-${idx}`) === val);
                              if (ang) {
                                const pName = currentProductObj?.name || selectedProduct.toUpperCase();
                                const adapted = convertAngleToPOVDialogue(ang, pName);
                                setScriptText(adapted);
                                setSelectedScenarioId('');
                              }
                            }
                          }}
                          className="w-full px-3 py-2 rounded-lg bg-[#0D111A] border border-white/[0.1] text-xs text-slate-200 focus:border-[#25F4EE] focus:outline-none"
                        >
                          <option value="">-- หรือเลือก Angle เพื่อแปลงเป็นบทสนทนาแชท LINE อัตโนมัติ --</option>
                          {availableAngles.map((ang, idx) => {
                            const angId = ang.angle_id || ang.id || `ang-${idx}`;
                            const name = ang.angle_name || `Angle ${idx + 1}`;
                            const hook = ang.hook_title ? ` (${ang.hook_title.slice(0, 32)}...)` : '';
                            return (
                              <option key={angId} value={angId}>
                                • {name}{hook}
                              </option>
                            );
                          })}
                        </select>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">
                      ดึงบทสคริปต์จาก Angle ของสินค้า (จัดกลุ่มตามความเข้ากันได้ของสไตล์)
                    </label>
                    <select
                      value={selectedAngleId}
                      onChange={(e) => handleSelectAngle(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-lg bg-[#0D111A] border border-white/[0.1] text-xs text-slate-200 focus:border-[#25F4EE] focus:outline-none"
                    >
                      <option value="">
                        {availableAngles.length > 0
                          ? `-- เลือก Angle ของสินค้าเพื่อดึงบทสคริปต์ (${availableAngles.length} บท) --`
                          : '-- ไม่พบบท Angle ที่บันทึกไว้สำหรับสินค้านี้ --'}
                      </option>

                      {/* Optgroup 1: Recommended for this style */}
                      {categorizedAngles.recommended.length > 0 && (
                        <optgroup label={`⭐ แนะนำตรงสไตล์ 100% (เนื้อหาและภาษาภาพสอดคล้องกัน)`}>
                          {categorizedAngles.recommended.map((ang) => {
                            const angId = ang.angle_id || ang.id || `ang-${ang.originalIndex}`;
                            const name = ang.angle_name || `Angle ${ang.originalIndex + 1}`;
                            const hook = ang.hook_title ? ` (${ang.hook_title.slice(0, 34)}...)` : '';
                            return (
                              <option key={angId} value={angId}>
                                ⭐ {name}{hook}
                              </option>
                            );
                          })}
                        </optgroup>
                      )}

                      {/* Optgroup 2: Other angles requiring adaptation */}
                      {categorizedAngles.others.length > 0 && (
                        <optgroup label={`มุมมองอื่นๆ (ต้องกดแปลงบทให้เข้ากับจังหวะไทม์ไลน์)`}>
                          {categorizedAngles.others.map((ang) => {
                            const angId = ang.angle_id || ang.id || `ang-${ang.originalIndex}`;
                            const name = ang.angle_name || `Angle ${ang.originalIndex + 1}`;
                            const hook = ang.hook_title ? ` (${ang.hook_title.slice(0, 34)}...)` : '';
                            return (
                              <option key={angId} value={angId}>
                                • {name}{hook}
                              </option>
                            );
                          })}
                        </optgroup>
                      )}
                    </select>
                  </div>
                )}

                {/* ── Real-time Compatibility Guard & Alert Banner ── */}
                {compatibilityInfo && (
                  <div className={`p-3 rounded-xl border text-xs space-y-1.5 transition-all animate-in fade-in ${
                    compatibilityInfo.level === 'high'
                      ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200'
                      : compatibilityInfo.level === 'moderate'
                        ? 'bg-sky-950/30 border-sky-500/40 text-sky-200'
                        : 'bg-amber-950/30 border-amber-500/40 text-amber-200'
                  }`}>
                    <div className="flex items-center justify-between gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold border ${compatibilityInfo.badgeColor}`}>
                        {compatibilityInfo.tag}
                      </span>
                      {compatibilityInfo.level !== 'high' && (
                        <button
                          type="button"
                          onClick={handleAdaptScript}
                          className="text-[11px] font-semibold text-[#25F4EE] hover:underline flex items-center gap-1 cursor-pointer"
                        >
                          <Wand2 className="w-3 h-3" />
                          กดแปลงบทให้ตรงสไตล์
                        </button>
                      )}
                    </div>
                    <p className="text-[11px] leading-relaxed opacity-90">
                      {compatibilityInfo.message}
                    </p>
                  </div>
                )}
              </div>

              {/* Script Textarea with 1-Click Adapter Header */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    บทสคริปต์ (Script Prompt สำหรับ Whisper และจัดไทม์ไลน์)
                  </label>
                  <button
                    type="button"
                    onClick={handleAdaptScript}
                    className="text-[11px] px-2.5 py-1 rounded-lg bg-gradient-to-r from-[#25F4EE]/10 to-[#00D2C4]/10 hover:from-[#25F4EE]/20 hover:to-[#00D2C4]/20 text-[#25F4EE] border border-[#25F4EE]/30 font-medium transition-all flex items-center gap-1 cursor-pointer"
                    title="ปรับประโยคและจังหวะของบทพูดให้ตรงกับสูตร Beat-by-Beat ของสไตล์นี้"
                  >
                    <Wand2 className="w-3 h-3" />
                    แปลงบทให้ตรงจังหวะสไตล์
                  </button>
                </div>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  placeholder="แบบฟอร์มอ้างอิงเดิม ใช้บททางการและ flow ผลิตด้านบนสำหรับงานใหม่"
                  rows={5}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-sm focus:border-[#25F4EE] focus:ring-1 focus:ring-[#25F4EE]/40 focus:outline-none resize-none leading-relaxed font-mono text-xs"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={isCreating || isDuplicateId}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#25F4EE] to-[#00D2C4] hover:brightness-110 disabled:opacity-50 text-slate-950 font-bold text-sm transition-all shadow-md shadow-[#25F4EE]/20 cursor-pointer"
                >
                  {isCreating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      กำลังประมวลผล Whisper...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      เริ่มงานใหม่ผ่าน flow ด้านบน
                    </>
                  )}
                </button>
              </div>
              </fieldset>
            </form>
          </div>
        </div>
      )}

      {/* ── Style Detail & Breakdown Modal ── */}
      {selectedStyleDetail && (() => {
        const modalExtras = STYLE_EXTRAS[selectedStyleDetail.id] || {
          tagColor: 'bg-white/[0.05] text-slate-300 border-white/[0.1]',
          audioDetail: selectedStyleDetail.has_voiceover ? 'มีเสียงพากย์ Fenrir (1.0)' : 'ดนตรีล้วน',
          rhythm: []
        };

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in">
            <div className="relative w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl bg-[#0D111A] border border-white/[0.12] shadow-2xl p-6 flex flex-col md:flex-row gap-6">
              {/* Close Button */}
              <button
                type="button"
                onClick={() => setSelectedStyleDetail(null)}
                className="absolute top-4 right-4 p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors border border-white/[0.08] cursor-pointer"
                title="ปิดหน้าต่าง"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Left Column: 9:16 Mockup Frame */}
              <div className="w-full md:w-64 shrink-0 flex flex-col items-center gap-3">
                <StylePosterMockup styleId={selectedStyleDetail.id} />
                <span className="text-xs text-slate-400 font-mono">
                  ภาพจำลองหน้าปก & HUD 9:16
                </span>
              </div>

              {/* Right Column: Editorial Intelligence */}
              <div className="flex-1 flex flex-col justify-between space-y-4">
                <div className="space-y-4">
                  {/* Title & Badge */}
                  <div className="flex items-start justify-between gap-3 pr-8">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        {getStyleIcon(selectedStyleDetail.id)}
                        <h2 className="text-xl font-bold text-white tracking-tight">
                          {selectedStyleDetail.name}
                        </h2>
                      </div>
                      <p className="text-sm text-slate-400">
                        {selectedStyleDetail.tagline}
                      </p>
                    </div>
                    <span className={`text-xs px-2.5 py-1 rounded-full border font-medium shrink-0 ${modalExtras.tagColor}`}>
                      {selectedStyleDetail.badge}
                    </span>
                  </div>

                  {/* Beat-by-Beat Timeline Breakdown */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-[#25F4EE]" />
                      สูตรจังหวะการตัดไทม์ไลน์ (Rhythm Blueprint):
                    </h4>
                    <div className="space-y-1.5 bg-[#080B11]/80 p-3 rounded-xl border border-white/[0.06]">
                      {modalExtras.rhythm.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-2.5 text-xs">
                          <span className={`px-2 py-0.5 rounded font-mono font-medium text-[11px] shrink-0 border ${step.color}`}>
                            {step.time}
                          </span>
                          <div>
                            <span className="font-semibold text-white">{step.label}: </span>
                            <span className="text-slate-300">{step.desc}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Formula Description */}
                  <div className="space-y-1.5">
                    <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      แนวทางการเล่าเรื่อง (Narrative Formula):
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed bg-[#080B11]/50 p-3 rounded-xl border border-white/[0.06]">
                      {selectedStyleDetail.formula}
                    </p>
                  </div>

                  {/* Technical DNA & Guidelines */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-[#080B11]/50 p-3 rounded-xl border border-white/[0.06]">
                    <div>
                      <span className="text-slate-500 block mb-0.5">ความยาวที่แนะนำ:</span>
                      <span className="font-semibold text-white font-mono">
                        ~{selectedStyleDetail.recommended_duration_sec} วินาที
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block mb-0.5">ระบบเสียง & พากย์:</span>
                      <span className="font-semibold text-[#25F4EE]">
                        {modalExtras.audioDetail}
                      </span>
                    </div>
                    <div className="sm:col-span-2">
                      <span className="text-slate-500 block mb-0.5">คลิปต้นแบบอ้างอิง:</span>
                      <span className="text-slate-200 font-mono text-[11px]">
                        {selectedStyleDetail.reference}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Modal Footer Actions */}
                <div className="pt-4 border-t border-white/[0.08] flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedStyle(selectedStyleDetail.id);
                      setSelectedStyleDetail(null);
                      setActiveTab('create');
                    }}
                    className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-[#25F4EE] to-[#00D2C4] hover:brightness-110 text-slate-950 font-bold text-sm transition-all shadow-md shadow-[#25F4EE]/20 text-center cursor-pointer"
                  >
                    ดูแบบฟอร์มอ้างอิงของสไตล์นี้
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedStyleDetail(null)}
                    className="px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-300 font-medium text-sm border border-white/[0.08] transition-colors cursor-pointer"
                  >
                    ปิดหน้าต่าง
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
        </div>
      </details>
    </div>
  );
}
