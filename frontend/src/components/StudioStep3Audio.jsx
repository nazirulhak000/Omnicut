import React, { useState } from 'react';
import { Mic, Zap, User, Video, Volume2, Play, CheckCircle2, Upload, Sparkles } from 'lucide-react';
import { previewVoice, uploadFile } from '../api';

export default function StudioStep3Audio({
  voiceMode,
  setVoiceMode,
  voiceGender,
  setVoiceGender,
  voiceSpeed,
  setVoiceSpeed,
  voicePreset,
  setVoicePreset,
  adTone = 'commercial_premium',
  setAdTone,
  humanVoiceAudio,
  setHumanVoiceAudio,
  productName,
  fontName,
  setFontName,
  bilingualSubtitles,
  setBilingualSubtitles,
  stickerBadge,
  setStickerBadge
}) {
  const [testingVoice, setTestingVoice] = useState(false);
  const [testAudioUrl, setTestAudioUrl] = useState(null);
  const [uploadingVoice, setUploadingVoice] = useState(false);

  const adToneOptions = [
    {
      id: 'commercial_premium',
      label: '📢 โฆษณาพรีเมียม (Premium Commercial)',
      desc: 'เริ่มน่าค้นหา บิวต์ฟีเจอร์ จบชวนซื้อกระแทกใจ (แนะนำสำหรับสินค้าแบรนด์)',
      context: 'The Sound Stage Booth • Polished, persuasive & inviting'
    },
    {
      id: 'commercial_hype',
      label: '🔥 ป้ายยาตัวแม่ TikTok ไวรัล (Viral Hype)',
      desc: 'กระตือรือร้น ตื่นเต้น ไวรัล สปีดกระชับ กระตุ้นยอดขายทันที',
      context: 'Viral TikTok Stage • High-energy, fast-paced & excited'
    },
    {
      id: 'commercial_aesthetic',
      label: '✨ มินิมอล นุ่มนวล ดูแพง (Aesthetic Beauty)',
      desc: 'นุ่มลึก เป็นกันเอง สบายหู เหมาะกับสกินแคร์ เครื่องสำอาง ของแต่งบ้าน',
      context: 'Cozy Modern Studio • Warm, soothing & intimate tone'
    },
    {
      id: 'commercial_expert',
      label: '🎙️ ผู้เชี่ยวชาญ คมชัด น่าเชื่อถือ (Tech & Pro)',
      desc: 'มั่นใจ ชัดเจน เป็นมืออาชีพ เหมาะกับแกดเจ็ต ไอที เครื่องใช้ไฟฟ้า',
      context: 'Tech Broadcast Studio • Authoritative & confident tone'
    }
  ];

  const saleBadges = [
    { id: 'badge_flash_sale_3d.png', label: '⚡ Flash Sale 3D', color: 'border-red-500/50 text-red-300' },
    { id: 'badge_free_shipping_3d.png', label: '🚚 ส่งฟรีทั่วไทย', color: 'border-emerald-500/50 text-emerald-300' },
    { id: 'badge_best_seller_3d.png', label: '⭐ สินค้าขายดี 5 ดาว', color: 'border-yellow-500/50 text-yellow-300' },
    { id: 'badge_yellow_cart_3d.png', label: '🛒 กดสั่งในตะกร้า', color: 'border-amber-400/50 text-amber-300' },
    { id: 'badge_authentic_shield_3d.png', label: '🛡️ การันตีของแท้', color: 'border-teal-500/50 text-teal-300' },
    { id: 'badge_special_gift_3d.png', label: '🎁 โปรโมชั่นพิเศษ', color: 'border-purple-500/50 text-purple-300' },
    { id: 'badge_hot_deal_3d.png', label: '🔥 ดีลเด็ดมาแรง', color: 'border-orange-500/50 text-orange-300' },
    { id: 'badge_cod_secure_3d.png', label: '💰 เก็บเงินปลายทาง', color: 'border-blue-500/50 text-blue-300' },
    { id: '', label: '❌ ไม่ใส่ป้าย', color: 'border-slate-700 text-slate-400' }
  ];

  const voiceModes = [
    {
      id: 'gemini_tts',
      title: '⚡ Google Gemini 3.1 Flash AI Voice (Cloud HD)',
      desc: 'โมเดลเสียงพากย์ 3.1 Flash ล่าสุดจาก Google เสียงสมจริงเป็นธรรมชาติสูงสุด มีจังหวะหายใจและอารมณ์ป้ายยา',
      icon: Sparkles,
      badge: 'แนะนำอันดับ 1 (3.1)'
    },
    {
      id: 'edge_tts',
      title: '⚡ เสียงพากย์ TikTok HD พลังสูง',
      desc: 'ออกเสียงชัด 100% + สปีด 1.2x กระชับ ตรงสไตล์ TikTok Creator',
      icon: Zap,
    },
    {
      id: 'human',
      title: '🎙️ ใช้เสียงคนพูดจริง',
      desc: 'อัปโหลดไฟล์เสียงอัดจากมือถือ (Voice Memo / .mp3 / .wav)',
      icon: User,
    },
    {
      id: 'video',
      title: '📹 ดึงเสียงพูดจากคลิปวิดีโอ',
      desc: 'ใช้เสียงพูดดั้งเดิมที่บันทึกอยู่ในไฟล์วิดีโอสินค้า',
      icon: Video,
    },
    // F5-TTS (local voice-clone) is dropped permanently, not just deferred
    // until a GPU shows up -- the voice strategy is Google AI Studio's Gemini
    // Flash TTS (scripts/gemini_tts_engine.py) from here on. Backend has no
    // code path for F5 at all anymore, so no option for it is offered here --
    // picking it used to silently fall back to Edge-TTS instead.
  ];

  const handleTestVoice = async () => {
    setTestingVoice(true);
    try {
      const speedVal = parseFloat(voiceSpeed.replace('+', '').replace('%', '')) / 100 + 1.0;
      const res = await previewVoice({
        text: `ทุกคน! สายชาร์จแม่เหล็กตัวนี้คือที่สุด ดูดแน่น ชาร์จเร็ว 66 วัตต์ รีบกดในตะกร้าซ้ายล่างได้เลยครับ`,
        voice_gender: voiceMode === 'gemini_tts' ? voicePreset || 'gemini_puck_male_hype' : voiceGender,
        ad_tone: adTone,
        speed: speedVal || 1.15
      });
      if (res.audio_url) {
        setTestAudioUrl(`${res.audio_url}?t=${Date.now()}`);
      }
    } catch (err) {
      alert('ไม่สามารถสร้างตัวอย่างเสียงได้: ' + err.message);
    } finally {
      setTestingVoice(false);
    }
  };

  const handleVoiceUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingVoice(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_dir', 'inbox');

    try {
      const res = await uploadFile(formData);
      if (res.file) {
        setHumanVoiceAudio(res.file.path);
      }
    } catch (err) {
      alert('อัปโหลดเสียงไม่สำเร็จ: ' + err.message);
    } finally {
      setUploadingVoice(false);
    }
  };

  return (
    <div className="glass-card p-5 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs font-black tracking-wider text-white uppercase rounded-full bg-gradient-to-r from-[#FE2C55] to-[#FF0050] shadow-md shadow-[#FE2C55]/30">
            STEP 3
          </span>
          <div className="flex items-center gap-2">
            <Mic className="w-5 h-5 text-[#FE2C55]" />
            <h2 className="text-base sm:text-lg font-bold text-white font-kanit">
              เสียงพากย์, เพลง BGM & สติกเกอร์ 3D
            </h2>
          </div>
        </div>
      </div>

      {/* Voice Mode Selector Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        {voiceModes.map((mode) => {
          const Icon = mode.icon;
          const isSelected = voiceMode === mode.id;
          return (
            <button
              key={mode.id}
              onClick={() => setVoiceMode(mode.id)}
              className={`p-3 rounded-xl border text-left transition-all relative cursor-pointer ${
                isSelected
                  ? 'bg-[#212838] border-[#FE2C55] shadow-lg shadow-[#FE2C55]/15 ring-1 ring-[#FE2C55]'
                  : 'bg-black/30 border-white/5 hover:border-white/15 hover:bg-black/50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <div className={`p-2 rounded-lg ${isSelected ? 'bg-[#FE2C55]/20 text-[#FE2C55]' : 'bg-slate-800 text-slate-400'}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white flex items-center gap-1.5">
                      {mode.title}
                    </div>
                  </div>
                </div>
                {mode.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gradient-to-r from-cyan-500 to-blue-500 text-white">
                    {mode.badge}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed pl-1">
                {mode.desc}
              </p>
            </button>
          );
        })}
      </div>

      {/* Mode Specific Settings: GEMINI 3.1 FLASH TTS */}
      {voiceMode === 'gemini_tts' && (
        <div className="p-4 rounded-xl bg-gradient-to-br from-[#121622] to-[#1A2234] border border-cyan-500/30 space-y-4 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Google Gemini 3.1 Flash TTS Active (API Key เชื่อมต่อแล้ว)</span>
            </span>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 font-bold">
              โมเดล 3.1 ล่าสุด ~1.5 วิ
            </span>
          </div>

          {/* Voice Character & Speed */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                เลือกคาแรกเตอร์เสียง Gemini 3.1 Flash:
              </label>
              <select
                value={voicePreset || 'gemini_puck_male_hype'}
                onChange={(e) => setVoicePreset && setVoicePreset(e.target.value)}
                className="w-full py-2 px-3 rounded-xl bg-[#0F121A] border border-white/10 text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-cyan-400"
              >
                <option value="gemini_puck_male_hype">⚡ Puck (ชายพลังสูง สไตล์ TikTok ไวรัล)</option>
                <option value="gemini_kore_female_bright">✨ Kore (หญิงสดใส น่ารัก ป้ายยาเก่ง)</option>
                <option value="gemini_aoede_female_pro">👑 Aoede (หญิงพรีเมียม นุ่มนวล ดูแพง)</option>
                <option value="gemini_charon_male_pro">🎙️ Charon (ชายทุ้มลึก น่าเชื่อถือ)</option>
                <option value="gemini_fenrir_male_strong">🔥 Fenrir (ชายสตรอง คมเข้ม)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                ความเร็วการพูด (Speed):
              </label>
              <select
                value={voiceSpeed}
                onChange={(e) => setVoiceSpeed(e.target.value)}
                className="w-full py-2 px-3 rounded-xl bg-[#0F121A] border border-white/10 text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-cyan-400"
              >
                <option value="+10%">1.1x (+10%) ชัดเจน นุ่มนวล</option>
                <option value="+15%">1.15x (+15%) มาตรฐานรีวิว (แนะนำ)</option>
                <option value="+20%">1.2x (+20%) สไตล์ TikTok ไวรัล</option>
              </select>
            </div>
          </div>

          {/* Commercial Ad Tone Presets (Scene / Sample Context) */}
          <div className="pt-1">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <span>🎭 โทนเสียงสไตล์โฆษณา (Commercial Acting Tone):</span>
              </label>
              <span className="text-[10px] text-cyan-300 font-mono">
                [Scene Context Directives]
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {adToneOptions.map((tone) => {
                const isSelected = (adTone || 'commercial_premium') === tone.id;
                return (
                  <button
                    key={tone.id}
                    type="button"
                    onClick={() => setAdTone && setAdTone(tone.id)}
                    className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-cyan-950/60 border-cyan-400 ring-1 ring-cyan-400 shadow-md shadow-cyan-500/20'
                        : 'bg-[#0F121A]/80 border-white/10 hover:border-white/20'
                    }`}
                  >
                    <div className="text-xs font-bold text-white flex items-center justify-between">
                      <span>{tone.label}</span>
                      {isSelected && <span className="text-[10px] text-cyan-400">✓ เลือกอยู่</span>}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                      {tone.desc}
                    </p>
                    <div className="mt-1.5 pt-1.5 border-t border-white/5 text-[10px] font-mono text-cyan-300/80">
                      🎬 {tone.context}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Test Audition Button */}
          <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
            <button
              onClick={handleTestVoice}
              disabled={testingVoice}
              className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-md shadow-cyan-500/20"
            >
              <Volume2 className="w-4 h-4 text-white" />
              {testingVoice ? 'กำลังสังเคราะห์เสียงด้วย Gemini 3.1 Flash...' : '🔊 ทดลองฟังเสียงโฆษณา Commercial สดๆ'}
            </button>
            {testAudioUrl && (
              <audio controls src={testAudioUrl} autoPlay className="h-8 flex-1 w-full max-w-[280px]" />
            )}
          </div>
        </div>
      )}

      {voiceMode === 'edge_tts' && (
        <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-3.5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                โทนเสียงพากย์:
              </label>
              <select
                value={voiceGender}
                onChange={(e) => setVoiceGender(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55]"
              >
                <option value="female">✨ เสียงผู้หญิงสดใส (TikTok Pro Female)</option>
                <option value="male">🔥 เสียงผู้ชายมั่นใจ (TikTok Pro Male)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                ความเร็วสปีด TikTok:
              </label>
              <select
                value={voiceSpeed}
                onChange={(e) => setVoiceSpeed(e.target.value)}
                className="w-full py-2.5 px-3 rounded-xl bg-[#121622] border border-white/10 text-slate-100 text-sm focus:outline-none focus:border-[#FE2C55]"
              >
                <option value="+10%">1.1x (+10%) ชัดเจน นุ่มนวล</option>
                <option value="+15%">1.15x (+15%) มาตรฐานรีวิว</option>
                <option value="+20%">1.2x (+20%) สไตล์ TikTok ไวรัล (แนะนำ)</option>
                <option value="+25%">1.25x (+25%) พูดเร็ว กระตุ้นความสนใจ</option>
              </select>
            </div>
          </div>

          {/* Test Voice Audition Button */}
          <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
            <button
              onClick={handleTestVoice}
              disabled={testingVoice}
              className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-[#232A3B] hover:bg-[#323B52] border border-white/10 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <Volume2 className="w-4 h-4 text-[#25F4EE]" />
              {testingVoice ? 'กำลังสังเคราะห์ตัวอย่างเสียง...' : '🔊 ทดลองฟังตัวอย่างเสียงพากย์ (2 วิ)'}
            </button>
            {testAudioUrl && (
              <audio controls src={testAudioUrl} autoPlay className="h-8 flex-1 w-full max-w-[280px]" />
            )}
          </div>
        </div>
      )}

      {voiceMode === 'human' && (
        <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-3">
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            อัปโหลดไฟล์เสียงพูดจริง (.mp3, .wav, .m4a):
          </label>
          <div className="flex items-center gap-3">
            <label className="px-4 py-2.5 rounded-xl bg-[#232A3B] hover:bg-[#323B52] border border-white/10 text-white font-semibold text-xs flex items-center gap-2 cursor-pointer transition-colors">
              <Upload className="w-4 h-4 text-[#FE2C55]" />
              {uploadingVoice ? 'กำลังอัปโหลด...' : 'เลือกไฟล์เสียง'}
              <input
                type="file"
                accept="audio/*"
                onChange={handleVoiceUpload}
                disabled={uploadingVoice}
                className="hidden"
              />
            </label>
            {humanVoiceAudio && (
              <span className="text-xs text-[#25F4EE] truncate max-w-[260px]">
                ✅ {humanVoiceAudio.split('\\').pop()?.split('/').pop()}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Aesthetic Subtitle Font Selector */}
      <div className="mt-4 pt-3.5 border-t border-white/10">
        <label className="block text-xs font-bold text-slate-200 mb-2 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            🎨 ฟอนต์ซับไตเติล (Aesthetic Minimal Fonts):
          </span>
          <span className="text-[10px] text-[#25F4EE] font-normal">Google Fonts Premium</span>
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[
            { id: 'Mitr', name: '🌸 01 Mitr (มิตร)', desc: 'โค้งมน คลีน สบายตามินิมอล' },
            { id: 'IBMPlex', name: '💻 02 IBM Plex', desc: 'คมกริบ เรียบหรู สายไอที' },
            { id: 'Prompt', name: '📐 03 Prompt (พร้อมท์)', desc: 'โมเดิร์น เรขาคณิต อ่านง่าย' },
            { id: 'ChakraPetch', name: '⚡ 04 Chakra Petch', desc: 'เหลี่ยมล้ำยุค สไตล์ไซเบอร์' },
            { id: 'Kanit', name: '💥 05 Kanit (คณิต)', desc: 'ตัวหนา พลังสูง ดุดันสะดุดตา' },
            { id: 'capsule_pill', name: '✨ 06 Dark Capsule', desc: 'กล่องแคปซูลมน อ่านง่าย 100%' }
          ].map((f) => {
            const isSel = (fontName || 'Mitr') === f.id;
            return (
              <button
                key={f.id}
                type="button"
                onClick={() => setFontName && setFontName(f.id)}
                className={`p-2.5 rounded-xl border text-left transition-all ${
                  isSel
                    ? 'bg-[#FE2C55]/15 border-[#FE2C55] ring-1 ring-[#FE2C55] shadow-md shadow-[#FE2C55]/20'
                    : 'bg-black/30 border-white/5 hover:border-white/15 hover:bg-black/50'
                }`}
              >
                <div className="text-xs font-bold text-white truncate">{f.name}</div>
                <div className="text-[10px] text-slate-400 truncate mt-0.5">{f.desc}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Bilingual Subtitle Stacked Toggle */}
      <div className="mt-4 pt-3.5 border-t border-white/10 flex items-center justify-between p-3 rounded-2xl bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-indigo-500/10 border border-cyan-500/20">
        <div>
          <div className="text-xs font-bold text-white flex items-center gap-1.5">
            <span>🌐 ซับไตเติล 2 ภาษา (Bilingual Stacked)</span>
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-cyan-400/20 text-cyan-300 font-bold">TikTok Trend</span>
          </div>
          <div className="text-[11px] text-slate-400 mt-0.5">
            บรรทัดบนภาษาไทยตัวใหญ่ + บรรทัดล่างแปลภาษาอังกฤษตัวเล็ก เรียบหรูอินเตอร์
          </div>
        </div>
        <button
          type="button"
          onClick={() => setBilingualSubtitles && setBilingualSubtitles(!bilingualSubtitles)}
          className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer ${
            bilingualSubtitles ? 'bg-cyan-500' : 'bg-slate-700'
          }`}
        >
          <div
            className={`w-5 h-5 rounded-full bg-white transition-transform absolute top-0.5 ${
              bilingualSubtitles ? 'left-6.5' : 'left-0.5'
            }`}
          />
        </button>
      </div>

      {/* Promotional Sale Badges / Stickers Overlay */}
      <div className="mt-4 pt-3.5 border-t border-white/10">
        <div className="flex items-center justify-between mb-2.5">
          <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <span>🏷️ ป้ายโปรโมชั่น & สติกเกอร์กระตุ้นยอดขาย (Sale Badge Overlay):</span>
            <span className="text-[10px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full font-bold">
              เพิ่มยอดคลิก
            </span>
          </label>
          <span className="text-[11px] text-slate-400">แสดงมุมขวาบนของวิดีโอ</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {saleBadges.map((badge) => {
            const isSel = (stickerBadge || '') === badge.id;
            return (
              <button
                key={badge.id}
                type="button"
                onClick={() => setStickerBadge && setStickerBadge(badge.id)}
                className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                  isSel
                    ? 'bg-amber-500/20 border-amber-400 ring-1 ring-amber-400 text-white shadow-md shadow-amber-500/20'
                    : 'bg-black/30 border-white/5 hover:border-white/15 text-slate-300 hover:text-white'
                }`}
              >
                <div className="text-xs font-bold truncate">{badge.label}</div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
