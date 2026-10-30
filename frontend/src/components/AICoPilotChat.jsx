import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Sparkles, Send, Bot, User, CheckCircle2, Film, Clapperboard,
  RefreshCw, Play, ExternalLink, ChevronRight, Layers, MessageSquare,
  Wand2, ArrowRight, Loader2, Volume2, ShieldCheck, ShoppingCart
} from 'lucide-react';
import { Modal } from './ui/Modal';
import { Button } from './ui/Button';
import { Badge } from './ui/Badge';
import {
  createCopilotSession,
  getCopilotSession,
  sendCopilotChatMessage,
  generateCopilotScript,
  buildCopilotDraft,
  renderCopilotSession,
  openHyperFramesStudio
} from '../api';

const QUICK_PROMPTS = [
  'ขอสไตล์คู่รักสายใต้น้องนุ้ยกับพี่บ่าว',
  'เน้นจุดขายเรื่องความคุ้มค่าและทนทาน',
  'ผ่าสเปกและฟีเจอร์เด่นให้เห็นภาพชัด',
  'บทสนทนาสั้นกระชับ จบใน 25 วินาที'
];

export default function AICoPilotChat({
  isOpen,
  onClose,
  product,
  onDraftCreated
}) {
  const [session, setSession] = useState(null);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);
  const [isBuildingDraft, setIsBuildingDraft] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState('couple_paper_chat');
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'script' | 'draft'

  const chatEndRef = useRef(null);

  // Initialize or load session when modal opens
  useEffect(() => {
    if (!isOpen || !product?.id) {
      setSession(null);
      return;
    }

    let isMounted = true;
    setIsLoadingSession(true);

    createCopilotSession(product.id, 'เริ่มวางแผนคลิปวิดีโอ TikTok')
      .then((data) => {
        if (isMounted && data.success) {
          setSession(data.session);
        }
      })
      .catch((err) => {
        console.error('Failed to init copilot session:', err);
      })
      .finally(() => {
        if (isMounted) setIsLoadingSession(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, product?.id]);

  // Scroll to bottom when messages update
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [session?.messages]);

  const handleSendMessage = useCallback(async (msgToSend) => {
    const text = (msgToSend || inputMessage).trim();
    if (!text || !session?.session_id || isSendingMessage) return;

    setInputMessage('');
    setIsSendingMessage(true);

    try {
      const res = await sendCopilotChatMessage(session.session_id, text);
      if (res.success && res.session) {
        setSession(res.session);
      }
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsSendingMessage(false);
    }
  }, [inputMessage, session?.session_id, isSendingMessage]);

  const handleGenerateScript = useCallback(async () => {
    if (!session?.session_id || isGeneratingScript) return;
    setIsGeneratingScript(true);

    try {
      const res = await generateCopilotScript(session.session_id, selectedStyle);
      if (res.success && res.session) {
        setSession(res.session);
        setActiveTab('script');
      }
    } catch (err) {
      console.error('Failed to generate script:', err);
    } finally {
      setIsGeneratingScript(false);
    }
  }, [session?.session_id, selectedStyle, isGeneratingScript]);

  const handleBuildDraft = useCallback(async () => {
    if (!session?.session_id || isBuildingDraft) return;
    setIsBuildingDraft(true);

    try {
      const res = await buildCopilotDraft(session.session_id, null, false);
      if (res.success && res.session) {
        setSession(res.session);
        setActiveTab('draft');
        if (onDraftCreated) {
          onDraftCreated(res.session.draft_info);
        }
      }
    } catch (err) {
      console.error('Failed to build draft:', err);
    } finally {
      setIsBuildingDraft(false);
    }
  }, [session?.session_id, isBuildingDraft, onDraftCreated]);

  const handleOpenStudioPreview = useCallback(async () => {
    try {
      await openHyperFramesStudio(3002);
      if (session?.draft_info?.preview_url) {
        window.open(session.draft_info.preview_url, '_blank');
      }
    } catch (err) {
      console.error('Failed to open HyperFrames Studio:', err);
      if (session?.draft_info?.preview_url) {
        window.open(session.draft_info.preview_url, '_blank');
      }
    }
  }, [session?.draft_info?.preview_url]);

  const handleRenderDraft = useCallback(async () => {
    if (!session?.session_id || isRendering) return;
    setIsRendering(true);

    try {
      const res = await renderCopilotSession(session.session_id);
      if (res.success && res.session) {
        setSession(res.session);
        if (onDraftCreated) {
          onDraftCreated(res.session.draft_info);
        }
      }
    } catch (err) {
      console.error('Failed to render draft:', err);
    } finally {
      setIsRendering(false);
    }
  }, [session?.session_id, isRendering, onDraftCreated]);

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AI Production Co-Pilot"
      subtitle={`วางแผนและร่างคลิปอัตโนมัติสำหรับ: ${product?.name || 'สินค้า'}`}
      maxWidth="max-w-5xl"
    >
      <div className="flex flex-col h-[78vh] max-h-[820px] bg-[#0c1017] text-white rounded-xl overflow-hidden">
        {/* Top Product Bar */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#131924] border-b border-white/[0.08]">
          <div className="flex items-center gap-3 min-w-0">
            {product?.thumbnail || (product?.images && product.images[0]) ? (
              <img
                src={product.thumbnail || product.images[0]}
                alt="product"
                className="w-11 h-11 rounded-lg object-cover border border-white/10 shrink-0"
              />
            ) : (
              <div className="w-11 h-11 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <ShoppingCart className="w-5 h-5 text-emerald-400" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm sm:text-base text-white truncate max-w-[400px]">
                  {product?.name}
                </span>
                {product?.price_note && (
                  <Badge variant="outline" className="text-amber-300 border-amber-400/30 bg-amber-500/10 text-xs">
                    {product.price_note}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-slate-400 truncate">
                สไตล์มาตรฐาน: <span className="text-emerald-400 font-medium">Couple Paper Chat #5 (น้องนุ้ย & พี่บ่าว)</span> · HyperFrames 9:16
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {session?.draft_info?.status === 'draft_ready' ? (
              <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-xs flex items-center gap-1.5 py-1 px-2.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                HyperFrames Draft พร้อมตรวจ
              </Badge>
            ) : session?.script ? (
              <Badge className="bg-sky-500/20 text-sky-300 border-sky-500/40 text-xs flex items-center gap-1.5 py-1 px-2.5">
                <Film className="w-3.5 h-3.5" />
                มีสคริปต์พร้อมร่าง
              </Badge>
            ) : null}
          </div>
        </div>

        {/* View Tabs */}
        <div className="flex border-b border-white/[0.08] bg-[#0f141d] px-4 gap-4 text-xs font-medium">
          <button
            onClick={() => setActiveTab('chat')}
            className={`py-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'chat'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            แชทบรีฟ & วางมุมขาย
          </button>
          <button
            onClick={() => setActiveTab('script')}
            className={`py-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'script'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            บทสคริปต์ ({session?.script ? 'สร้างแล้ว' : 'รอสร้าง'})
          </button>
          <button
            onClick={() => setActiveTab('draft')}
            className={`py-2.5 border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'draft'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clapperboard className="w-3.5 h-3.5" />
            HyperFrames Draft
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {isLoadingSession ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="w-7 h-7 animate-spin text-emerald-400" />
              <span className="text-sm">กำลังเชื่อมต่อ AI Production Co-Pilot...</span>
            </div>
          ) : (
            <>
              {/* Tab 1: Interactive Chat */}
              {activeTab === 'chat' && (
                <div className="flex-1 flex flex-col min-w-0">
                  {/* Messages Scroll Area */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {session?.messages?.map((m, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-3 max-w-[85%] ${
                          m.role === 'user' ? 'ml-auto flex-row-reverse' : ''
                        }`}
                      >
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold ${
                            m.role === 'user'
                              ? 'bg-blue-600 text-white'
                              : 'bg-emerald-600 text-white'
                          }`}
                        >
                          {m.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                        </div>
                        <div
                          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                            m.role === 'user'
                              ? 'bg-blue-600/90 text-white rounded-tr-none'
                              : 'bg-[#1a2232] text-slate-200 rounded-tl-none border border-white/[0.08]'
                          }`}
                        >
                          <div className="whitespace-pre-wrap">{m.content}</div>

                          {/* Suggested angles inside message */}
                          {m.angles && m.angles.length > 0 && (
                            <div className="mt-3 space-y-2 pt-2 border-t border-white/10">
                              <span className="text-xs font-semibold text-emerald-300">มุมมองที่แนะนำ:</span>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                                {m.angles.map((ang) => (
                                  <div
                                    key={ang.id}
                                    onClick={() => handleSendMessage(`เลือกมุม: ${ang.title}`)}
                                    className="p-2.5 rounded-lg bg-black/40 hover:bg-emerald-500/10 border border-white/10 hover:border-emerald-500/40 cursor-pointer transition-all"
                                  >
                                    <div className="font-semibold text-xs text-white truncate">{ang.title}</div>
                                    <div className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{ang.hook}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {isSendingMessage && (
                      <div className="flex gap-3 max-w-[80%] items-center text-slate-400 text-xs">
                        <div className="w-7 h-7 rounded-full bg-emerald-600/30 flex items-center justify-center shrink-0">
                          <Bot className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div className="flex items-center gap-1.5 py-2">
                          <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                          <span>AI กำลังวิเคราะห์และพิมพ์คำตอบ...</span>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  {/* Quick Prompts Bar */}
                  <div className="px-4 py-2 bg-[#101622] border-t border-white/[0.06] flex items-center gap-2 overflow-x-auto no-scrollbar">
                    <span className="text-[11px] text-slate-400 shrink-0">คำสั่งด่วน:</span>
                    {QUICK_PROMPTS.map((qp, i) => (
                      <button
                        key={i}
                        onClick={() => handleSendMessage(qp)}
                        disabled={isSendingMessage}
                        className="px-2.5 py-1 rounded-full bg-white/[0.05] hover:bg-emerald-500/20 text-slate-300 hover:text-emerald-300 border border-white/10 hover:border-emerald-500/30 text-xs whitespace-nowrap transition-colors"
                      >
                        {qp}
                      </button>
                    ))}
                  </div>

                  {/* Input Box */}
                  <div className="p-3 bg-[#131924] border-t border-white/[0.08] flex items-center gap-2">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                      placeholder="บอก AI เช่น: 'ขอคลิปแนวฮาๆ ป้ายยาน้องนุ้ยกับพี่บ่าว', 'เน้นโปรโมชันส่งฟรี'..."
                      className="flex-1 bg-black/40 border border-white/10 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none"
                    />
                    <Button
                      onClick={() => handleSendMessage()}
                      disabled={!inputMessage.trim() || isSendingMessage}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl px-4 py-2.5 shrink-0"
                    >
                      {isSendingMessage ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* Tab 2: Script View */}
              {activeTab === 'script' && (
                <div className="flex-1 flex flex-col p-5 overflow-y-auto">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="font-bold text-white text-base">บทสคริปต์อัตโนมัติ (Couple Paper Chat Standard)</h4>
                      <p className="text-xs text-slate-400">
                        สร้างสคริปต์แบบสองบทสนทนา (น้องนุ้ย Aoede & พี่บ่าว Puck) ไร้จุดไข่ปลา
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <select
                        value={selectedStyle}
                        onChange={(e) => setSelectedStyle(e.target.value)}
                        className="bg-[#1a2232] border border-white/10 rounded-lg text-xs px-2.5 py-1.5 text-slate-200"
                      >
                        <option value="couple_paper_chat">Couple Paper Chat (น้องนุ้ย & พี่บ่าว)</option>
                        <option value="meme_pas">Meme-PAS (ปัญหาชีวิต)</option>
                        <option value="tech_explainer">Tech Explainer (ผ่าสเปก)</option>
                        <option value="vs_battle">VS Battle (มวยคู่เอก)</option>
                      </select>
                      <Button
                        onClick={handleGenerateScript}
                        disabled={isGeneratingScript}
                        className="bg-sky-600 hover:bg-sky-500 text-white text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5"
                      >
                        {isGeneratingScript ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            กำลังร่างบท...
                          </>
                        ) : (
                          <>
                            <Wand2 className="w-3.5 h-3.5" />
                            ร่างบทสคริปต์ใหม่
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {session?.script ? (
                    <div className="space-y-4">
                      {/* Headlines Summary */}
                      <div className="bg-[#141b27] border border-white/10 rounded-xl p-3.5">
                        <span className="text-xs font-semibold text-amber-300 block mb-2">หัวข้อพาดหัวบนกระดาษยับ (Headlines):</span>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                          {session.script.headlines?.map((h, i) => (
                            <div key={i} className="p-2 rounded bg-black/30 border border-white/5 text-xs">
                              <span className="text-slate-400 text-[10px] block">ช่วงที่ {i + 1}:</span>
                              <div className="font-semibold text-rose-300">{h[2]}</div>
                              <div className="text-[11px] text-slate-300">{h[1]}</div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Dialogue Turns */}
                      <div className="space-y-2.5">
                        {session.script.turns?.map((t, idx) => (
                          <div
                            key={idx}
                            className={`p-3 rounded-xl border flex gap-3 ${
                              t.speaker === 'F'
                                ? 'bg-pink-950/20 border-pink-500/20'
                                : 'bg-emerald-950/20 border-emerald-500/20'
                            }`}
                          >
                            <div
                              className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
                                t.speaker === 'F'
                                  ? 'bg-pink-600 text-white'
                                  : 'bg-emerald-600 text-white'
                              }`}
                            >
                              {t.speaker === 'F' ? 'น' : 'บ'}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-xs text-white">
                                  {t.speaker === 'F' ? 'น้องนุ้ย (Aoede)' : 'พี่บ่าว (Puck)'}
                                </span>
                                {t.photo && (
                                  <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30 text-[10px] py-0 px-1.5">
                                    มีการ์ดรูปสินค้า
                                  </Badge>
                                )}
                              </div>
                              <div className="text-sm text-slate-200">
                                {t.phrases?.map((p, pi) => (
                                  <span key={pi} className="mr-2">
                                    {p[0]}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="pt-3 flex justify-end">
                        <Button
                          onClick={handleBuildDraft}
                          disabled={isBuildingDraft}
                          className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-4 py-2 rounded-xl flex items-center gap-2"
                        >
                          {isBuildingDraft ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              กำลังสร้าง HyperFrames Draft...
                            </>
                          ) : (
                            <>
                              <Clapperboard className="w-4 h-4" />
                              สร้าง HyperFrames Draft ทันที
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-slate-400 py-12">
                      <Film className="w-10 h-10 text-slate-600" />
                      <span className="text-sm">ยังไม่มีบทสคริปต์ กดปุ่ม "ร่างบทสคริปต์ใหม่" ด้านบนได้เลยครับ</span>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Draft Status & Studio Preview */}
              {activeTab === 'draft' && (
                <div className="flex-1 flex flex-col p-6 overflow-y-auto items-center justify-center text-center">
                  {session?.draft_info?.status === 'rendered' ? (
                    <div className="max-w-md w-full bg-[#131924] border border-emerald-500/30 rounded-2xl p-6 shadow-2xl">
                      <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto mb-4 text-emerald-400">
                        <CheckCircle2 className="w-8 h-8" />
                      </div>
                      <h3 className="font-bold text-lg text-white mb-1">เรนเดอร์คลิปวิดีโอ 9:16 สำเร็จแล้ว!</h3>
                      <p className="text-xs text-slate-400 mb-4">
                        วิดีโอถูกส่งเข้าโฟลเดอร์ผลงาน และย้ายสถานะใน Content Tracker เป็น Rendered เรียบร้อยแล้ว
                      </p>

                      <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-left text-xs space-y-1.5 mb-5 text-slate-300">
                        <div><strong className="text-white">Clip ID:</strong> {session.draft_info.clip_id}</div>
                        <div className="truncate"><strong className="text-white">ไฟล์ MP4:</strong> {session.draft_info.video_url}</div>
                        <div><strong className="text-white">สถานะ Tracker:</strong> <span className="text-emerald-400 font-semibold">เสร็จสมบูรณ์ (Rendered)</span></div>
                      </div>

                      <div className="flex flex-col gap-2.5">
                        <Button
                          onClick={onClose}
                          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2.5 rounded-xl flex items-center justify-center gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          ไปดูคลิปใน Content Tracker / ทำภาพปก
                        </Button>
                      </div>
                    </div>
                  ) : session?.draft_info?.status === 'draft_ready' ? (
                    <div className="max-w-md w-full bg-[#131924] border border-emerald-500/30 rounded-2xl p-6 shadow-2xl">
                      <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mx-auto mb-4 text-emerald-400">
                        <CheckCircle2 className="w-8 h-8" />
                      </div>
                      <h3 className="font-bold text-lg text-white mb-1">HyperFrames Composition พร้อมแล้ว!</h3>
                      <p className="text-xs text-slate-400 mb-4">
                        โครงสร้างคลิป 9:16 ติดตั้งในสตูดิโอเรียบร้อย ตรวจความถูกต้องใน Preview แล้วกดเรนเดอร์ได้ทันที
                      </p>

                      <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-left text-xs space-y-1.5 mb-5 text-slate-300">
                        <div><strong className="text-white">Clip ID:</strong> {session.draft_info.clip_id}</div>
                        <div><strong className="text-white">รูปแบบ:</strong> {session.draft_info.style} (Couple Paper Chat)</div>
                        <div className="truncate"><strong className="text-white">Path:</strong> {session.draft_info.composition_path}</div>
                      </div>

                      <div className="flex flex-col gap-2.5">
                        <Button
                          onClick={handleOpenStudioPreview}
                          className="w-full bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium py-2.5 rounded-xl flex items-center justify-center gap-2 border border-white/10"
                        >
                          <Play className="w-4 h-4" />
                          เปิดตรวจหน้า Studio Preview
                        </Button>
                        <Button
                          onClick={handleRenderDraft}
                          disabled={isRendering}
                          className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40"
                        >
                          {isRendering ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              กำลังเรนเดอร์วิดีโอ MP4 9:16...
                            </>
                          ) : (
                            <>
                              <Film className="w-4 h-4" />
                              เรนเดอร์เป็นวิดีโอ MP4 (1-Click)
                            </>
                          )}
                        </Button>
                        <Button
                          onClick={onClose}
                          variant="outline"
                          className="w-full border-white/10 text-slate-400 hover:text-white py-2 rounded-xl text-xs"
                        >
                          ปิดหน้าต่างนี้และไปดูใน Content Tracker
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-4 max-w-sm">
                      <Clapperboard className="w-12 h-12 text-slate-600" />
                      <div>
                        <h4 className="font-bold text-white text-sm mb-1">ยังไม่ได้สร้าง HyperFrames Draft</h4>
                        <p className="text-xs text-slate-400">
                          เมื่อคุยบรีฟและพอใจกับบทสคริปต์แล้ว สามารถกดปุ่มสร้าง Draft ได้ทันที
                        </p>
                      </div>
                      <Button
                        onClick={handleBuildDraft}
                        disabled={isBuildingDraft || !session?.script}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-4 py-2.5 rounded-xl flex items-center gap-2"
                      >
                        {isBuildingDraft ? (
                          <>
                            <Loader2 className="w-4 h-4 animate-spin" />
                            กำลังสร้าง Draft...
                          </>
                        ) : (
                          <>
                            <Wand2 className="w-4 h-4" />
                            {session?.script ? 'สร้าง Draft จากสคริปต์นี้' : 'กรุณาสร้างสคริปต์ก่อน'}
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}
