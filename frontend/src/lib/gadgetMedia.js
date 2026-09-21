export const GADGET_MEDIA_SERIES = {
  watch_before_buy: { label: 'ดูคลิปนี้ก่อนซื้อ', tone: 'rose' },
  spec_in_plain_language: { label: 'แปลสเปกเป็นภาษาคน', tone: 'cyan' },
  real_vs_marketing: { label: 'ของจริงกับคำโฆษณา', tone: 'amber' },
};

export const GADGET_MEDIA_STATUSES = {
  planned: 'วางแผนแล้ว',
  scripted: 'มีสคริปต์',
  recorded: 'ถ่ายแล้ว',
  edited: 'ตัดต่อแล้ว',
  published: 'เผยแพร่แล้ว',
};

export const SOURCE_RIGHTS_OPTIONS = [
  { value: 'self_recorded', label: 'ถ่ายเอง' },
  { value: 'licensed_press_kit', label: 'ได้รับสิทธิ์หรือ Press kit' },
  { value: 'commentary_excerpt', label: 'ใช้ช่วงสั้นเพื่อวิจารณ์' },
  { value: 'original_ai_visual', label: 'ภาพประกอบ AI ที่สร้างใหม่' },
];

export function seriesLabel(series) {
  return GADGET_MEDIA_SERIES[series]?.label || series;
}

export function statusLabel(status) {
  return GADGET_MEDIA_STATUSES[status] || status;
}

export function campaignProgress(campaign) {
  const slots = campaign?.slots || [];
  const published = slots.filter((slot) => slot.status === 'published').length;
  const edited = slots.filter((slot) => slot.status === 'edited').length;
  return {
    total: slots.length,
    published,
    edited,
    inProgress: slots.filter((slot) => !['planned', 'published'].includes(slot.status)).length,
    percent: slots.length ? Math.round((published / slots.length) * 100) : 0,
  };
}

export function readinessCounts(readiness) {
  return {
    ready: readiness?.ready_slots || 0,
    blocked: readiness?.blocked_slots || 0,
    total: readiness?.total_slots || 0,
  };
}

export const SCRIPT_TEMPLATES = {
  watch_before_buy: {
    name: 'ดูคลิปนี้ก่อนซื้อ',
    defaultHook: (item) => `${item || 'รุ่นนี้'} คลิปนี้ดูเหมือนคุ้ม แต่วันนี้ผมจะสรุป 1 จุดที่ต้องเช็คก่อนซื้อ`,
    sections: {
      hook: (item) => `${item || 'รุ่นนี้'} คลิปนี้ดูเหมือนคุ้ม แต่วันนี้ผมจะสรุป 1 จุดที่ต้องเช็คก่อนซื้อ`,
      evidence: (brand) => `ฟุตเทจเปิดตัวและข้อมูลทางเทคนิคของ ${brand || 'แบรนด์'} ชูจุดเด่นเรื่องความเร็วและการประมวลผล`,
      explain: () => 'ระบบประมวลผลและการใช้งานจริงต่างจากที่หลายคนคิด อุณหภูมิและการจัดการพลังงานต้องดูจากการใช้งานจริง',
      verdict: () => 'ถ้าเน้นความคุ้มค่าและพกพาง่ายรุ่นนี้ผ่าน แต่ถ้าเน้นใช้งานหนักต่อเนื่องแนะนำให้รอดูผลทดสอบเพิ่มเติม',
      cta: () => 'คุณคิดว่ารุ่นนี้น่าซื้อไหม หรืออยากให้เราลองฟีเจอร์ไหนต่อ พิมพ์คอมเมนต์บอกไว้ได้เลยครับ',
    },
  },
  spec_in_plain_language: {
    name: 'แปลสเปกเป็นภาษาคน',
    defaultHook: (item) => `สเปก ${item || 'ตัวนี้'} แปลเป็นการใช้งานจริงว่าอะไร เสียเงินเพิ่มแล้วคุ้มไหม`,
    sections: {
      hook: (item) => `สเปก ${item || 'ตัวนี้'} แปลเป็นการใช้งานจริงว่าอะไร เสียเงินเพิ่มแล้วคุ้มไหม`,
      evidence: (brand) => `ในหน้ากระดาษ ${brand || 'ผู้ผลิต'} เคลมตัวเลขมาสูงมาก แต่ในการใช้งานชีวิตประจำวัน`,
      explain: () => 'ตัวเลขนี้หมายความว่าคุณเปิดแอปและประมวลผลได้ไวขึ้น แต่ถ้าใช้งานทั่วไปอาจจะไม่รู้สึกถึงความแตกต่างชัดเจน',
      verdict: () => 'ดังนั้นไม่ต้องรีบจ่ายแพงขึ้นเพื่อสเปกนี้ เว้นแต่ว่าคุณทำงานเฉพาะทางที่จำเป็นจริงๆ',
      cta: () => 'มีคำศัพท์สเปกตัวไหนที่อ่านแล้วยังสงสัย คอมเมนต์ไว้ เดี๋ยวผมมาแปลให้ฟังครับ',
    },
  },
  real_vs_marketing: {
    name: 'ของจริงกับคำโฆษณา',
    defaultHook: (item) => `ของจริงกับคำโฆษณา ${item || 'รุ่นนี้'} ทำได้จริงตามที่โปรโมทหรือแค่การตลาด`,
    sections: {
      hook: (item) => `ของจริงกับคำโฆษณา ${item || 'รุ่นนี้'} ทำได้จริงตามที่โปรโมทหรือแค่การตลาด`,
      evidence: (brand) => `ในคลิปโปรโมทชูจุดเด่นเรื่องนี้เป็นไฮไลท์หลัก แต่ผลการทดสอบการใช้งานจริง`,
      explain: () => 'สถานการณ์ใช้งานจริงมีข้อจำกัดเรื่องอุณหภูมิและสภาพแวดล้อมที่ไม่ได้ระบุไว้ในโฆษณา',
      verdict: () => 'ถือว่าใช้งานได้ดีในระดับหนึ่ง แต่ไม่ได้หวือหวาเกินจริงอย่างที่โฆษณาไว้',
      cta: () => 'เห็นโฆษณาตัวไหนแล้วสงสัย ส่งมาให้เราช่วยจับพิรุธในคลิปถัดไปได้เลยครับ',
    },
  },
};

export function generateScriptTemplate(series, { topic = '', brand = '' } = {}) {
  const item = topic || brand || '';
  const template = SCRIPT_TEMPLATES[series] || SCRIPT_TEMPLATES.watch_before_buy;
  const hook = template.sections.hook(item);
  const evidence = template.sections.evidence(brand);
  const explain = template.sections.explain();
  const verdict = template.sections.verdict();
  const cta = template.sections.cta();

  const script = [
    `[Hook 0-2s] ${hook}`,
    `[Evidence 3-8s] ${evidence}`,
    `[Explain 9-28s] ${explain}`,
    `[Verdict 29-36s] ${verdict}`,
    `[CTA 37-40s] ${cta}`,
  ].join('\n\n');

  return {
    hook,
    script,
    sections: { hook, evidence, explain, verdict, cta },
  };
}

export function calculateCampaignAnalytics(campaign) {
  const slots = campaign?.slots || [];
  let totalViews = 0;
  let totalComments = 0;
  let totalFollows = 0;
  const slotsWithViews = [];

  const seriesBreakdown = {
    watch_before_buy: { views: 0, follows: 0, comments: 0, count: 0, slotsWithViews: [] },
    spec_in_plain_language: { views: 0, follows: 0, comments: 0, count: 0, slotsWithViews: [] },
    real_vs_marketing: { views: 0, follows: 0, comments: 0, count: 0, slotsWithViews: [] },
  };

  slots.forEach((slot) => {
    const metrics = slot.metrics || {};
    const views = Number(metrics.views) || 0;
    const comments = Number(metrics.comments) || 0;
    const follows = Number(metrics.follows) || 0;
    const completionRate = Number(metrics.completion_rate) || 0;

    totalViews += views;
    totalComments += comments;
    totalFollows += follows;

    if (views > 0) {
      slotsWithViews.push(completionRate);
    }

    if (seriesBreakdown[slot.series]) {
      const s = seriesBreakdown[slot.series];
      s.views += views;
      s.follows += follows;
      s.comments += comments;
      s.count += 1;
      if (views > 0) s.slotsWithViews.push(completionRate);
    }
  });

  const avgCompletionRate = slotsWithViews.length > 0
    ? Math.round((slotsWithViews.reduce((a, b) => a + b, 0) / slotsWithViews.length) * 10) / 10
    : 0;

  const followsPer1000Views = totalViews > 0
    ? Math.round(((totalFollows / totalViews) * 1000) * 100) / 100
    : 0;

  const series = {};
  Object.keys(seriesBreakdown).forEach((key) => {
    const s = seriesBreakdown[key];
    const sAvgComp = s.slotsWithViews.length > 0
      ? Math.round((s.slotsWithViews.reduce((a, b) => a + b, 0) / s.slotsWithViews.length) * 10) / 10
      : 0;
    const sFPer1k = s.views > 0
      ? Math.round(((s.follows / s.views) * 1000) * 100) / 100
      : 0;
    series[key] = {
      views: s.views,
      follows: s.follows,
      comments: s.comments,
      count: s.count,
      avgCompletionRate: sAvgComp,
      followsPer1000Views: sFPer1k,
    };
  });

  return {
    totalViews,
    totalComments,
    totalFollows,
    avgCompletionRate,
    followsPer1000Views,
    series,
  };
}

