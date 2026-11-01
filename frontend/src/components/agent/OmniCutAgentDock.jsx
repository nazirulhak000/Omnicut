import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles, X, Send, ChevronDown, ChevronRight, Terminal,
  RefreshCw, CheckCircle2, ShieldCheck, Zap
} from 'lucide-react';
import ActionApprovalCard from './ActionApprovalCard.jsx';

export default function OmniCutAgentDock({
  isOpen = false,
  onClose,
  projectName = '',
  onActionApplied,
}) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'agent',
      content: 'สวัสดีครับ! ผม Antigravity AI Co-Producer ประจำสตูดิโอของคุณ พร้อมช่วยตรวจจับไทม์ไลน์ เสนอจุดตัด J-Cut ปรับระดับเสียง 4 บัส หรือจัดสไตล์ซับไตเติลให้ตรงกฎ 9:16 ทันทีครับ',
      thoughts: ['ตรวจพบ Antigravity Engine ในเครื่องและโปรเจกต์พร้อมทำงาน'],
      actions: [],
    },
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [expandedThoughts, setExpandedThoughts] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, messages]);

  // Toggle thought visibility
  const toggleThought = (msgId) => {
    setExpandedThoughts((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  // Quick Chips
  const quickChips = [
    'ตั้งกล้องอัจฉริยะ 9:16',
    'เกรดสีระดับโปรครบวงจร',
    'ปรับเสียงมาตรฐาน -14 LUFS',
    'ใส่ทรานซิชันไวรัล',
    'ช่วยปรับเสียงพากย์และดนตรีให้ได้ -14 LUFS',
    'เสนอจุดตัดแยกคลิปและ J-Cut ที่เหมาะสม',
    'จัดสไตล์ซับไตเติลฟอนต์ Mali-Bold สีนีออน',
    'แนะนำ Hook เปิดคลิป 0-1.8 วินาที',
  ];

  const handleSend = async (textToSend = input) => {
    const text = textToSend.trim();
    if (!text || isStreaming) return;

    setInput('');
    const userMsgId = `user_${Date.now()}`;
    const agentMsgId = `agent_${Date.now()}`;

    // Add user message and empty agent message
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, sender: 'user', content: text },
      { id: agentMsgId, sender: 'agent', content: '', thoughts: [], actions: [] },
    ]);

    setIsStreaming(true);

    try {
      const response = await fetch('/api/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          project_name: projectName || null,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.replace('data: ', '').trim();
          if (!jsonStr) continue;

          try {
            const data = JSON.parse(jsonStr);

            if (data.type === 'thought') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === agentMsgId
                    ? { ...m, thoughts: [...(m.thoughts || []), data.content] }
                    : m
                )
              );
            } else if (data.type === 'token') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === agentMsgId
                    ? { ...m, content: (m.content || '') + data.content }
                    : m
                )
              );
            } else if (data.type === 'action_proposal') {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === agentMsgId
                    ? { ...m, actions: [...(m.actions || []), data.proposal] }
                    : m
                )
              );
            }
          } catch (parseErr) {
            // Ignore malformed chunks
          }
        }
      }
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentMsgId
            ? {
                ...m,
                content:
                  (m.content || '') +
                  `\n\n*(ข้อผิดพลาดในการเชื่อมต่อ Antigravity: ${err.message})*`,
              }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleApplyAction = async (action) => {
    const res = await fetch('/api/agent/actions/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to apply action');
    }
    const data = await res.json();
    if (typeof onActionApplied === 'function') {
      onActionApplied(data);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      data-testid="omnicut-agent-dock"
      className="fixed bottom-4 right-4 z-50 flex h-[620px] w-[460px] max-w-[calc(100vw-2rem)] flex-col rounded-2xl border border-emerald-500/30 bg-[#0c1017]/95 shadow-[0_12px_40px_rgba(0,0,0,0.8),0_0_20px_rgba(16,185,129,0.15)] backdrop-blur-xl transition-all animate-in fade-in slide-in-from-bottom-4 duration-200"
    >
      {/* ── Dock Header ── */}
      <div className="flex items-center justify-between border-b border-white/[0.08] bg-white/[0.02] px-4 py-3 rounded-t-2xl">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-[0_0_10px_rgba(16,185,129,0.3)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-black tracking-wide text-white">Antigravity Co-Producer</span>
              <span className="rounded-full bg-emerald-500/20 px-1.5 py-0.2 text-[9px] font-bold text-emerald-400 border border-emerald-500/30">
                LOCAL
              </span>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span>{projectName ? `Project: ${projectName}` : 'OmniCut Studio'}</span>
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          title="ปิดหน้าต่าง AI Agent (Ctrl+K)"
          className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-white/10 hover:text-white cursor-pointer"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* ── Message Stream Area ── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin scrollbar-thumb-white/10">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            {/* Thoughts Drawer (Collapsible) */}
            {msg.sender === 'agent' && msg.thoughts && msg.thoughts.length > 0 && (
              <div className="mb-1.5 max-w-[92%]">
                <button
                  type="button"
                  onClick={() => toggleThought(msg.id)}
                  className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-emerald-300 transition-colors cursor-pointer py-0.5"
                >
                  {expandedThoughts[msg.id] ? (
                    <ChevronDown className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                  <span>กระบวนการคิดของ Antigravity ({msg.thoughts.length})</span>
                </button>
                {expandedThoughts[msg.id] && (
                  <div className="mt-1 rounded-lg border border-white/[0.06] bg-black/40 p-2 text-[11px] font-mono text-slate-300 space-y-1">
                    {msg.thoughts.map((th, i) => (
                      <div key={i} className="flex items-start gap-1.5">
                        <span className="text-emerald-400">›</span>
                        <span>{th}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Bubble */}
            <div
              className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed whitespace-pre-wrap ${
                msg.sender === 'user'
                  ? 'bg-emerald-600 text-white font-medium rounded-tr-none shadow-md'
                  : 'bg-white/[0.04] text-slate-200 border border-white/[0.08] rounded-tl-none'
              }`}
            >
              {msg.content || (isStreaming && msg.sender === 'agent' ? (
                <span className="inline-flex items-center gap-1.5 text-slate-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-ping" />
                  <span>กำลังคิดและเขียนคำตอบ...</span>
                </span>
              ) : null)}

              {/* Action Approval Cards */}
              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 space-y-2">
                  {msg.actions.map((act) => (
                    <ActionApprovalCard
                      key={act.action_id}
                      action={act}
                      onApply={handleApplyAction}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Quick Suggestion Chips ── */}
      <div className="px-3 py-1.5 flex gap-1.5 overflow-x-auto no-scrollbar border-t border-white/[0.04]">
        {quickChips.map((chip, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSend(chip)}
            disabled={isStreaming}
            className="flex-shrink-0 text-[10px] font-medium text-slate-400 bg-white/[0.03] hover:bg-white/[0.08] hover:text-emerald-300 border border-white/[0.06] px-2.5 py-1 rounded-full transition-colors cursor-pointer disabled:opacity-50"
          >
            {chip}
          </button>
        ))}
      </div>

      {/* ── Chat Input Bar ── */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="p-3 border-t border-white/[0.08] bg-black/30 rounded-b-2xl"
      >
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-1.5 focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/50 transition-all">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder="พิมพ์สั่งงาน Antigravity AI (เช่น ช่วยตัดช่วงเงียบ, ปรับเสียง -14 LUFS)..."
            className="flex-1 bg-transparent text-xs text-white placeholder-slate-500 outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            title="ส่งคำสั่ง (Enter)"
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500 text-slate-950 font-bold hover:bg-emerald-400 disabled:opacity-40 transition-all cursor-pointer"
          >
            {isStreaming ? (
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
            ) : (
              <Send className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
