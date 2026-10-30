import { channelLocalStorage } from '../lib/channelStorage.js';
import { activeChannel } from '../lib/channelRuntime.js';
import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { getActiveTasks, cancelTaskApi, deleteTaskApi, clearCompletedTasksApi, getTiktokMilestones } from '../api';
import { useToast } from '../hooks/useToast';

const TaskContext = createContext(null);

// Last statuses this device saw (channel-scoped via workspaceStorage). Lets a
// reopened PWA / returning tab report what finished while it was away.
const TASK_STATUS_SNAPSHOT_KEY = 'capcut_task_status_snapshot';
const TASK_STATUS_SNAPSHOT_LIMIT = 200;
// Success notifications clear themselves; failures stay until dismissed.
const SUCCESS_TOAST_MS = 6000;
const NOTIFICATION_QUEUE_LIMIT = 5;

function isCutoutSliceTask(t) {
  return t?.type === 'background_isolation' || t?.task_type === 'background_isolation';
}

function readStatusSnapshot(storage) {
  try {
    const raw = storage?.getItem(TASK_STATUS_SNAPSHOT_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed.statuses === 'object' && parsed.statuses ? { ...parsed.statuses } : {};
  } catch {
    return {};
  }
}

function writeStatusSnapshot(storage, tasks) {
  try {
    const statuses = {};
    for (const t of tasks.slice(0, TASK_STATUS_SNAPSHOT_LIMIT)) {
      if (t?.id != null && t.status) statuses[t.id] = t.status;
    }
    storage?.setItem(TASK_STATUS_SNAPSHOT_KEY, JSON.stringify({ statuses, savedAt: Date.now() }));
  } catch { /* storage full/blocked -- the summary is a convenience */ }
}

function isPageHidden() {
  return typeof document !== 'undefined' && document.hidden === true;
}

// Optional subtle audio chime using Web Audio API (no external file dependency)
function playCompletionChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.exponentialRampToValueAtTime(880.0, ctx.currentTime + 0.15); // A5

    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {
    // Audio autostart may be blocked by browser policy until interaction
  }
}

export function TaskProvider({ children, onNavigateTab, onSelectProductForFlow }) {
  const [workspaceStorage] = useState(channelLocalStorage);

  const [tasks, setTasks] = useState(() => {
    try {
      const saved = workspaceStorage.getItem('capcut_task_cache');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false);
  const {
    toast: notificationToast,
    showToast: enqueueNotification,
    hideToast: dismissNotification,
  } = useToast(0, NOTIFICATION_QUEUE_LIMIT);
  const setNotificationToast = useCallback((nextToast) => {
    if (!nextToast) {
      dismissNotification();
      return;
    }
    const type = nextToast.type || 'info';
    const duration = nextToast.duration ?? (type === 'error' || type === 'warning' ? 0 : SUCCESS_TOAST_MS);
    enqueueNotification(
      nextToast.message || nextToast.title || 'มีการแจ้งเตือนใหม่',
      type,
      duration,
      nextToast,
    );
  }, [dismissNotification, enqueueNotification]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [viralMilestones, setViralMilestones] = useState([]);
  const [taskSyncState, setTaskSyncState] = useState({
    status: 'unknown',
    lastSuccessfulAt: null,
    error: null,
  });

  // Check TikTok viral milestones periodically
  const notifiedMilestonesRef = useRef(new Set());
  const viralMilestonesInFlightRef = useRef(null);

  const fetchViralMilestones = useCallback(async () => {
    if (viralMilestonesInFlightRef.current) return viralMilestonesInFlightRef.current;
    const request = (async () => {
      try {
      const res = await getTiktokMilestones(1000);
      if (res && Array.isArray(res.milestones)) {
        setViralMilestones(res.milestones);
        // If a high-tier viral milestone (> 10k) hasn't notified this session
        res.milestones.forEach(m => {
          if (m.views >= 10000 && !notifiedMilestonesRef.current.has(m.post_id)) {
            notifiedMilestonesRef.current.add(m.post_id);
            setNotificationToast({
              type: 'success',
              title: 'คลิปยอดวิวทะลุเป้า',
              message: `คลิป "${m.product_name}" ทำยอดวิวทะลุ ${m.views.toLocaleString()} วิวแล้ว!`,
              milestone: m,
              time: Date.now()
            });
          }
        });
      }
      } catch (e) {
        // Analytics can be unavailable independently of task polling. Keep the
        // last known milestones and retry on the next safe polling window.
      } finally {
        viralMilestonesInFlightRef.current = null;
      }
    })();
    viralMilestonesInFlightRef.current = request;
    return request;
  }, [setNotificationToast]);

  const lastViralMilestoneCheckRef = useRef(0);
  const maybeFetchViralMilestones = useCallback(() => {
    const now = Date.now();
    if (now - lastViralMilestoneCheckRef.current < 30_000) return;
    lastViralMilestoneCheckRef.current = now;
    void fetchViralMilestones();
  }, [fetchViralMilestones]);

  // Keep a map of previous statuses to detect transitions (e.g. processing -> completed).
  // Seeded from the persisted snapshot so work that finished while the app was
  // closed is still reported once.
  const prevStatusesRef = useRef(null);
  if (prevStatusesRef.current === null) prevStatusesRef.current = readStatusSnapshot(workspaceStorage);
  // True on mount and whenever the page was hidden: the next successful poll
  // summarises everything that changed meanwhile instead of a toast storm.
  const awayRef = useRef(true);
  const [isPageVisible, setIsPageVisible] = useState(() => !isPageHidden());
  // Holds the Promise of an in-flight pollTasks() call (or null when idle).
  const inFlightPollRef = useRef(null);
  // Set when pollTasks() is called again while one is already in flight.
  // The in-flight call's data may predate this request's caller (e.g. a
  // cancelTask() confirming refresh requested mid-poll needs a *fresh* fetch,
  // not the stale one already underway) -- so instead of dropping the extra
  // call, we queue exactly one more fetch to run right after the current one
  // finishes, and hand its promise to the caller.
  const queuedPollRef = useRef(null);

  const activeTasks = tasks.filter(t => t.status === 'processing' || t.status === 'queued');
  const activeCount = activeTasks.length;
  const completedTasks = tasks.filter(t => t.status === 'completed');

  // Save cache to localStorage
  useEffect(() => {
    try {
      workspaceStorage.setItem('capcut_task_cache', JSON.stringify(tasks.slice(0, 20)));
    } catch (e) {
      console.error('Failed to cache tasks:', e);
    }
  }, [tasks]);

  const fetchAndApplyTasks = useCallback(async () => {
    try {
      const res = await getActiveTasks();
      if (!res || !Array.isArray(res.tasks)) {
        throw new Error('Invalid task status response');
      }
      const fetchedTasks = res.tasks;

      const notifyTransition = (t) => {
        if (t.status === 'completed') {
          if (!isCutoutSliceTask(t)) {
            playCompletionChime();
            setNotificationToast({
              type: 'success',
              title: 'งานเสร็จสมบูรณ์',
              message: t.step_label || t.title,
              task: t,
              time: Date.now()
            });
          }
        } else if (t.status === 'failed') {
          setNotificationToast({
            type: 'error',
            title: 'งานไม่สำเร็จ',
            message: t.error || t.step_label || t.title,
            task: t,
            time: Date.now()
          });
        }
      };

      // First poll after mount / returning to the page: collect, then summarise.
      const summarizeAway = awayRef.current && !isPageHidden();
      if (summarizeAway) awayRef.current = false;
      const awayTransitions = [];

      // Check for state transitions
      fetchedTasks.forEach(t => {
        const prevStatus = prevStatusesRef.current[t.id];
        if (prevStatus && prevStatus !== t.status && (t.status === 'completed' || t.status === 'failed')) {
          // Auto-refresh child views
          if (t.status === 'completed') setRefreshTrigger(prev => prev + 1);
          if (summarizeAway) awayTransitions.push(t);
          else notifyTransition(t);
        }
        prevStatusesRef.current[t.id] = t.status;
      });

      if (awayTransitions.length === 1) {
        notifyTransition(awayTransitions[0]);
      } else if (awayTransitions.length > 1) {
        const doneCount = awayTransitions.filter(t => t.status === 'completed' && !isCutoutSliceTask(t)).length;
        const failedCount = awayTransitions.filter(t => t.status === 'failed').length;
        if (doneCount + failedCount > 0) {
          if (doneCount > 0) playCompletionChime();
          setNotificationToast({
            type: failedCount > 0 ? 'error' : 'success',
            title: 'สรุปงานเบื้องหลัง',
            message: `ระหว่างไม่อยู่: เสร็จ ${doneCount} · ล้มเหลว ${failedCount}`,
            summary: { done: doneCount, failed: failedCount },
            time: Date.now()
          });
        }
      }
      writeStatusSnapshot(workspaceStorage, fetchedTasks);

      // Initialize prevStatuses for new tasks
      fetchedTasks.forEach(t => {
        if (!prevStatusesRef.current[t.id]) {
          prevStatusesRef.current[t.id] = t.status;
        }
      });

      setTasks(fetchedTasks);
      setTaskSyncState({
        status: 'healthy',
        lastSuccessfulAt: Date.now(),
        error: null,
      });
      maybeFetchViralMilestones();
    } catch (err) {
      setTaskSyncState(prev => ({
        status: 'stale',
        lastSuccessfulAt: prev.lastSuccessfulAt,
        error: err?.response?.data?.detail || err?.message || 'เชื่อมต่อ backend ไม่สำเร็จ',
      }));
      throw err;
    }
  }, [maybeFetchViralMilestones, setNotificationToast, workspaceStorage]);

  // Starts exactly one fresh fetch, tracked via inFlightPollRef.
  const startPoll = useCallback(() => {
    const run = (async () => {
      try {
        await fetchAndApplyTasks();
      } catch (err) {
        // Network failure or backend temporarily unavailable
      } finally {
        inFlightPollRef.current = null;
      }
    })();

    inFlightPollRef.current = run;
    return run;
  }, [fetchAndApplyTasks]);

  const pollTasks = useCallback(() => {
    // If a poll is already running, don't drop this call -- queue exactly
    // one more fetch to run right after it finishes and hand its promise to
    // the caller. This matters for confirming refreshes (cancelTask, etc.):
    // the in-flight poll may have started before their mutating API call
    // resolved, so its data can be stale for their purposes.
    if (inFlightPollRef.current) {
      if (!queuedPollRef.current) {
        queuedPollRef.current = inFlightPollRef.current
          .catch(() => {}) // don't let the current poll's error skip the queued one
          .then(() => {
            queuedPollRef.current = null;
            return startPoll();
          });
      }
      return queuedPollRef.current;
    }

    return startPoll();
  }, [startPoll]);

  // Background/foreground: a hidden page (locked phone, other app, background
  // tab) stops polling; coming back -- visibilitychange, a bfcache restore
  // (pageshow) or the network returning (online) -- polls immediately.
  useEffect(() => {
    if (typeof document === 'undefined') return undefined;
    const onVisibilityChange = () => {
      const visible = !isPageHidden();
      if (!visible) awayRef.current = true;
      setIsPageVisible(visible);
    };
    const onResume = () => {
      if (isPageHidden()) return;
      setIsPageVisible(true);
      pollTasks();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pageshow', onResume);
    window.addEventListener('online', onResume);
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('pageshow', onResume);
      window.removeEventListener('online', onResume);
    };
  }, [pollTasks]);

  // Adaptive Polling: 1.5s when active tasks exist, 6s when idle; paused while hidden.
  useEffect(() => {
    if (!isPageVisible) return undefined;
    pollTasks(); // Initial fetch on mount / F5 / return to the page
    const intervalTime = activeCount > 0 ? 1500 : 6000;
    const timer = setInterval(() => {
      if (!isPageHidden()) pollTasks();
    }, intervalTime);
    return () => clearInterval(timer);
  }, [activeCount, pollTasks, isPageVisible]);

  // Actions
  const cancelTask = useCallback(async (taskId) => {
    try {
      await cancelTaskApi(taskId);
      await pollTasks();
    } catch (e) {
      console.error('Cancel task failed:', e);
    }
  }, [pollTasks]);

  const deleteTask = useCallback(async (taskId) => {
    try {
      await deleteTaskApi(taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (e) {
      console.error('Delete task failed:', e);
    }
  }, []);

  const clearCompleted = useCallback(async () => {
    try {
      await clearCompletedTasksApi();
      setTasks(prev => prev.filter(t => t.status === 'processing' || t.status === 'queued'));
    } catch (e) {
      console.error('Clear completed tasks failed:', e);
    }
  }, []);

  const jumpToTaskResult = useCallback((task, destinationTab = null) => {
    if (!task) return;
    if (task.read_only_projection && task.type?.startsWith('hyperframes_')) {
      const owner = task.channel_id;
      if (owner !== activeChannel() || !task.payload?.project_id) return;
      setIsActivityDrawerOpen(false);
      setNotificationToast(null);
      onNavigateTab?.('tracker');
      return;
    }
    setIsActivityDrawerOpen(false);
    setNotificationToast(null);

    const hasVideo = Boolean(
      task.result?.mp4 ||
      task.result?.mp4_video ||
      task.result?.output_video ||
      task.result?.final_video_path ||
      task.result?.video_url
    );

    const isEditTask = Boolean(
      task.type === 'edit_project' ||
      task.type === 'one_click' ||
      task.type === 'pipeline' ||
      task.task_type === 'edit_project' ||
      (typeof task.title === 'string' && task.title.includes('ตัดต่อ'))
    );

    const isRenderTask = Boolean(
      !isEditTask && (
        task.type === 'render_video' ||
        task.type === 'render' ||
        task.task_type === 'render_video' ||
        task.task_type === 'render' ||
        (typeof task.title === 'string' && task.title.includes('เรนเดอร์'))
      )
    );

    const isScrapeTask = Boolean(
      task.type === 'scrape_and_plan' ||
      task.task_type === 'scrape_and_plan' ||
      (typeof task.title === 'string' && task.title.includes('วิเคราะห์สินค้า'))
    );

    const isRerollTask = Boolean(
      task.type === 'reroll_script' ||
      task.task_type === 'reroll_script'
    );

    // scripts/api_shot_lists.py's generate_shot_list / batch_generate_audio tasks -- like reroll,
    // this never touches the timeline/editor, so it must not fall through
    // to the generic "newly cut project" -> editor default below.
    const isShotListTask = Boolean(
      task.type === 'generate_shot_list' ||
      task.task_type === 'generate_shot_list' ||
      task.type === 'batch_generate_audio' ||
      task.task_type === 'batch_generate_audio' ||
      (typeof task.title === 'string' && task.title.includes('เตรียมเสียงพากย์'))
    );

    const isImageMetadataTask = Boolean(
      task.type === 'image_metadata' ||
      task.task_type === 'image_metadata'
    );

    // scripts/api_recording.py's finalize_recording_session task -- also
    // belongs on the same script's flow page, not the editor/timeline.
    const isFinalizeRecordingTask = Boolean(
      task.type === 'finalize_recording_session' ||
      task.task_type === 'finalize_recording_session'
    );

    const isSceneIndexingTask = Boolean(
      task.type === 'scene_indexing' ||
      task.task_type === 'scene_indexing' ||
      (typeof task.title === 'string' && task.title.includes('สแกนสารบัญฉาก'))
    );

    const isProductFlowTask = isScrapeTask || isRerollTask || isImageMetadataTask || isShotListTask || isFinalizeRecordingTask || isSceneIndexingTask;
    const projName = !isProductFlowTask
      ? (task.result?.project_name || (Array.isArray(task.result?.items) ? task.result.items.find(i => i?.project_name)?.project_name : null) || task.payload?.project_name)
      : null;
    const productId = task.result?.saved_product?.id || task.result?.product?.id || task.result?.product_id || task.payload?.product_id || (isProductFlowTask ? task.target_id : null);
    const angleId = (isRerollTask || (task.type === 'generate_shot_list' || task.task_type === 'generate_shot_list'))
      ? (task.result?.angle?.angle_id || task.payload?.angle_id)
      : (isFinalizeRecordingTask ? task.payload?.angle_id : null);

    // Determine targetTab if not explicitly provided:
    // 1. Scrape & Plan / script reroll / shot list / batch audio tasks -> Product -> Clip ('flow')
    // 2. Render tasks with video -> Gallery preview ('gallery')
    // 3. Newly cut projects (edit_project / 1-click edit) -> Editor timeline ('editor')
    let targetTab = destinationTab;
    if (!targetTab) {
      if (isProductFlowTask) {
        targetTab = 'flow';
      } else if (hasVideo && isRenderTask) {
        targetTab = 'gallery';
      } else if (isEditTask || projName) {
        targetTab = 'editor';
      } else {
        targetTab = task.target_tab || 'flow';
      }
    }

    const targetId = isProductFlowTask
      ? (productId || task.target_id)
      : (projName || (targetTab === 'editor' ? projName : task.target_id) || productId);

    if (targetTab === 'flow' && (productId || targetId) && onSelectProductForFlow) {
      onSelectProductForFlow(productId || targetId);
    }

    if (onNavigateTab) {
      onNavigateTab(targetTab, {
        targetId,
        projectName: projName,
        angleId,
        taskResult: task.result,
        task,
      });
    }
  }, [onSelectProductForFlow, onNavigateTab]);

  const toggleActivityDrawer = useCallback(() => {
    setIsActivityDrawerOpen(prev => !prev);
  }, []);

  // Memoized because polling replaces `tasks` every 1.5s while a task runs.
  // A fresh object literal here re-rendered every useTaskManager() consumer on
  // each tick -- EditorShell and ProductToClip among them, both large trees --
  // even when the only thing that changed was a field they never read.
  const value = useMemo(() => ({
    tasks,
    activeTasks,
    activeCount,
    completedTasks,
    isActivityDrawerOpen,
    setIsActivityDrawerOpen,
    toggleActivityDrawer,
    notificationToast,
    setNotificationToast,
    taskSyncState,
    refreshTrigger,
    pollTasks,
    cancelTask,
    deleteTask,
    clearCompleted,
    jumpToTaskResult,
    viralMilestones,
    fetchViralMilestones
  }), [
    tasks, activeTasks, activeCount, completedTasks,
    isActivityDrawerOpen, toggleActivityDrawer,
    notificationToast, taskSyncState, refreshTrigger,
    pollTasks, cancelTask, deleteTask, clearCompleted, jumpToTaskResult,
    viralMilestones, fetchViralMilestones
  ]);

  return (
    <TaskContext.Provider value={value}>
      {children}
    </TaskContext.Provider>
  );
}

export function useTaskManager() {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error('useTaskManager must be used within a TaskProvider');
  }
  return context;
}
