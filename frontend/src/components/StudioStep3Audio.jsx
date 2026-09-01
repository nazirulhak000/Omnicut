import React, { useState, useRef, useEffect } from 'react';
import { Mic, Zap, User, Video, Volume2, Play, Pause, CheckCircle2, Upload, Sparkles, ChevronDown, ChevronUp, Type, Award, Globe, Loader2, Music, Palette } from 'lucide-react';
import { previewVoice, uploadFile, getAllAssets } from '../api';

export default function StudioStep3Audio({
  voiceMode, setVoiceMode,
  voiceGender, setVoiceGender,
  voiceSpeed, setVoiceSpeed,
  voicePreset, setVoicePreset,
  adTone = 'commercial_premium', setAdTone,
  humanVoiceAudio, setHumanVoiceAudio,
  productName,
  fontName, setFontName,
  bilingualSubtitles, setBilingualSubtitles,
  stickerBadge, setStickerBadge,
  bgmName, setBgmName,
  lutName, setLutName
}) {
  const [testingVoice, setTestingVoice] = useState(false);
  const [testAudioUrl, setTestAudioUrl] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [uploadingVoice, setUploadingVoice] = useState(false);
  const [bgmList, setBgmList] = useState([]);
  const [lutList, setLutList] = useState([]);
  const audioRef = useRef(null);

  useEffect(() => {
    getAllAssets().then(data => {
      setBgmList(data.music || []);
      setLutList(data.luts || []);
    }).catch(() => {});
  }, []);

  const adToneOptions = [
    { id: 'commercial_premium', label: 'พรีเมียม ดูแพง', icon: '📢', desc: 'น่าเชื่อถือ ชัดเจน' },
    { id: 'commercial_hype', label: 'ไวรัล TikTok', icon: '🔥', desc: 'ตื่นเต้น กระตุ้นยอด' },
    { id: 'commercial_aesthetic', label: 'มินิมอล นุ่มนวล', icon: '✨', desc: 'ฟังสบาย ผ่อนคลาย' },
    { id: 'commercial_expert', label: 'ผู้เชี่ยวชาญ', icon: '🎙️', desc: 'คมชัด น่าติดตาม' },
  ];

  const saleBadges = [
    { id: 'badge_flash_sale_3d.png', label: '⚡ Flash Sale' },
    { id: 'badge_free_shipping_3d.png', label: '🚚 ส่งฟรี' },
    { id: 'badge_best_seller_3d.png', label: '⭐ ขายดี' },
    { id: 'badge_yellow_cart_3d.png', label: '🛒 กดตะกร้า' },
    { id: 'badge_authentic_shield_3d.png', label: '🛡️ ของแท้ 100%' },
    { id: 'badge_special_gift_3d.png', label: '🎁 โปรพิเศษ' },
    { id: '', label: '✕ ไม่ใส่ป้าย' },
  ];

  const voiceModes = [
    { id: 'gemini_tts', label: 'Gemini AI', icon: Sparkles, badge: 'แนะนำ', desc: 'เสียงธรรมชาติ HD' },
    { id: 'edge_tts', label: 'TikTok HD', icon: Zap, desc: 'ชัด เป๊ะ 100%' },
    { id: 'human', label: 'เสียงจริง', icon: User, desc: 'อัปโหลดเสียงพากย์' },
    { id: 'video', label: 'จากคลิป', icon: Video, desc: 'ดึงเสียงจากวิดีโอ' },
  ];

  const handleTestVoice = async () => {
    setTestingVoice(true);
    setIsPlayingAudio(false);
    try {
      const speedVal = parseFloat(voiceSpeed.replace('+', '').replace('%', '')) / 100 + 1.0;
      const res = await previewVoice({
        text: `ทุกคน! ${productName || 'สินค้าตัวนี้'} คือที่สุด ดูดแน่น ชาร์จเร็ว รีบกดในตะกร้าซ้ายล่างได้เลยครับ`,
        voice_gender: voiceMode === 'gemini_tts' ? voicePreset || 'gemini_puck_male_hype' : voiceGender,
        ad_tone: adTone,
        speed: speedVal || 1.15
      });
      if (res.audio_url) {
        const audioSrc = `${res.audio_url}?t=${Date.now()}`;
        setTestAudioUrl(audioSrc);
        setTimeout(() => {
          if (audioRef.current) {
            audioRef.current.play().then(() => setIsPlayingAudio(true)).catch(() => {});
          }
        }, 150);
      }
    } catch (err) {
      alert('ไม่สามารถสร้างตัวอย่างเสียงได้: ' + err.message);
    } finally {
      setTestingVoice(false);
    }
  };

  const togglePlayAudio = () => {
    if (!audioRef.current) return;
    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current.play();
      setIsPlayingAudio(true);
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
      if (res.file) setHumanVoiceAudio(res.file.path);
    } catch (err) {
      alert('อัปโหลดเสียงไม่สำเร็จ: ' + err.message);
    } finally {
      setUploadingVoice(false);
    }
  };

  const selectClass = "w-full py-2 px-3 rounded-xl bg-[#080B11] border border-white/[0.1] text-slate-100 text-xs sm:text-sm focus:outline-none focus:border-[#25F4EE]/50 transition-colors shadow-inner";

  return (
    <section className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-cyan-400 to-[#25F4EE] flex items-center justify-center text-[11px] font-extrabold text-slate-950 shadow-md shadow-[#25F4EE]/20">
            3
          </span>
          <h3 className="text-sm font-bold text-white flex items-center gap-2 font-kanit">
            <span>เสียงพากย์ AI & สไตล์ภาพ</span>
          </h3>
        </div>

        <span className="text-[10px] font-bold text-[#25F4EE] bg-[#25F4EE]/10 px-2 py-0.5 rounded-md border border-[#25F4EE]/20 font-mono">
          Gemini HD Engine
        </span>
      </div>

      <div className="glass-card p-4 space-y-4">
        {/* Voice Mode Selector Grid */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-300 mb-2">
            🎙️ เลือกโหมดเสียงพากย์
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {voiceModes.map((mode) => {
              const Icon = mode.icon;
              const isActive = voiceMode === mode.id;
              return (
                <button
                  key={mode.id}
                  onClick={() => setVoiceMode(mode.id)}
                  className={`relative p-2.5 rounded-xl text-center transition-all cursor-pointer ${
                    isActive
                      ? 'bg-gradient-to-b from-[#25F4EE]/20 to-transparent border border-[#25F4EE]/50 text-white shadow-lg shadow-[#25F4EE]/10 scale-[1.02]'
                      : 'bg-white/[0.02] border border-white/[0.06] text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }`}
                >
                  <Icon className={`w-4 h-4 mx-auto mb-1 ${isActive ? 'text-[#25F4EE]' : 'text-slate-500'}`} />
                  <div className="text-xs font-bold">{mode.label}</div>
                  <div className="text-[9px] text-slate-500 mt-0.5">{mode.desc}</div>
                  {mode.badge && (
                    <span className="absolute -top-1.5 -right-1.5 text-[8px] font-black px-1.5 py-0.2 rounded-full bg-[#25F4EE] text-slate-950 shadow-md">
                      {mode.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Gemini TTS Voice Customizer */}
        {voiceMode === 'gemini_tts' && (
          <div className="space-y-3.5 p-3.5 rounded-xl bg-black/40 border border-white/[0.08]">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  🎭 คาแรกเตอร์เสียงพากย์
                </label>
                <select
                  value={voicePreset || 'gemini_puck_male_hype'}
                  onChange={(e) => setVoicePreset && setVoicePreset(e.target.value)}
                  className={selectClass}
                >
                  <option value="gemini_puck_male_hype">⚡ Puck — ชายพลังสูง TikTok ไวรัล</option>
                  <option value="gemini_kore_female_bright">✨ Kore — หญิงสดใส เป็นธรรมชาติ</option>
                  <option value="gemini_aoede_female_pro">👑 Aoede — หญิงพรีเมียม เรียบหรู</option>
                  <option value="gemini_charon_male_pro">🎙️ Charon — ชายทุ้มลึก น่าเชื่อถือ</option>
                  <option value="gemini_fenrir_male_strong">🔥 Fenrir — ชายสายสตรอง ดุดัน</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                  ⏩ ความเร็วเสียงพูด
                </label>
                <select
                  value={voiceSpeed}
                  onChange={(e) => setVoiceSpeed(e.target.value)}
                  className={selectClass}
                >
                  <option value="+10%">1.1x — สบายๆ กำลังดี</option>
                  <option value="+15%">1.15x — มาตรฐาน TikTok (แนะนำ)</option>
                  <option value="+20%">1.2x — ไวรัล กระชับ ดึงดูด</option>
                </select>
              </div>
            </div>

            {/* Ad Tone Options */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1.5">
                🎯 โทนและอารมณ์เสียงขาย
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {adToneOptions.map((tone) => {
                  const isSelected = (adTone || 'commercial_premium') === tone.id;
                  return (
                    <button
                      key={tone.id}
                      onClick={() => setAdTone && setAdTone(tone.id)}
                      className={`p-2 rounded-xl text-left transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-[#25F4EE]/15 border border-[#25F4EE]/40 text-white shadow-sm'
                          : 'bg-white/[0.02] border border-white/[0.05] text-slate-400 hover:border-white/[0.12]'
                      }`}
                    >
                      <div className="text-[11px] font-bold text-slate-200 flex items-center gap-1.5">
                        <span>{tone.icon}</span>
                        <span>{tone.label}</span>
                      </div>
                      <div className="text-[9px] text-slate-500 mt-0.5">{tone.desc}</div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Live Audio Test Wave Player */}
            <div className="pt-2 flex flex-col sm:flex-row items-center gap-3">
              <button
                onClick={handleTestVoice}
                disabled={testingVoice}
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.15] border border-white/[0.1] text-white text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer flex-shrink-0"
              >
                {testingVoice ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 text-[#25F4EE] animate-spin" />
                    <span>กำลังสร้างเสียงตัวอย่าง...</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>🔊 ทดลองฟังเสียง AI สด</span>
                  </>
                )}
              </button>

              {testAudioUrl && (
                <div className="flex items-center gap-3 p-2 rounded-xl bg-black/60 border border-white/10 w-full sm:w-auto flex-1 animate-fadeIn">
                  <button
                    onClick={togglePlayAudio}
                    className="w-7 h-7 rounded-lg bg-[#25F4EE] text-slate-950 flex items-center justify-center flex-shrink-0 shadow-md cursor-pointer"
                  >
                    {isPlayingAudio ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                  </button>

                  <div className="flex items-center gap-1 flex-1 h-4">
                    <span className={`w-1 bg-[#25F4EE] rounded-full ${isPlayingAudio ? 'wave-bar-1' : 'h-1'}`} />
                    <span className={`w-1 bg-[#25F4EE] rounded-full ${isPlayingAudio ? 'wave-bar-2' : 'h-2'}`} />
                    <span className={`w-1 bg-[#25F4EE] rounded-full ${isPlayingAudio ? 'wave-bar-3' : 'h-3'}`} />
                    <span className={`w-1 bg-[#25F4EE] rounded-full ${isPlayingAudio ? 'wave-bar-4' : 'h-1.5'}`} />
                    <span className={`w-1 bg-[#25F4EE] rounded-full ${isPlayingAudio ? 'wave-bar-2' : 'h-2.5'}`} />
                  </div>

                  <span className="text-[10px] text-emerald-400 font-mono font-semibold">
                    {isPlayingAudio ? 'กำลังเล่น...' : 'พร้อมฟัง'}
                  </span>

                  <audio
                    ref={audioRef}
                    src={testAudioUrl}
                    onEnded={() => setIsPlayingAudio(false)}
                    className="hidden"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Subtitle & Badge Styling Controls */}
        <div className="space-y-3 pt-1 border-t border-white/[0.08]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Font Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <Type className="w-3.5 h-3.5 text-[#25F4EE]" />
                <span>ฟอนต์ซับไตเติล (Auto Thai Typography)</span>
              </label>
              <select
                value={fontName || 'IBMPlex'}
                onChange={(e) => setFontName && setFontName(e.target.value)}
                className={selectClass}
              >
                <option value="IBMPlex">IBM Plex Sans Thai (พรีเมียม สบายตา)</option>
                <option value="Kanit">Kanit (ตัวหนา เด่น ชัดเจน)</option>
                <option value="Prompt">Prompt (โมเดิร์น สไตล์แบรนด์ชั้นนำ)</option>
                <option value="NotoSansThai">Noto Sans Thai (มาตรฐาน คมชัด)</option>
              </select>
            </div>

            {/* 3D Sale Badge Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <Award className="w-3.5 h-3.5 text-amber-400" />
                <span>ป้ายสติกเกอร์ 3D กระตุ้นยอดขาย</span>
              </label>
              <select
                value={stickerBadge || 'badge_flash_sale_3d.png'}
                onChange={(e) => setStickerBadge && setStickerBadge(e.target.value)}
                className={selectClass}
              >
                {saleBadges.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* BGM Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <Music className="w-3.5 h-3.5 text-purple-400" />
                <span>เพลง BGM ประกอบคลิป</span>
              </label>
              <select
                value={bgmName || ''}
                onChange={(e) => setBgmName && setBgmName(e.target.value || null)}
                className={selectClass}
              >
                <option value="">🎵 เสียงหลักของช่อง (ค่าเริ่มต้น แนะนำ)</option>
                {bgmList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label_th || m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* LUT Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <Palette className="w-3.5 h-3.5 text-cyan-400" />
                <span>โทนสี LUT (ไม่บังคับ)</span>
              </label>
              <select
                value={lutName || ''}
                onChange={(e) => setLutName && setLutName(e.target.value || null)}
                className={selectClass}
                title="เครื่องนี้ไม่มีการ์ดจอช่วยเรนเดอร์ — ใส่ LUT วัดแล้วเรนเดอร์ช้าลง ~90%"
              >
                <option value="">⚪ ไม่ใช้ (เร็วกว่า)</option>
                {lutList.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name.replace(/\.cube$/i, '')}
                  </option>
                ))}
              </select>
              {lutName && (
                <div className="text-[9px] text-amber-400 mt-1">⚠️ เรนเดอร์จะช้าลง ~90% บนเครื่องนี้ (ไม่มีการ์ดจอช่วย)</div>
              )}
            </div>
          </div>

          {/* Bilingual Subtitle Toggle */}
          <div className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-[#25F4EE]" />
              <div>
                <div className="text-xs font-bold text-white">ซับไตเติล 2 ภาษา (Bilingual Subtitles)</div>
                <div className="text-[10px] text-slate-400">บรรทัดบน: ภาษาไทย / บรรทัดล่าง: คำแปลภาษาอังกฤษอัตโนมัติ</div>
              </div>
            </div>

            <div
              onClick={() => setBilingualSubtitles && setBilingualSubtitles(!bilingualSubtitles)}
              className={`w-8 h-[18px] rounded-full transition-colors relative p-0.5 cursor-pointer ${
                bilingualSubtitles !== false ? 'bg-[#25F4EE]' : 'bg-white/[0.12]'
              }`}
            >
              <div className={`w-3.5 h-3.5 rounded-full bg-slate-950 transition-transform ${
                bilingualSubtitles !== false ? 'translate-x-3.5' : 'translate-x-0'
              }`} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
