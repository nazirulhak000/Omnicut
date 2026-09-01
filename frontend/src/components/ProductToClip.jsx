import React, { useState, useEffect, useRef } from 'react';
import {
  Link2, Sparkles, Clapperboard, Send, Loader2, Check, Copy, Download,
  AlertTriangle, RefreshCw, Camera, Package, QrCode, TrendingUp, Coins
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import AIBridgePanel from './AIBridgePanel';
import {
  aiRun, fetchProductInfo, createProduct, updateProduct, getAngles,
  startRender, startReroll, getRenderStatus,
  createPost, getPosts, setPostMetrics, getPerformance
} from '../api';

const VOICE_PRESETS = [
  { id: 'gemini_puck_male_hype', label: '⚡ Puck — ชายพลังสูง สไตล์ TikTok' },
  { id: 'gemini_charon_male_pro', label: '🎙️ Charon — ชายทุ้มลึก น่าเชื่อถือ' },
  { id: 'gemini_kore_female_bright', label: '✨ Kore — หญิงสดใส ป้ายยาเก่ง' },
  { id: 'gemini_aoede_female_pro', label: '👑 Aoede — หญิงพรีเมียม นุ่มนวล' },
  { id: 'gemini_fenrir_male_strong', label: '🔥 Fenrir — ชายสตรอง คมเข้ม' },
];

// Ordered cheapest first: the user should reach for a fast fix before a slow one.
const REROLL_BUTTONS = [
  { part: 'hook', label: 'ข้อความเปิด', cost: '~30 วิ' },
  { part: 'subtitles', label: 'ซับไตเติล', cost: '~40 วิ' },
  { part: 'video', label: 'จังหวะตัด', cost: '~1 นาที' },
  { part: 'voice', label: 'เสียงพากย์', cost: '2-4 นาที' },
];

const METRIC_LABELS = {
  views: 'ยอดวิว',
  likes: 'ไลค์',
  comments: 'คอมเมนต์',
  shares: 'แชร์',
  cart_clicks: 'คลิกตะกร้า',
  orders: 'ออเดอร์',
  commission_thb: 'คอมมิชชั่น (บาท)',
};

function StepCard({ number, title, subtitle, locked, children }) {
  return (
    <div className={`glass-card p-4 sm:p-5 transition-opacity ${locked ? 'opacity-40 pointer-events-none' : ''}`}>
      <div className="flex items-center gap-2.5 mb-4">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-r from-[#FE2C55] to-[#FF0050] flex items-center justify-center text-white text-xs font-black flex-shrink-0">
          {number}
        </div>
        <div className="min-w-0">
          <h3 className="text-sm sm:text-base font-bold text-white truncate">{title}</h3>
          {subtitle && <p className="text-[11px] text-slate-400 truncate">{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch { /* clipboard blocked — the text is selectable anyway */ }
      }}
      className="px-2.5 py-1.5 rounded-lg bg-[#232A3B] hover:bg-[#323B52] text-white text-[11px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer flex-shrink-0"
    >
      {copied ? <><Check className="w-3 h-3 text-emerald-400" />คัดลอกแล้ว</> : <><Copy className="w-3 h-3 text-[#25F4EE]" />{label}</>}
    </button>
  );
}

export default function ProductToClip({ status, videos, onRefresh }) {
  // Step 1 — product
  const [url, setUrl] = useState('');
  const [fetching, setFetching] = useState(false);
  const [product, setProduct] = useState({
    name: '', category: '', price_note: '', thumbnail: '',
    specs: [], pain_points: [], selling_points: [], raw_text: '',
  });
  const [productId, setProductId] = useState(null);

  // Step 2 — angles and script
  const [angles, setAngles] = useState([]);
  const [angle, setAngle] = useState(null);
  const [script, setScript] = useState(null);

  // Step 3 — render
  const [selectedVideo, setSelectedVideo] = useState('');
  const [voicePreset, setVoicePreset] = useState('gemini_puck_male_hype');
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [rendering, setRendering] = useState(false);
  const [result, setResult] = useState(null);
  const projectNameRef = useRef(null);

  // Step 4 — publish
  const [caption, setCaption] = useState(null);
  const [posted, setPosted] = useState(false);

  // Results panel
  const [pending, setPending] = useState([]);
  const [performance, setPerformance] = useState([]);

  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [manual, setManual] = useState(null);

  useEffect(() => {
    if (!selectedVideo && videos?.length > 0) setSelectedVideo(videos[0].path);
  }, [videos, selectedVideo]);

  const refreshResults = async () => {
    try {
      const [postsRes, perfRes] = await Promise.all([getPosts(), getPerformance()]);
      setPending(postsRes.pending_metrics || []);
      setPerformance(perfRes.by_angle || []);
    } catch { /* the panel is informational; a failure here must not block the flow */ }
  };

  useEffect(() => { refreshResults(); }, []);

  // Poll a render or re-roll job. Both return the same job shape.
  useEffect(() => {
    if (!jobId || !rendering) return;
    const timer = setInterval(async () => {
      try {
        const s = await getRenderStatus(jobId);
        setJob(s);
        if (s.status === 'completed') {
          setRendering(false);
          setResult(s.result);
          setPosted(false);
          clearInterval(timer);
          if (onRefresh) onRefresh();
          // Move the product along the queue so it is no longer just a candidate.
          if (productId) {
            updateProduct(productId, { status: 'rendered' }).catch(() => {});
          }
        } else if (s.status === 'failed') {
          setRendering(false);
          setError(s.error || 'การตัดต่อล้มเหลว');
          clearInterval(timer);
        }
      } catch (err) {
        console.error('poll failed', err);
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [jobId, rendering, onRefresh, productId]);

  /** Run an AI task, falling back to the copy-paste panel when there is no key. */
  const runAI = async (task, context, onData) => {
    setBusy(task);
    setError(null);
    try {
      const res = await aiRun(task, context);
      if (res.mode === 'manual') {
        setManual({
          task,
          prompt: res.prompt,
          warning: res.warning,
          onParsed: (data) => { setManual(null); onData(data); },
        });
      } else {
        onData(res.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(null);
    }
  };

  // --- Step 1 ---------------------------------------------------------
  const handleFetch = async () => {
    setFetching(true);
    setError(null);
    try {
      const info = await fetchProductInfo(url);
      setProduct((p) => ({
        ...p,
        name: info.title || p.name,
        price_note: info.price_note || p.price_note,
        thumbnail: info.thumbnail || '',
        raw_text: info.raw_text || '',
      }));
      if (info.blocked) setError(info.warning || 'หน้านี้ไม่เปิดข้อมูลให้ดึง — กรอกเองได้เลย');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setFetching(false);
    }
  };

  const handleEnrich = () => runAI(
    'product_enrich',
    { product_title: product.name, raw_text: product.raw_text || product.name },
    async (data) => {
      setProduct((p) => ({
        ...p,
        name: data.product_name || p.name,
        category: data.category || '',
        specs: data.specs || [],
        pain_points: data.pain_points || [],
        selling_points: data.selling_points || [],
        price_note: data.price_note || p.price_note,
      }));
      try {
        const saved = await createProduct({
          name: data.product_name || product.name,
          url,
          category: data.category || '',
          specs: data.specs || [],
          pain_points: data.pain_points || [],
          selling_points: data.selling_points || [],
          price_note: data.price_note || product.price_note,
          thumbnail: product.thumbnail,
        });
        setProductId(saved.product.id);
      } catch { /* the queue is a convenience; losing it must not stop the clip */ }
    }
  );

  // --- Step 2 ---------------------------------------------------------
  const handleAngles = async () => {
    setBusy('angles');
    try {
      const cat = await getAngles({ seller_assets_only: true, product_name: product.name });
      await runAI(
        'angles',
        {
          product_name: product.name,
          specs: product.specs,
          pain_points: product.pain_points,
          angle_catalog: cat.catalog,
        },
        (data) => setAngles(
          (data.angles || []).sort((a, b) => (Number(b.priority) || 0) - (Number(a.priority) || 0))
        )
      );
      // With no AI available at all, the catalog still offers usable angles.
      setAngles((current) => (current.length ? current : cat.fallback));
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(null);
    }
  };

  const handleScript = (chosen) => {
    setAngle(chosen);
    return runAI(
      'script',
      {
        product_name: product.name,
        angle_title: chosen.title,
        hook: chosen.hook,
        specs: product.specs,
        price_deal: product.price_note || 'ราคาพิเศษวันนี้',
      },
      (data) => setScript(data)
    );
  };

  // --- Step 3 ---------------------------------------------------------
  const buildProjectName = () => {
    const clean = (product.name || 'product').replace(/[^\p{L}\p{N}]+/gu, '_').slice(0, 40);
    return `TikTok_${clean}_${angle?.angle_key || 'clip'}`;
  };

  const handleRender = async () => {
    if (!selectedVideo) { setError('เลือกวิดีโอดิบก่อน'); return; }
    setError(null);
    setResult(null);
    setRendering(true);
    setJob({ status: 'queued', progress: 0.03, message: 'กำลังเริ่มต้น...', logs: [] });

    const projectName = buildProjectName();
    projectNameRef.current = projectName;

    try {
      const res = await startRender({
        product_name: product.name,
        project_name: projectName,
        raw_video_path: selectedVideo,
        key_features: (product.selling_points || []).join(' '),
        pain_point: (product.pain_points || []).join(' '),
        price_deal: product.price_note || 'ราคาพิเศษวันนี้',
        hook_title: script?.hook_title || angle?.hook || product.name,
        // Send the AI script as custom_script, otherwise the pipeline falls
        // back to its own template and the chosen angle is lost.
        custom_script: (script?.lines || []).map((l) => l.text).join('\n'),
        // Index-aligned with the lines above -- the spec numbers that burn
        // onto the video via subtitle_engine.py's SpecBar style, not just
        // spoken. Empty string for a line with nothing to show on screen.
        script_overlays: (script?.lines || []).map((l) => l.on_screen || ''),
        voice_mode: 'gemini_tts',
        voice_gender: voicePreset.includes('female') ? 'female' : 'male',
        voice_preset: voicePreset,
        export_mp4: true,
      });
      setJobId(res.job_id);
    } catch (err) {
      setRendering(false);
      setError(err.response?.data?.detail || err.message);
    }
  };

  const handleReroll = async (part) => {
    if (!projectNameRef.current) return;
    setError(null);
    setRendering(true);
    setJob({ status: 'queued', progress: 0.03, message: `กำลังสุ่ม${part}ใหม่...`, logs: [] });
    try {
      const res = await startReroll({
        project_name: projectNameRef.current,
        part,
        ...(part === 'voice' ? { voice_preset: voicePreset } : {}),
        ...(part === 'hook' ? { hook_title: script?.hook_title || angle?.hook } : {}),
      });
      setJobId(res.job_id);
    } catch (err) {
      setRendering(false);
      setError(err.response?.data?.detail || err.message);
    }
  };

  // --- Step 4 ---------------------------------------------------------
  const handleCaption = () => runAI(
    'caption',
    {
      product_name: product.name,
      angle_title: angle?.title || '',
      hook: angle?.hook || '',
      price_deal: product.price_note || 'ราคาพิเศษวันนี้',
    },
    (data) => setCaption(data)
  );

  const handleMarkPosted = async () => {
    try {
      await createPost({
        product_name: product.name,
        clip_file: result?.mp4_video || '',
        product_url: url,
        angle_key: angle?.angle_key || '',
        angle_title: angle?.title || '',
        hook: angle?.hook || '',
        caption: caption?.caption || '',
        hashtags: caption?.hashtags || [],
      });
      setPosted(true);
      refreshResults();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const mobileUrl = status?.mobile_url || `http://${window.location.hostname}:5173`;
  const progressPct = Math.round((job?.progress || 0) * 100);

  return (
    <main className="space-y-5">
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-2xl bg-red-500/10 border border-red-500/25 text-xs text-red-300">
          <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white cursor-pointer">✕</button>
        </div>
      )}

      {manual && (
        <AIBridgePanel
          task={manual.task}
          prompt={manual.prompt}
          warning={manual.warning}
          onParsed={manual.onParsed}
          onCancel={() => setManual(null)}
        />
      )}

      {/* STEP 1 — product */}
      <StepCard number="1" title="สินค้า" subtitle="วางลิงก์ Shopee / TikTok Shop แล้วให้ AI สรุปจุดขาย">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex-1 flex items-center gap-2 px-3 rounded-xl bg-[#121622] border border-white/10 focus-within:border-[#25F4EE]/50">
            <Link2 className="w-4 h-4 text-slate-500 flex-shrink-0" />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://shopee.co.th/..."
              className="w-full py-2.5 bg-transparent outline-none text-xs text-slate-200"
            />
          </div>
          <button
            onClick={handleFetch}
            disabled={fetching || !url.trim()}
            className="py-2.5 px-4 rounded-xl bg-[#232A3B] hover:bg-[#323B52] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-40"
          >
            {fetching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4 text-[#25F4EE]" />}
            ดึงข้อมูล
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
          <input
            value={product.name}
            onChange={(e) => setProduct({ ...product, name: e.target.value })}
            placeholder="ชื่อสินค้า"
            className="py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 focus:border-[#25F4EE]/50 outline-none text-xs text-slate-200"
          />
          <input
            value={product.price_note}
            onChange={(e) => setProduct({ ...product, price_note: e.target.value })}
            placeholder="ราคา / โปรโมชั่น"
            className="py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 focus:border-[#25F4EE]/50 outline-none text-xs text-slate-200"
          />
        </div>

        {product.specs?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {product.specs.map((s, i) => (
              <span key={i} className="px-2 py-1 rounded-lg bg-[#25F4EE]/10 border border-[#25F4EE]/25 text-[11px] text-[#25F4EE] font-mono">
                {s.label}: {s.value}
              </span>
            ))}
          </div>
        )}
        {product.pain_points?.length > 0 && (
          <p className="text-[11px] text-slate-400 mt-2">
            <b className="text-slate-300">ปัญหาที่คนเจอ:</b> {product.pain_points.join(' · ')}
          </p>
        )}

        <button
          onClick={handleEnrich}
          disabled={!product.name.trim() || busy === 'product_enrich'}
          className="w-full mt-3 py-2.5 rounded-xl bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#E02449] text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/30 transition-all active:scale-95 cursor-pointer disabled:opacity-40"
        >
          {busy === 'product_enrich' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Package className="w-4 h-4" />}
          ให้ AI สรุปจุดขาย
        </button>
      </StepCard>

      {/* STEP 2 — angles */}
      <StepCard
        number="2"
        title="มุมเล่า"
        subtitle="สินค้าชิ้นเดียว ยิงได้หลายคลิป — เลือกมุมที่จะทำก่อน"
        locked={!product.name.trim()}
      >
        <button
          onClick={handleAngles}
          disabled={busy === 'angles'}
          className="w-full py-2.5 rounded-xl bg-[#232A3B] hover:bg-[#323B52] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-40"
        >
          {busy === 'angles' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-[#25F4EE]" />}
          คิดมุมให้หน่อย
        </button>

        {angles.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 mt-3">
            {angles.map((a) => {
              const active = angle?.angle_key === a.angle_key;
              return (
                <button
                  key={a.angle_key}
                  onClick={() => handleScript(a)}
                  className={`text-left p-3 rounded-xl border transition-all cursor-pointer ${
                    active
                      ? 'bg-[#FE2C55]/10 border-[#FE2C55]/50'
                      : 'bg-[#161B26] border-white/10 hover:border-[#25F4EE]/40'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-white truncate">{a.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold flex-shrink-0 ${
                      a.needs_own_footage
                        ? 'bg-amber-500/15 text-amber-300'
                        : 'bg-emerald-500/15 text-emerald-300'
                    }`}>
                      {a.needs_own_footage ? 'ต้องมีของ' : 'ใช้รูปร้านได้'}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 line-clamp-2">“{a.hook}”</p>
                  {a.why_it_works && <p className="text-[10px] text-slate-500 mt-1 line-clamp-1">{a.why_it_works}</p>}
                </button>
              );
            })}
          </div>
        )}

        {busy === 'script' && (
          <p className="text-[11px] text-slate-400 mt-3 flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> กำลังเขียนสคริปต์...
          </p>
        )}

        {script && (
          <div className="mt-3 p-3 rounded-xl bg-[#0A0D14] border border-white/10 space-y-1.5">
            <div className="text-[11px] font-bold text-[#25F4EE]">📌 {script.hook_title}</div>
            {(script.lines || []).map((l, i) => (
              <div key={i} className="text-[11px] text-slate-300 flex gap-2">
                <span className="text-slate-600 font-mono flex-shrink-0">{i + 1}.</span>
                <span className="flex-1">{l.text}</span>
                {l.on_screen && <span className="text-[10px] text-amber-300 font-mono flex-shrink-0">{l.on_screen}</span>}
              </div>
            ))}
          </div>
        )}
      </StepCard>

      {/* STEP 3 — render */}
      <StepCard number="3" title="ตัดคลิป" subtitle="เลือกวิดีโอดิบและเสียง แล้วปล่อยให้ระบบตัด" locked={!script}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <select
            value={selectedVideo}
            onChange={(e) => setSelectedVideo(e.target.value)}
            className="py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 outline-none text-xs text-slate-200 cursor-pointer"
          >
            <option value="">— เลือกวิดีโอดิบ —</option>
            {(videos || []).map((v) => (
              <option key={v.path} value={v.path}>{v.name}</option>
            ))}
          </select>
          <select
            value={voicePreset}
            onChange={(e) => setVoicePreset(e.target.value)}
            className="py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 outline-none text-xs text-slate-200 cursor-pointer"
          >
            {VOICE_PRESETS.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
          </select>
        </div>

        <button
          onClick={handleRender}
          disabled={rendering || !selectedVideo}
          className="w-full mt-3 py-3 rounded-xl bg-gradient-to-r from-[#FE2C55] via-[#FF0050] to-[#E02449] text-white text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/40 transition-all active:scale-95 cursor-pointer disabled:opacity-40"
        >
          {rendering ? <Loader2 className="w-4 h-4 animate-spin" /> : <Clapperboard className="w-4 h-4" />}
          {rendering ? `กำลังตัด... ${progressPct}%` : 'ตัดคลิปเลย'}
        </button>

        {rendering && (
          <div className="mt-3 space-y-1.5">
            <p className="text-[11px] text-slate-300">{job?.message}</p>
            <div className="h-1.5 rounded-full bg-[#121622] overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}

        {result?.mp4_url && (
          <div className="mt-4 space-y-3">
            <video
              key={result.mp4_url}
              src={result.mp4_url}
              controls
              playsInline
              className="w-full max-w-[260px] mx-auto rounded-xl border border-white/10 bg-black aspect-[9/16] object-contain"
            />
            <div>
              <p className="text-[11px] text-slate-400 mb-1.5">ไม่ชอบตรงไหน สุ่มใหม่เฉพาะส่วนนั้น — เรียงจากถูกไปแพง</p>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
                {REROLL_BUTTONS.map((b) => (
                  <button
                    key={b.part}
                    onClick={() => handleReroll(b.part)}
                    disabled={rendering}
                    className="py-2 px-2 rounded-xl bg-[#161B26] hover:bg-[#232A3B] border border-white/10 hover:border-[#25F4EE]/40 text-white text-[11px] font-bold flex flex-col items-center gap-0.5 transition-all cursor-pointer disabled:opacity-40"
                  >
                    <span className="flex items-center gap-1"><RefreshCw className="w-3 h-3 text-[#25F4EE]" />{b.label}</span>
                    <span className="text-[10px] text-slate-500 font-normal">{b.cost}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </StepCard>

      {/* STEP 4 — publish */}
      <StepCard number="4" title="โพสต์" subtitle="แคปชั่น แฮชแท็ก และส่งไฟล์เข้ามือถือ" locked={!result?.mp4_url}>
        <button
          onClick={handleCaption}
          disabled={busy === 'caption'}
          className="w-full py-2.5 rounded-xl bg-[#232A3B] hover:bg-[#323B52] text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-40"
        >
          {busy === 'caption' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-[#25F4EE]" />}
          เขียนแคปชั่น + แฮชแท็ก
        </button>

        {caption && (
          <div className="mt-3 space-y-2">
            <div className="p-3 rounded-xl bg-[#0A0D14] border border-white/10">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-[11px] font-bold text-slate-300">แคปชั่น</span>
                <CopyButton text={caption.caption} label="คัดลอก" />
              </div>
              <p className="text-xs text-slate-200 whitespace-pre-wrap">{caption.caption}</p>
            </div>
            <div className="p-3 rounded-xl bg-[#0A0D14] border border-white/10">
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-[11px] font-bold text-slate-300">แฮชแท็ก</span>
                <CopyButton text={(caption.hashtags || []).join(' ')} label="คัดลอก" />
              </div>
              <p className="text-xs text-[#25F4EE] break-words">{(caption.hashtags || []).join(' ')}</p>
            </div>
            {caption.cover_text && (
              <p className="text-[11px] text-slate-400">
                <b className="text-slate-300">ข้อความบนปก:</b> {caption.cover_text}
              </p>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-col sm:flex-row items-center gap-4 p-3 rounded-xl bg-[#0A0D14] border border-white/10">
          <div className="p-2.5 bg-white rounded-xl flex-shrink-0">
            <QRCodeSVG value={mobileUrl} size={92} level="M" />
          </div>
          <div className="flex-1 text-center sm:text-left space-y-1.5">
            <p className="text-xs font-bold text-white flex items-center justify-center sm:justify-start gap-1.5">
              <QrCode className="w-3.5 h-3.5 text-emerald-400" /> ส่งไฟล์เข้ามือถือ
            </p>
            <p className="text-[11px] text-slate-400">
              สแกนด้วยมือถือที่ต่อ Wi-Fi เดียวกัน แล้วโหลดคลิปจากแท็บคลังวิดีโอ
            </p>
            {result?.mp4_url && (
              <a
                href={result.mp4_url}
                download
                className="inline-flex items-center gap-1.5 text-[11px] font-bold text-[#25F4EE] hover:underline"
              >
                <Download className="w-3 h-3" /> โหลดลงเครื่องนี้
              </a>
            )}
          </div>
        </div>

        <button
          onClick={handleMarkPosted}
          disabled={posted}
          className="w-full mt-3 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-40"
        >
          {posted ? <><Check className="w-4 h-4" />บันทึกแล้ว — กลับมากรอกผลใน 48 ชม.</> : <><Send className="w-4 h-4" />โพสต์แล้ว บันทึกลงสมุด</>}
        </button>
      </StepCard>

      {/* Results loop */}
      {(pending.length > 0 || performance.length > 0) && (
        <div className="glass-panel p-4 sm:p-5 space-y-4 border border-white/10">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#25F4EE]" /> ผลงานที่ผ่านมา
          </h3>

          {pending.length > 0 && (
            <div className="space-y-2">
              <p className="text-[11px] text-amber-300">
                มี {pending.length} คลิปที่โพสต์เกิน 48 ชม. แล้วยังไม่ได้กรอกผล — ไม่กรอกก็ไม่รู้ว่ามุมไหนขายได้
              </p>
              {pending.map((p) => <MetricsForm key={p.id} post={p} onSaved={refreshResults} />)}
            </div>
          )}

          {performance.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-slate-400 border-b border-white/10">
                    <th className="text-left py-1.5 px-2">มุมเล่า</th>
                    <th className="text-right py-1.5 px-2">คลิป</th>
                    <th className="text-right py-1.5 px-2">วิวเฉลี่ย</th>
                    <th className="text-right py-1.5 px-2">คลิกตะกร้า</th>
                    <th className="text-right py-1.5 px-2">คอมมิชชั่น</th>
                  </tr>
                </thead>
                <tbody>
                  {performance.map((row) => (
                    <tr key={row.angle_key} className="border-b border-white/5">
                      <td className="py-1.5 px-2 text-white font-bold">{row.angle_title || row.angle_key}</td>
                      <td className="py-1.5 px-2 text-right text-slate-300">{row.clips}</td>
                      <td className="py-1.5 px-2 text-right text-slate-300">{row.avg_views?.toLocaleString()}</td>
                      <td className="py-1.5 px-2 text-right text-slate-300">{row.cart_click_rate}%</td>
                      <td className="py-1.5 px-2 text-right text-emerald-400 font-bold">
                        <span className="inline-flex items-center gap-1"><Coins className="w-3 h-3" />{row.commission_thb}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </main>
  );
}

function MetricsForm({ post, onSaved }) {
  const [values, setValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const save = async () => {
    setSaving(true);
    setErr(null);
    try {
      await setPostMetrics(post.id, values);
      onSaved();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-3 rounded-xl bg-[#0A0D14] border border-white/10 space-y-2">
      <div className="flex items-center gap-2 text-[11px]">
        <Camera className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
        <span className="text-white font-bold truncate">{post.product_name}</span>
        <span className="text-slate-500 truncate">· {post.angle_title || post.angle_key}</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
        {Object.entries(METRIC_LABELS).map(([field, label]) => (
          <input
            key={field}
            type="number"
            placeholder={label}
            value={values[field] ?? ''}
            onChange={(e) => setValues({ ...values, [field]: e.target.value })}
            className="py-1.5 px-2 rounded-lg bg-[#121622] border border-white/10 focus:border-[#25F4EE]/50 outline-none text-[11px] text-slate-200"
          />
        ))}
      </div>
      {err && <p className="text-[11px] text-red-300">{err}</p>}
      <button
        onClick={save}
        disabled={saving}
        className="w-full py-1.5 rounded-lg bg-[#232A3B] hover:bg-[#323B52] text-white text-[11px] font-bold cursor-pointer disabled:opacity-40"
      >
        {saving ? 'กำลังบันทึก...' : 'บันทึกผล'}
      </button>
    </div>
  );
}
