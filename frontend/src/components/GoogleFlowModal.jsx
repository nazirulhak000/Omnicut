import { useState, useEffect } from 'react';
import { Video, Sparkles, RefreshCw, CheckCircle, AlertCircle, Play, Download, ExternalLink, ShieldCheck } from 'lucide-react';
import { Modal, Badge } from './ui';
import {
  getFlowStatus,
  startFlowService,
  getFlowPresets,
  expandFlowPrompt,
  generateFlowVideo,
  getFlowJobs,
  getFlowJob,
  ingestFlowClip,
} from '../api';

export default function GoogleFlowModal({
  isOpen,
  onClose,
  productId,
  productName = '',
  initialPrompt = '',
  onClipIngested = null,
}) {
  const [status, setStatus] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [startingService, setStartingService] = useState(false);

  // Form states
  const [mode, setMode] = useState('text'); // 'text' | 'image'
  const [prompt, setPrompt] = useState(initialPrompt);
  const [thaiNotes, setThaiNotes] = useState('');
  const [technique, setTechnique] = useState('orbit');
  const [lighting, setLighting] = useState('studio_clean');
  const [referencePath, setReferencePath] = useState('');
  const [expandingPrompt, setExpandingPrompt] = useState(false);

  // Presets & Jobs
  const [presets, setPresets] = useState({ camera_techniques: [], lighting_presets: [] });
  const [jobs, setJobs] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [ingestingId, setIngestingId] = useState(null);

  // Fetch status & presets on open
  useEffect(() => {
    if (!isOpen) return;
    refreshStatus();
    loadPresets();
    loadJobs();
  }, [isOpen, productId]);

  const refreshStatus = async () => {
    setLoadingStatus(true);
    try {
      const data = await getFlowStatus(true);
      setStatus(data);
    } catch {
      setStatus({ service_online: false, hint: 'ไม่สามารถเชื่อมต่อ flow-mcp service ได้' });
    } finally {
      setLoadingStatus(false);
    }
  };

  const loadPresets = async () => {
    try {
      const data = await getFlowPresets();
      setPresets(data);
    } catch {
      // Fallback defaults
    }
  };

  const loadJobs = async () => {
    if (!productId) return;
    try {
      const data = await getFlowJobs(productId);
      setJobs(data.jobs || []);
    } catch {
      // Silent error
    }
  };

  const handleStartService = async () => {
    setStartingService(true);
    setErrorMsg(null);
    try {
      await startFlowService();
      await new Promise((r) => setTimeout(r, 2000));
      await refreshStatus();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'เปิดบริการ flow-mcp ไม่สำเร็จ');
    } finally {
      setStartingService(false);
    }
  };

  const handleExpandPrompt = async () => {
    if (!thaiNotes.trim() && !prompt.trim()) return;
    setExpandingPrompt(true);
    setErrorMsg(null);
    try {
      const res = await expandFlowPrompt({
        thai_description: thaiNotes.trim() || prompt.trim(),
        product_name: productName,
        technique,
        lighting,
      });
      if (res.prompt) {
        setPrompt(res.prompt);
      }
    } catch (err) {
      setErrorMsg('สร้าง Prompt อัตโนมัติไม่สำเร็จ กรุณาลองใหม่');
    } finally {
      setExpandingPrompt(false);
    }
  };

  const handleSubmitGenerate = async () => {
    if (!prompt.trim()) {
      setErrorMsg('กรุณาระบุ Prompt สำหรับสร้างวิดีโอ');
      return;
    }
    setSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    const scene = {
      prompt: prompt.trim(),
      type: 'video',
      aspect_ratio: '9:16',
      duration: 8,
      technique: technique || undefined,
      download_quality: 'original',
    };

    if (mode === 'image' && referencePath.trim()) {
      scene.reference_images = [referencePath.trim()];
    }

    try {
      const res = await generateFlowVideo({
        product_id: productId,
        scenes: [scene],
      });
      setSuccessMsg('ส่งงานเข้าคิว Google Flow สำเร็จ');
      loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'ส่งงานสร้างวิดีโอไม่สำเร็จ');
    } finally {
      setSubmitting(false);
    }
  };

  const handleIngest = async (job, resultItem) => {
    const srcPath = resultItem?.path || resultItem?.file_path;
    if (!srcPath) return;
    setIngestingId(job.id);
    try {
      const res = await ingestFlowClip({
        product_id: productId,
        source_path: srcPath,
        shot_label: 'flow_broll',
      });
      setSuccessMsg(`นำเข้าคลิปสำเร็จ: ${res.metadata.filename}`);
      if (onClipIngested) onClipIngested(res.metadata);
      loadJobs();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'นำเข้าคลิปไม่สำเร็จ');
    } finally {
      setIngestingId(null);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="สร้างวิดีโอด้วย Google Flow (Veo)" size="2xl">
      <div className="space-y-6 text-sm text-zinc-300">
        {/* Status Bar */}
        <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${status?.service_online ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <div>
              <div className="font-semibold text-zinc-100 flex items-center gap-2">
                Flow Engine (Port 8787): {status?.service_online ? 'ออนไลน์พร้อมใช้งาน' : 'ออฟไลน์'}
              </div>
              <div className="text-xs text-zinc-400">
                {status?.service_online
                  ? `เครดิตคงเหลือ: ${status.credits_remaining !== undefined ? status.credits_remaining : 'ตรวจพบ'} เครดิต · โควตาฟรี 50 ต่อวัน`
                  : 'กดปุ่มด้านขวาเพื่อเปิด Service เบื้องหลัง'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!status?.service_online && (
              <button
                type="button"
                onClick={handleStartService}
                disabled={startingService}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium disabled:opacity-50"
              >
                {startingService ? 'กำลังเริ่มระบบ...' : 'เปิดระบบ Flow Service'}
              </button>
            )}
            <button
              type="button"
              onClick={refreshStatus}
              disabled={loadingStatus}
              className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs"
              title="รีเฟรชสถานะ"
            >
              <RefreshCw className={`w-4 h-4 ${loadingStatus ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Alerts */}
        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-800 text-emerald-200 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Generation Form */}
        <div className="space-y-4 bg-zinc-900/60 p-5 rounded-xl border border-zinc-800">
          {/* Mode Switcher */}
          <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
            <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">รูปแบบการสร้าง</span>
            <div className="flex rounded-lg bg-zinc-950 p-1 border border-zinc-800 text-xs">
              <button
                type="button"
                onClick={() => setMode('text')}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  mode === 'text' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Text-to-Video
              </button>
              <button
                type="button"
                onClick={() => setMode('image')}
                className={`px-3 py-1 rounded-md font-medium transition ${
                  mode === 'image' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Image-to-Video (ภาพสินค้า)
              </button>
            </div>
          </div>

          {/* Thai Concept for AI Expansion */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              แนวคิดภาพหรือช็อตที่ต้องการ (ภาษาไทย)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={thaiNotes}
                onChange={(e) => setThaiNotes(e.target.value)}
                placeholder="เช่น สินค้าตั้งตระหง่านบนโต๊ะ ไฟสถานะ LED กระพริบสวยงาม"
                className="flex-1 px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
              />
              <button
                type="button"
                onClick={handleExpandPrompt}
                disabled={expandingPrompt || (!thaiNotes.trim() && !prompt.trim())}
                className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 shrink-0"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {expandingPrompt ? 'กำลังเขียน...' : 'ขยาย Prompt ด้วย AI'}
              </button>
            </div>
          </div>

          {/* Presets Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1">มุมกล้อง (Camera Motion)</label>
              <select
                value={technique}
                onChange={(e) => setTechnique(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="orbit">Orbit 360 (หมุนรอบสินค้า)</option>
                <option value="macro">Macro Texture (โคลสอัพดีเทล)</option>
                <option value="dolly_in">Dolly In (ดันกล้องเข้าหา)</option>
                <option value="reveal">Low Angle Reveal (เสยมุมต่ำ)</option>
                <option value="floating">Floating (ลอยตัวสโลว์โมชัน)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1">โทนแสง (Lighting Style)</label>
              <select
                value={lighting}
                onChange={(e) => setLighting(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="studio_clean">Studio Clean (สตูดิโอขาวพรีเมียม)</option>
                <option value="dramatic_dark">Dramatic Dark (สตูดิโอดำขอบนีออน)</option>
                <option value="warm_lifestyle">Warm Lifestyle (แสงธรรมชาติอบอุ่น)</option>
                <option value="futuristic_tech">Futuristic Tech (ห้องแล็บแสงฟ้า)</option>
              </select>
            </div>
          </div>

          {/* Reference Image input if mode == image */}
          {mode === 'image' && (
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                พาทภาพสินค้าอ้างอิง (Absolute Path ใน 01_Raw)
              </label>
              <input
                type="text"
                value={referencePath}
                onChange={(e) => setReferencePath(e.target.value)}
                placeholder="D:\Winona\Programmer\Omnicut\01_Raw\... หรือชื่อไฟล์"
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
            </div>
          )}

          {/* Final Cinematic Prompt */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1">
              คำสั่งสร้างภาพภาษาอังกฤษ (Cinematic English Prompt)
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Cinematic vertical commercial shot of tech gadget, slow 360 orbital pan, studio lighting, 9:16 vertical..."
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Submit Button */}
          <div className="pt-2 flex justify-end">
            <button
              type="button"
              onClick={handleSubmitGenerate}
              disabled={submitting || !status?.service_online}
              className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 flex items-center gap-2"
            >
              <Video className="w-4 h-4" />
              {submitting ? 'กำลังส่งงานเข้าคิว...' : 'สร้างวิดีโอบน Google Flow'}
            </button>
          </div>
        </div>

        {/* Recent Jobs & Ingestion Table */}
        {jobs.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-semibold text-zinc-400 tracking-wider">
                คิวงานสร้างวิดีโอล่าสุด ({jobs.length})
              </span>
              <button
                type="button"
                onClick={loadJobs}
                className="text-xs text-cyan-400 hover:text-cyan-300"
              >
                รีเฟรชคิว
              </button>
            </div>

            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between gap-3 text-xs"
                >
                  <div className="truncate flex-1">
                    <div className="font-medium text-zinc-200 truncate">
                      {job.scenes?.[0]?.prompt || job.id}
                    </div>
                    <div className="text-zinc-500 text-[11px] mt-0.5">
                      สถานะ: <span className="text-zinc-300 font-semibold">{job.status}</span> · สร้างเมื่อ: {new Date(job.created_at).toLocaleTimeString('th-TH')}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {job.results?.map((res, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleIngest(job, res)}
                        disabled={ingestingId === job.id}
                        className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1"
                        title="นำเข้าคลิปลง 01_Raw"
                      >
                        <Download className="w-3.5 h-3.5 text-emerald-400" />
                        {ingestingId === job.id ? 'กำลังนำเข้า...' : 'นำเข้าคลัง 01_Raw'}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
