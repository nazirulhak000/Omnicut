/**
 * frontend/src/lib/uploadQueue.js — Resumable Chunked Upload Queue (Phase 8.2).
 *
 * Features:
 * - Splits large mobile files (>100MB over Cloudflare Tunnel) into 8MB chunks (`8 * 1024 * 1024`).
 * - Queries `GET /api/uploads/{id}` to sync server byte offset and resume automatically
 *   on `online` and `visibilitychange` events.
 * - Acquires `navigator.wakeLock.request('screen')` while active uploads are running.
 * - Stores queue state in IndexedDB (with in-memory fallback) and notifies subscribers (`UploadTray`).
 */

export const DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024; // 8 MB

const DB_NAME = 'omnicut_upload_queue_db';
const STORE_NAME = 'uploads';

class UploadQueueManager {
  constructor() {
    this.items = new Map();
    this.listeners = new Set();
    this.wakeLockSentinel = null;
    this.isProcessing = false;
    this._boundOnline = () => this.resumeInterrupted();
    this._boundVisibility = () => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        this.resumeInterrupted();
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('online', this._boundOnline);
      document.addEventListener('visibilitychange', this._boundVisibility);
    }
  }

  subscribe(callback) {
    this.listeners.add(callback);
    callback(this.getSnapshot());
    return () => {
      this.listeners.delete(callback);
    };
  }

  getSnapshot() {
    return Array.from(this.items.values()).map((item) => ({ ...item }));
  }

  _emit() {
    const snap = this.getSnapshot();
    for (const cb of this.listeners) {
      try {
        cb(snap);
      } catch (_err) {
        // Ignore listener error
      }
    }
  }

  async _acquireWakeLock() {
    if (typeof navigator === 'undefined' || !navigator.wakeLock) return;
    if (this.wakeLockSentinel) return;
    try {
      this.wakeLockSentinel = await navigator.wakeLock.request('screen');
      if (this.wakeLockSentinel && typeof this.wakeLockSentinel.addEventListener === 'function') {
        this.wakeLockSentinel.addEventListener('release', () => {
          this.wakeLockSentinel = null;
        });
      }
    } catch (_err) {
      this.wakeLockSentinel = null;
    }
  }

  async _releaseWakeLock() {
    if (!this.wakeLockSentinel) return;
    try {
      await this.wakeLockSentinel.release();
    } catch (_err) {
      // Ignore release errors
    } finally {
      this.wakeLockSentinel = null;
    }
  }

  async _saveToIndexedDB(record) {
    if (typeof indexedDB === 'undefined') return;
    try {
      const db = await new Promise((resolve, reject) => {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => {
          const d = req.result;
          if (!d.objectStoreNames.contains(STORE_NAME)) {
            d.createObjectStore(STORE_NAME, { keyPath: 'localId' });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
      await new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        tx.objectStore(STORE_NAME).put({
          localId: record.localId,
          uploadId: record.uploadId,
          filename: record.filename,
          totalSize: record.totalSize,
          offset: record.offset,
          status: record.status,
          productCode: record.productCode,
          productId: record.productId,
          targetDir: record.targetDir,
          result: record.result ? { ...record.result } : null,
          file: record.fileRecord || record.result?.file || null,
          updatedAt: Date.now(),
        });
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
      db.close();
    } catch (_err) {
      // Fallback silently when IndexedDB is unavailable
    }
  }

  /**
   * Add a File/Blob to the resumable upload queue and start uploading.
   * Options:
   * - productId: Target product UUID
   * - targetDir: 'raw' (default) or 'inbox'
   * - filename: Override display / target filename
   * - onProgress: (pct: number, item: object) => void
   * - onComplete: (result: object, item: object) => void
   * - onError: (err: Error, item: object) => void
   * - returnPromise: boolean (if true returns the completion Promise)
   */
  enqueue(file, options = {}) {
    const localId = options.localId || `local_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

    let resolvePromise, rejectPromise;
    const promise = new Promise((resolve, reject) => {
      resolvePromise = resolve;
      rejectPromise = reject;
    });

    const item = {
      localId,
      uploadId: options.uploadId || null,
      file,
      filename: options.filename || file.name || 'video.mp4',
      totalSize: file.size || 0,
      mimeType: file.type || 'video/mp4',
      productCode: options.productCode || null,
      productId: options.productId || null,
      targetDir: options.targetDir || 'raw',
      chunkSize: options.chunkSize || DEFAULT_CHUNK_SIZE,
      offset: 0,
      progress: 0,
      status: 'queued', // queued | uploading | paused | interrupted | completed | error
      error: null,
      result: null,
      fileRecord: null,
      promise,
      _resolve: resolvePromise,
      _reject: rejectPromise,
      onProgress: options.onProgress || null,
      onComplete: options.onComplete || null,
      onError: options.onError || null,
    };

    this.items.set(localId, item);
    this._emit();
    this._saveToIndexedDB(item);
    this._processNext();

    if (options.returnPromise) {
      return promise;
    }
    return localId;
  }

  /**
   * Returns a Promise that resolves with upload completion result or rejects on failure.
   */
  waitFor(localId) {
    const item = this.items.get(localId);
    if (!item) return Promise.reject(new Error(`ไม่พบรายการอัปโหลด '${localId}'`));
    if (item.status === 'completed') return Promise.resolve(item.result);
    if (item.status === 'error') return Promise.reject(new Error(item.error || 'เกิดข้อผิดพลาดในการอัปโหลด'));
    return item.promise;
  }

  getItem(localId) {
    return this.items.get(localId) || null;
  }

  clearCompleted() {
    let changed = false;
    for (const [id, item] of this.items.entries()) {
      if (item.status === 'completed') {
        this.items.delete(id);
        changed = true;
      }
    }
    if (changed) {
      this._emit();
    }
  }

  pause(localId) {
    const item = this.items.get(localId);
    if (!item) return;
    if (item.status === 'uploading' || item.status === 'queued') {
      item.status = 'paused';
      this._emit();
      this._saveToIndexedDB(item);
    }
  }

  async resume(localId) {
    const item = this.items.get(localId);
    if (!item) return;
    if (item.status === 'paused' || item.status === 'interrupted' || item.status === 'error') {
      item.status = 'queued';
      item.error = null;
      this._emit();
      await this._syncServerOffset(item);
      this._processNext();
    }
  }

  retry(localId) {
    return this.resume(localId);
  }

  remove(localId) {
    const item = this.items.get(localId);
    if (!item) return;
    item.status = 'paused';
    if (item._reject && item.status !== 'completed') {
      try { item._reject(new Error('ยกเลิกการอัปโหลดแล้ว')); } catch {}
    }
    this.items.delete(localId);
    this._emit();
  }

  async resumeInterrupted() {
    let hasResumable = false;
    for (const item of this.items.values()) {
      if (item.status === 'interrupted' || item.status === 'uploading') {
        item.status = 'queued';
        item.error = null;
        hasResumable = true;
      }
    }
    if (hasResumable) {
      this._emit();
      await this._processNext();
    }
  }

  async _syncServerOffset(item) {
    if (!item.uploadId) return 0;
    try {
      const res = await fetch(`/api/uploads/${encodeURIComponent(item.uploadId)}`, {
        method: 'GET',
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        if (typeof data.offset === 'number') {
          item.offset = data.offset;
          item.progress = item.totalSize > 0 ? Math.min(100, Math.round((item.offset / item.totalSize) * 100)) : 0;
          this._emit();
          return data.offset;
        }
      }
    } catch (_err) {
      // Network still offline; keep current offset
    }
    return item.offset;
  }

  async _processNext() {
    if (this.isProcessing) return;
    this.isProcessing = true;
    await this._acquireWakeLock();

    try {
      while (true) {
        const nextItem = Array.from(this.items.values()).find((i) => i.status === 'queued');
        if (!nextItem) break;
        await this._uploadItem(nextItem);
      }
    } finally {
      this.isProcessing = false;
      const anyActive = Array.from(this.items.values()).some(
        (i) => i.status === 'uploading' || i.status === 'queued'
      );
      if (!anyActive) {
        await this._releaseWakeLock();
      }
    }
  }

  async _uploadItem(item) {
    item.status = 'uploading';
    item.error = null;
    this._emit();

    try {
      // 1. Initialize upload session if needed
      if (!item.uploadId) {
        const initRes = await fetch('/api/uploads/init', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            filename: item.filename,
            total_size: item.totalSize,
            mime_type: item.mimeType,
            product_code: item.productCode,
            product_id: item.productId,
            target_dir: item.targetDir,
          }),
        });
        if (!initRes.ok) {
          throw new Error(`เริ่มเซสชันอัปโหลดไม่สำเร็จ (${initRes.status})`);
        }
        const initData = await initRes.json();
        item.uploadId = initData.upload_id;
        item.chunkSize = initData.chunk_size || DEFAULT_CHUNK_SIZE;
        item.offset = initData.offset || 0;
        await this._saveToIndexedDB(item);
      } else {
        // Query server offset before resuming
        await this._syncServerOffset(item);
      }

      // 2. Upload chunks sequentially from current server offset
      while (item.offset < item.totalSize) {
        if (item.status !== 'uploading') {
          return; // Paused or removed
        }

        const end = Math.min(item.offset + item.chunkSize, item.totalSize);
        const chunkBlob = item.file.slice(item.offset, end);

        const patchRes = await fetch(`/api/uploads/${encodeURIComponent(item.uploadId)}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/octet-stream',
            'Upload-Offset': String(item.offset),
          },
          credentials: 'include',
          body: chunkBlob,
        });

        if (patchRes.status === 409) {
          // Offset out of sync: recover from server's authoritative offset
          const errBody = await patchRes.json().catch(() => ({}));
          if (typeof errBody.current_offset === 'number') {
            item.offset = errBody.current_offset;
            continue;
          }
          await this._syncServerOffset(item);
          continue;
        }

        if (!patchRes.ok) {
          throw new Error(`ส่งข้อมูลส่วนย่อยไม่สำเร็จ (${patchRes.status})`);
        }

        const patchData = await patchRes.json();
        item.offset = typeof patchData.offset === 'number' ? patchData.offset : end;
        item.progress = Math.min(100, Math.round((item.offset / item.totalSize) * 100));
        if (typeof item.onProgress === 'function') {
          try { item.onProgress(item.progress, item); } catch {}
        }
        this._emit();
        await this._saveToIndexedDB(item);
      }

      // 3. Finalize & verify magic bytes + SHA-256 deduplication
      const completeRes = await fetch(`/api/uploads/${encodeURIComponent(item.uploadId)}/complete`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!completeRes.ok) {
        const errData = await completeRes.json().catch(() => ({}));
        throw new Error(errData.detail || `ยืนยันไฟล์ไม่สำเร็จ (${completeRes.status})`);
      }

      const completeData = await completeRes.json();
      item.status = 'completed';
      item.progress = 100;
      item.result = completeData;
      item.fileRecord = completeData.file || null;
      if (typeof item.onProgress === 'function') {
        try { item.onProgress(100, item); } catch {}
      }
      if (item._resolve) {
        item._resolve(completeData);
      }
      if (typeof item.onComplete === 'function') {
        try { item.onComplete(completeData, item); } catch (cbErr) { console.error('Error in onComplete hook:', cbErr); }
      }
      this._emit();
      await this._saveToIndexedDB(item);
    } catch (err) {
      const isOffline = typeof navigator !== 'undefined' && navigator.onLine === false;
      item.status = isOffline ? 'interrupted' : 'error';
      item.error = err?.message || 'การเชื่อมต่อขัดข้อง ระบบจะส่งต่อให้อัตโนมัติเมื่อสัญญาณกลับมา';
      if (!isOffline && item._reject) {
        item._reject(err);
      }
      if (typeof item.onError === 'function') {
        try { item.onError(err, item); } catch (cbErr) { console.error('Error in onError hook:', cbErr); }
      }
      this._emit();
      await this._saveToIndexedDB(item);
    }
  }
}

export const uploadQueue = new UploadQueueManager();
export default uploadQueue;
