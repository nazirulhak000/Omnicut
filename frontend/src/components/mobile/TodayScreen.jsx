import React, { useEffect, useState, useCallback } from 'react';
import {
  Clapperboard,
  FileText,
  CheckCircle2,
  Send,
  Cpu,
  KeyRound,
  Activity,
  RefreshCw,
} from 'lucide-react';

const STATUS_LABELS = {
  queued: 'รอคิวผลิต',
  running: 'กำลังผลิต',
  awaiting_approval: 'รออนุมัติภาพตัวอย่าง',
  paused_quota: 'พักรอโควตา API',
  completed: 'ผลิตเสร็จสิ้น',
  failed: 'เกิดข้อผิดพลาด',
};

function resolveSystemField(value) {
  if (value === null || value === undefined || value === '') return 'ไม่ทราบ';
  if (typeof value === 'boolean') return value ? 'พร้อมใช้งาน' : 'ไม่พร้อมใช้งาน';
  return String(value);
}

export function TodayScreen({
  onNavigateTab,
  jobs: propJobs,
  todoCounts: propTodoCounts,
  health: propHealth,
  fetchImpl = typeof fetch === 'function' ? fetch : null,
}) {
  const [fetchedJobs, setFetchedJobs] = useState(null);
  const [fetchedPreflight, setFetchedPreflight] = useState(null);
  const [fetchedHealth, setFetchedHealth] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadDashboardData = useCallback(async () => {
    if (typeof fetchImpl !== 'function') return;
    setLoading(true);
    try {
      const safeJson = async (url) => {
        try {
          const res = await fetchImpl(url, {
            method: 'GET',
            headers: { Accept: 'application/json' },
          });
          if (!res || !res.ok) return null;
          return await res.json();
        } catch {
          return null;
        }
      };

      const [jobsData, preflightData, healthData] = await Promise.all([
        safeJson('/api/couple/jobs'),
        safeJson('/api/couple/preflight'),
        safeJson('/api/health'),
      ]);

      if (jobsData) {
        const list = Array.isArray(jobsData)
          ? jobsData
          : Array.isArray(jobsData.jobs)
          ? jobsData.jobs
          : null;
        if (list) setFetchedJobs(list);
      }
      if (preflightData && typeof preflightData === 'object') {
        setFetchedPreflight(preflightData);
      }
      if (healthData && typeof healthData === 'object') {
        setFetchedHealth(healthData);
      }
    } finally {
      setLoading(false);
    }
  }, [fetchImpl]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const effectiveJobs =
    Array.isArray(propJobs) && propJobs.length > 0
      ? propJobs
      : Array.isArray(fetchedJobs)
      ? fetchedJobs
      : [];

  const activeJob =
    effectiveJobs.find((j) =>
      ['running', 'queued', 'awaiting_approval', 'paused_quota'].includes(j?.status)
    ) ||
    effectiveJobs[0] ||
    null;

  const completedClips = Number(
    activeJob?.completed_clips ?? activeJob?.completedClips ?? activeJob?.done ?? 0
  );
  const totalClips = Number(
    activeJob?.total_clips ?? activeJob?.totalClips ?? activeJob?.total ?? 20
  );
  const activeStatusKey = activeJob?.status || 'idle';
  const activeStatusLabel =
    STATUS_LABELS[activeStatusKey] || (activeJob ? String(activeJob.status || 'กำลังดำเนินการ') : 'ไม่มีงานค้าง');

  const scriptsPending = Number(propTodoCounts?.scriptsPending ?? 0);
  const reviewPending = Number(propTodoCounts?.reviewPending ?? 0);
  const postDue = Number(propTodoCounts?.postDue ?? 0);

  const mergedHealth = {
    ...(fetchedHealth || {}),
    ...(fetchedPreflight || {}),
    ...(propHealth || {}),
  };

  const colabStatus = resolveSystemField(
    mergedHealth.colab ?? mergedHealth.runtime ?? mergedHealth.server_status
  );
  const gpuStatus = resolveSystemField(
    mergedHealth.gpu ?? mergedHealth.nvenc ?? mergedHealth.gpu_name
  );
  const apiKeysStatus = resolveSystemField(
    mergedHealth.apiKeys ??
      mergedHealth.api_keys ??
      (typeof mergedHealth.keys_count === 'number' ? `${mergedHealth.keys_count} คีย์` : undefined)
  );

  const navigate = (tab) => {
    if (typeof onNavigateTab === 'function') {
      onNavigateTab(tab);
    }
  };

  return (
    <div className="flex flex-col gap-4 pb-6" data-testid="today-screen">
      {/* 1. Active Production Job Summary */}
      <section
        aria-label="สรุปงานผลิตคลิป"
        className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 shadow-sm"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Clapperboard className="h-5 w-5 text-[#25F4EE]" aria-hidden="true" />
            <h2 className="text-base font-bold text-white">งานที่กำลังผลิต</h2>
          </div>
          <span
            data-testid="active-job-status-badge"
            className="rounded-full border border-white/15 bg-white/[0.06] px-2.5 py-1 text-xs font-semibold text-slate-200"
          >
            {activeStatusLabel}
          </span>
        </div>

        <div className="mt-3 flex items-baseline justify-between">
          <div>
            <p className="text-sm text-slate-300">
              {activeJob?.product_name || activeJob?.productName || activeJob?.product_code || 'สายการผลิต Couple 20 คลิป'}
            </p>
            <p className="mt-1 text-2xl font-extrabold text-white" data-testid="active-job-progress">
              {`${completedClips}/${totalClips} คลิป`}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <button
            type="button"
            onClick={() => navigate('create')}
            data-testid="today-go-create-job"
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] px-4 py-2.5 text-sm font-bold text-slate-950 transition hover:opacity-95"
          >
            <Clapperboard className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>ดูงานที่กำลังผลิต</span>
          </button>
        </div>
      </section>

      {/* 2. รายการต้องทำวันนี้ */}
      <section
        aria-label="รายการต้องทำวันนี้"
        className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
      >
        <h2 className="text-base font-bold text-white">รายการต้องทำวันนี้</h2>

        <div className="mt-3 flex flex-col gap-3">
          {/* สคริปต์รออนุมัติ */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200">สคริปต์รออนุมัติ</p>
              <p className="text-xs text-slate-400" data-testid="todo-scripts-count">
                {`${scriptsPending} รายการ`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('create')}
              data-testid="todo-scripts-btn"
              className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/[0.06] px-3.5 py-2 text-xs font-bold text-white hover:bg-white/[0.1]"
            >
              <FileText className="h-4 w-4 shrink-0 text-[#25F4EE]" aria-hidden="true" />
              <span>อนุมัติสคริปต์</span>
            </button>
          </div>

          {/* คลิปรอตรวจ */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200">คลิปรอตรวจ</p>
              <p className="text-xs text-slate-400" data-testid="todo-review-count">
                {`${reviewPending} รายการ`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('review')}
              data-testid="todo-review-btn"
              className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/[0.06] px-3.5 py-2 text-xs font-bold text-white hover:bg-white/[0.1]"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" aria-hidden="true" />
              <span>ตรวจคลิป</span>
            </button>
          </div>

          {/* คลิปถึงเวลาโพสต์ */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200">คลิปถึงเวลาโพสต์</p>
              <p className="text-xs text-slate-400" data-testid="todo-post-count">
                {`${postDue} รายการ`}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate('post')}
              data-testid="todo-post-btn"
              className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/[0.06] px-3.5 py-2 text-xs font-bold text-white hover:bg-white/[0.1]"
            >
              <Send className="h-4 w-4 shrink-0 text-[#FE2C55]" aria-hidden="true" />
              <span>โพสต์คลิป</span>
            </button>
          </div>
        </div>
      </section>

      {/* 3. System Status Card */}
      <section
        aria-label="สถานะระบบ"
        className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-emerald-400" aria-hidden="true" />
            <h2 className="text-base font-bold text-white">สถานะระบบ</h2>
          </div>
          <button
            type="button"
            onClick={loadDashboardData}
            disabled={loading}
            className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-white/[0.08]"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            <span>รีเฟรชสถานะ</span>
          </button>
        </div>

        <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5">
            <dt className="text-xs text-slate-400">Colab</dt>
            <dd className="mt-1 text-xs font-bold text-white" data-testid="status-colab">
              {colabStatus}
            </dd>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5">
            <dt className="flex items-center justify-center gap-1 text-xs text-slate-400">
              <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
              <span>GPU</span>
            </dt>
            <dd className="mt-1 text-xs font-bold text-white" data-testid="status-gpu">
              {gpuStatus}
            </dd>
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-2.5">
            <dt className="flex items-center justify-center gap-1 text-xs text-slate-400">
              <KeyRound className="h-3.5 w-3.5" aria-hidden="true" />
              <span>API Keys</span>
            </dt>
            <dd className="mt-1 text-xs font-bold text-white" data-testid="status-apikeys">
              {apiKeysStatus}
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

export default TodayScreen;
