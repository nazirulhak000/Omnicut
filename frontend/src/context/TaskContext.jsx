import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { getActiveTasks, cancelTaskApi, deleteTaskApi, clearCompletedTasksApi } from '../api';

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

  // Keep a map of previous statuses to detect transitions (e.g. processing -> completed)
  const prevStatusesRef = useRef({});
  const isPollingRef = useRef(false);

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

  const pollTasks = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    try {
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
    } catch (err) {
      // Network failure or backend temporarily unavailable
    } finally {
      isPollingRef.current = false;
    }
  }, []);

  // Adaptive Polling: 1.5s when active tasks exist, 6s when idle
  useEffect(() => {
    pollTasks(); // Initial fetch on mount / F5
    const intervalTime = activeCount > 0 ? 1500 : 6000;
    const timer = setInterval(pollTasks, intervalTime);
    return () => clearInterval(timer);
  }, [activeCount, pollTasks]);

  // Actions
  const cancelTask = async (taskId) => {
    try {
      await cancelTaskApi(taskId);
      await pollTasks();
    } catch (e) {
      console.error('Cancel task failed:', e);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      await deleteTaskApi(taskId);
      setTasks(prev => prev.filter(t => t.id !== taskId));
    } catch (e) {
      console.error('Delete task failed:', e);
    }
  };

  const clearCompleted = async () => {
    try {
      await clearCompletedTasksApi();
      setTasks(prev => prev.filter(t => t.status === 'processing' || t.status === 'queued'));
    } catch (e) {
      console.error('Clear completed tasks failed:', e);
    }
  };

  const jumpToTaskResult = (task, destinationTab = null) => {
    if (!task) return;
    setIsActivityDrawerOpen(false);
    setNotificationToast(null);

    const isRenderTask =
      task.type === 'render_video' ||
      task.type === 'render' ||
      task.task_type === 'render_video' ||
      task.task_type === 'render' ||
      (typeof task.title === 'string' && (task.title.includes('เรนเดอร์') || task.title.includes('ตัดต่อ')));

    const projName = task.result?.project_name || task.payload?.project_name || task.target_id;

    // For video creation/render tasks, navigate directly to Timeline Editor ('editor') by default
    let targetTab = destinationTab;
    if (!targetTab) {
      targetTab = isRenderTask ? 'editor' : (task.target_tab || 'flow');
    }

    const targetId = projName || task.target_id || (task.result?.saved_product?.id || task.result?.product?.id);

    if (targetTab === 'flow' && targetId && onSelectProductForFlow) {
      onSelectProductForFlow(targetId);
    }

    if (onNavigateTab) {
      onNavigateTab(targetTab, {
        targetId,
        projectName: projName,
        taskResult: task.result,
        task,
      });
    }
  };

  const toggleActivityDrawer = () => {
    setIsActivityDrawerOpen(prev => !prev);
  };

  const value = {
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
    jumpToTaskResult
  };

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
