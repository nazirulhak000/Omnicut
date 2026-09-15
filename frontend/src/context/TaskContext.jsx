import React, { createContext, useContext, useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { getActiveTasks, cancelTaskApi, deleteTaskApi, clearCompletedTasksApi, getTiktokMilestones } from '../api';

const TaskContext = createContext(null);

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
  const [tasks, setTasks] = useState(() => {
    try {
      const saved = localStorage.getItem('capcut_task_cache');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false);
  const [notificationToast, setNotificationToast] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [viralMilestones, setViralMilestones] = useState([]);

  // Check TikTok viral milestones periodically
  const notifiedMilestonesRef = useRef(new Set());

  const fetchViralMilestones = useCallback(async () => {
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
              title: '🔥 คลิปปังทะลุเป้า!',
              message: `คลิป "${m.product_name}" ทำยอดวิวทะลุ ${m.views.toLocaleString()} วิวแล้ว!`,
              milestone: m,
              time: Date.now()
            });
          }
        });
      }
    } catch (e) {
      // Quiet fail if analytics not populated yet
    }
  }, []);

  // Fetch viral milestones on-demand (no background polling)

  // Keep a map of previous statuses to detect transitions (e.g. processing -> completed)
  const prevStatusesRef = useRef({});
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
      localStorage.setItem('capcut_task_cache', JSON.stringify(tasks.slice(0, 20)));
    } catch (e) {
      console.error('Failed to cache tasks:', e);
    }
  }, [tasks]);

  const fetchAndApplyTasks = useCallback(async () => {
    const res = await getActiveTasks();
    if (res && Array.isArray(res.tasks)) {
      const fetchedTasks = res.tasks;

      // Check for state transitions
      fetchedTasks.forEach(t => {
        const prevStatus = prevStatusesRef.current[t.id];
        if (prevStatus && prevStatus !== t.status) {
          if (t.status === 'completed') {
            playCompletionChime();
            setNotificationToast({
              type: 'success',
              title: '🎉 งานเสร็จสมบูรณ์!',
              message: t.step_label || t.title,
              task: t,
              time: Date.now()
            });
            // Auto-refresh child views
            setRefreshTrigger(prev => prev + 1);
          } else if (t.status === 'failed') {
            setNotificationToast({
              type: 'error',
              title: '❌ งานไม่สำเร็จ',
              message: t.error || t.step_label || t.title,
              task: t,
              time: Date.now()
            });
          }
        }
        prevStatusesRef.current[t.id] = t.status;
      });

      // Initialize prevStatuses for new tasks
      fetchedTasks.forEach(t => {
        if (!prevStatusesRef.current[t.id]) {
          prevStatusesRef.current[t.id] = t.status;
        }
      });

      setTasks(fetchedTasks);
    }
  }, []);

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

  // Adaptive Polling: 1.5s when active tasks exist, 6s when idle
  useEffect(() => {
    pollTasks(); // Initial fetch on mount / F5
    const intervalTime = activeCount > 0 ? 1500 : 6000;
    const timer = setInterval(pollTasks, intervalTime);
    return () => clearInterval(timer);
  }, [activeCount, pollTasks]);

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

    const isProductFlowTask = isScrapeTask || isRerollTask || isImageMetadataTask || isShotListTask || isFinalizeRecordingTask;
    const projName = !isProductFlowTask ? (task.result?.project_name || task.payload?.project_name) : null;
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

    const targetId = isProductFlowTask ? (productId || task.target_id) : (projName || task.target_id || productId);

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
    notificationToast, refreshTrigger,
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
