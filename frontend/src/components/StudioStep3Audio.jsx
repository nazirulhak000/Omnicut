import React, { useState, useEffect, useRef } from 'react';
import {
  Mic, Music, Sparkles, Volume2, Upload, CheckCircle2,
  Play, Pause, Loader2, Zap, User, Video, Sliders, Type, Award, Globe
} from 'lucide-react';
import { previewVoice, getAllAssets, uploadFile } from '../api';

export default function StudioStep3Audio({
  productName,
  voiceMode, setVoiceMode,
  voicePreset, setVoicePreset,
  voiceGender, setVoiceGender,
  voiceSpeed, setVoiceSpeed,
  adTone, setAdTone,
  humanVoiceAudio, setHumanVoiceAudio,
  bgmName, setBgmName,
  fontName, setFontName,
  lutFilter, setLutFilter,
  stickerBadge, setStickerBadge,
  bilingualSubtitles, setBilingualSubtitles
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
      setBgmList(data.bgm || []);
      setLutList(data.luts || []);
    }).catch(() => {});
  }, []);

  const adToneOptions = [
    { id: 'commercial_premium', label: 'พรีเมียม ดูแพง', desc: 'น่าเชื่อถือ ชัดเจน' },
    { id: 'commercial_hype', label: 'ไวรัล TikTok', desc: 'ตื่นเต้น กระตุ้นยอด' },
    { id: 'commercial_aesthetic', label: 'มินิมอล นุ่มนวล', desc: 'ฟังสบาย ผ่อนคลาย' },
    { id: 'commercial_expert', label: 'ผู้เชี่ยวชาญ', desc: 'คมชัด น่าติดตาม' },
  ];

  const fontOptions = [
    { id: 'Mitr', name: 'Mitr (มิตร)', fontClass: 'font-mitr', desc: 'มินิมอลเกาหลี คลีน', sample: 'Aa ชาร์จไว' },
    { id: 'Kanit', name: 'Kanit (คณิต)', fontClass: 'font-kanit', desc: 'ตัวหนา ไวรัล TikTok', sample: 'Aa ชาร์จไว' },
    { id: 'IBMPlex', name: 'IBM Plex Thai', fontClass: 'font-ibm', desc: 'เทค ไอที พรีเมียม', sample: 'Aa ชาร์จไว' },
    { id: 'Prompt', name: 'Prompt (พร้อมท์)', fontClass: 'font-prompt', desc: 'โมเดิร์น เรขาคณิต', sample: 'Aa ชาร์จไว' },
    { id: 'ChakraPetch', name: 'Chakra Petch', fontClass: 'font-chakra', desc: 'ไซเบอร์ คมชัด', sample: 'Aa ชาร์จไว' },
    { id: 'capsule_pill', name: 'Capsule Pill', fontClass: 'font-mitr', desc: 'กล่องมน อ่านออก 100%', sample: 'Aa ชาร์จไว' },
  ];

  const saleBadges = [
    { id: 'badge_flash_sale_3d.png', label: 'Flash Sale' },
    { id: 'badge_free_shipping_3d.png', label: 'ส่งฟรี' },
    { id: 'badge_best_seller_3d.png', label: 'ขายดี' },
    { id: 'badge_yellow_cart_3d.png', label: 'กดตะกร้า' },
    { id: 'badge_authentic_shield_3d.png', label: 'ของแท้ 100%' },
    { id: 'badge_special_gift_3d.png', label: 'โปรพิเศษ' },
    { id: '', label: 'ไม่ใส่ป้าย' },
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
        }, 100);
      }
    } catch (err) {
      alert('ไม่สามารถสร้างเสียงทดสอบได้: ' + err.message);
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
          <span className="w-6 h-6 rounded-lg bg-gradient-to-tr from-[#25F4EE] to-blue-500 flex items-center justify-center text-[12px] font-bold text-slate-950 shadow-md shadow-[#25F4EE]/20">
            3
          </span>
          <h3 className="text-sm font-bold text-white font-kanit">
            เสียงพากย์ AI & สไตล์ภาพ
          </h3>
        </div>

        <span className="text-[10px] font-mono font-bold text-[#25F4EE] bg-[#25F4EE]/10 px-2.5 py-0.5 rounded-full border border-[#25F4EE]/30">
          Gemini HD Audio
        </span>
      </div>

      <div className="glass-card p-4 space-y-4">
        {/* Voice Mode Selector Grid */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-2">
            เลือกโหมดเสียงพากย์
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {voiceModes.map((mode) => {
              const Icon = mode.icon;
              const isActive = voiceMode === mode.id;
              return (
                <button
                  key={mode.id}
                  onClick={() => setVoiceMode(mode.id)}
                  className={`relative p-2.5 rounded-xl text-center transition-all cursor-pointer border ${
                    isActive
                      ? 'bg-gradient-to-b from-[#25F4EE]/20 to-blue-500/10 border-[#25F4EE]/50 text-white shadow-md shadow-[#25F4EE]/10'
                      : 'bg-white/[0.03] border-white/[0.06] text-slate-400 hover:text-white hover:border-white/[0.15]'
                  }`}
                >
                  <Icon className={`w-4 h-4 mx-auto mb-1 ${isActive ? 'text-[#25F4EE]' : 'text-slate-400'}`} />
                  <div className="text-xs font-bold">{mode.label}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{mode.desc}</div>
                  {mode.badge && (
                    <span className="absolute -top-1.5 -right-1.5 text-[9px] font-extrabold px-1.5 py-0.2 rounded-full bg-[#FE2C55] text-white shadow-sm">
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
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  คาแรกเตอร์เสียงพากย์
                </label>
                <select
                  value={voicePreset || 'gemini_puck_male_hype'}
                  onChange={(e) => setVoicePreset && setVoicePreset(e.target.value)}
                  className={selectClass}
                >
                  <option value="gemini_puck_male_hype">Puck — ชายพลังสูง TikTok ไวรัล</option>
                  <option value="gemini_kore_female_bright">Kore — หญิงสดใส เป็นธรรมชาติ</option>
                  <option value="gemini_aoede_female_pro">Aoede — หญิงพรีเมียม เรียบหรู</option>
                  <option value="gemini_charon_male_pro">Charon — ชายทุ้มลึก น่าเชื่อถือ</option>
                  <option value="gemini_fenrir_male_strong">Fenrir — ชายสายสตรอง ดุดัน</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  ความเร็วเสียงพูด
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
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                โทนและอารมณ์เสียงขาย
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {adToneOptions.map((tone) => {
                  const isSelected = (adTone || 'commercial_premium') === tone.id;
                  return (
                    <button
                      key={tone.id}
                      onClick={() => setAdTone && setAdTone(tone.id)}
                      className={`p-2 rounded-xl text-left transition-all cursor-pointer border ${
                        isSelected
                          ? 'bg-gradient-to-r from-[#25F4EE]/15 to-transparent border-[#25F4EE]/40 text-white shadow-sm'
                          : 'bg-white/[0.02] border-white/[0.06] text-slate-400 hover:border-white/[0.12] hover:text-white'
                      }`}
                    >
                      <div className="text-[11px] font-bold text-white">
                        {tone.label}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{tone.desc}</div>
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
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.1] text-slate-200 text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer flex-shrink-0 shadow-sm"
              >
                {testingVoice ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 text-[#25F4EE] animate-spin" />
                    <span>กำลังสร้างเสียงตัวอย่าง...</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="w-3.5 h-3.5 text-[#25F4EE]" />
                    <span>ทดลองฟังเสียง AI สด</span>
                  </>
                )}
              </button>

              {testAudioUrl && (
                <div className="flex items-center gap-3 p-2 rounded-xl bg-black/50 border border-[#25F4EE]/30 w-full sm:w-auto flex-1 animate-fadeIn shadow-md">
                  <button
                    onClick={togglePlayAudio}
                    className="w-7 h-7 rounded-lg bg-[#25F4EE] text-slate-950 flex items-center justify-center flex-shrink-0 shadow-sm cursor-pointer hover:scale-105 transition-transform"
                  >
                    {isPlayingAudio ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 ml-0.5" />}
                  </button>

                  <div className="flex-1 flex items-center gap-1">
                    <span className="wave-bar-1 h-3 w-1 bg-[#25F4EE] rounded-full inline-block"></span>
                    <span className="wave-bar-2 h-5 w-1 bg-[#25F4EE] rounded-full inline-block"></span>
                    <span className="wave-bar-3 h-4 w-1 bg-[#FE2C55] rounded-full inline-block"></span>
                    <span className="wave-bar-4 h-6 w-1 bg-[#25F4EE] rounded-full inline-block"></span>
                    <span className="text-[11px] font-mono text-slate-300 ml-2 font-bold">
                      {isPlayingAudio ? 'กำลังเล่นเสียงตัวอย่าง...' : 'พร้อมเปิดฟัง'}
                    </span>
                  </div>

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

        {/* Edge TTS Options */}
        {voiceMode === 'edge_tts' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-xl bg-black/40 border border-white/[0.08]">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                เสียงผู้พากย์
              </label>
              <select
                value={voiceGender}
                onChange={(e) => setVoiceGender(e.target.value)}
                className={selectClass}
              >
                <option value="male">นิวัฒน์ (ชาย) — ชัดถ้อยชัดคำ</option>
                <option value="female">เปรมวดี (หญิง) — ไพเราะ เป็นมิตร</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                ความเร็วเสียง
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
        )}

        {/* Human Audio Uploader */}
        {voiceMode === 'human' && (
          <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-2">
            <label className="block text-xs font-semibold text-slate-300">
              อัปโหลดไฟล์เสียงพากย์ของคุณเอง (.mp3, .wav, .m4a)
            </label>
            <div className="flex items-center gap-3">
              <label className="px-4 py-2 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold flex items-center gap-2 cursor-pointer transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span>{uploadingVoice ? 'กำลังอัปโหลด...' : 'เลือกไฟล์เสียง'}</span>
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleVoiceUpload}
                  disabled={uploadingVoice}
                  className="hidden"
                />
              </label>
              {humanVoiceAudio && (
                <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>โหลดไฟล์เสียงแล้ว</span>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Video Audio Extractor Note */}
        {voiceMode === 'video' && (
          <div className="p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs text-cyan-200">
            ระบบจะดึงเสียงพูดจากคลิปต้นฉบับที่คุณเลือกในขั้นตอนที่ 1 มาถอดคำและใส่ซับไตเติลให้โดยอัตโนมัติ
          </div>
        )}

        {/* Subtitle Typography, Badges, BGM & Style Options */}
        <div className="pt-2 border-t border-white/[0.08] space-y-3.5">
          {/* Visual Font Chips */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
              <Type className="w-3.5 h-3.5 text-[#25F4EE]" />
              <span>แบบฟอนต์ซับไตเติล (Typography Presets - 6 สไตล์ยอดฮิต)</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {fontOptions.map((f) => {
                const isSelected = (fontName || 'IBMPlex') === f.id;
                return (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFontName && setFontName(f.id)}
                    className={`p-3 rounded-2xl text-left transition-all cursor-pointer border ${
                      isSelected
                        ? 'bg-gradient-to-b from-[#25F4EE]/20 to-[#25F4EE]/5 border-[#25F4EE]/60 text-white shadow-md ring-1 ring-[#25F4EE]/40'
                        : 'bg-black/40 border-white/[0.08] text-slate-400 hover:border-white/[0.2] hover:text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-bold text-white ${f.fontClass}`}>{f.name}</span>
                      <span className={`text-[11px] font-bold text-[#25F4EE] opacity-80 ${f.fontClass}`}>{f.sample}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">{f.desc}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* 3D Sale Badge Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
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

            {/* BGM Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <Music className="w-3.5 h-3.5 text-slate-400" />
                <span>เพลง BGM ประกอบคลิป</span>
              </label>
              <select
                value={bgmName || ''}
                onChange={(e) => setBgmName && setBgmName(e.target.value || null)}
                className={selectClass}
              >
                <option value="">เสียงหลักของช่อง (ค่าเริ่มต้น แนะนำ)</option>
                {bgmList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label_th || m.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Bilingual Subtitle Toggle */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-black/40 border border-white/[0.08]">
            <div className="flex items-center gap-2.5">
              <Globe className="w-4 h-4 text-[#25F4EE]" />
              <div>
                <div className="text-xs font-bold text-white">ซับไตเติล 2 ภาษา (Bilingual Subtitles)</div>
                <div className="text-[11px] text-slate-400">บรรทัดบน: ภาษาไทย / บรรทัดล่าง: คำแปลภาษาอังกฤษอัตโนมัติ</div>
              </div>
            </div>

            <div
              onClick={() => setBilingualSubtitles && setBilingualSubtitles(!bilingualSubtitles)}
              className={`w-9 h-[20px] rounded-full transition-colors relative p-0.5 cursor-pointer ${
                bilingualSubtitles !== false ? 'bg-[#25F4EE]' : 'bg-slate-700'
              }`}
            >
              <div className={`w-4 h-4 rounded-full bg-slate-950 transition-transform shadow-sm ${
                bilingualSubtitles !== false ? 'translate-x-4' : 'translate-x-0'
              }`} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
