import React, { useState } from 'react';
import { Film, Download, Folder, RefreshCw, Calendar, HardDrive, Trash2, AlertTriangle, X, CheckCircle2, Play } from 'lucide-react';
import { openFolder, deleteFile } from '../api';

export default function ExportGallery({ exportsList, onRefresh }) {
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const handleOpenExportsFolder = () => {
    openFolder('exports');
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      // Pause videos to release any active streaming
      const videoEls = document.querySelectorAll('video');
      videoEls.forEach(v => {
        try {
          v.pause();
        } catch (e) {}
      });

      await deleteFile(deleteTarget.path);
      showToast(`ลบไฟล์ ${deleteTarget.name} เรียบร้อยแล้ว`);
      setDeleteTarget(null);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert('ไม่สามารถลบไฟล์ได้: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6 relative">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-2xl bg-emerald-500/90 text-white font-bold text-xs backdrop-blur-md shadow-2xl animate-bounce">
          <CheckCircle2 className="w-4 h-4" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 sm:p-6 glass-panel border border-white/10 shadow-2xl">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FE2C55] to-rose-600 flex items-center justify-center shadow-lg shadow-[#FE2C55]/30">
              <Film className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
                คลังวิดีโอที่ตัดเสร็จแล้ว (Export Gallery)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                ไฟล์วิดีโอทั้งหมด ({exportsList?.length || 0} คลิป) พร้อมนำไปโพสต์ลง TikTok / Reels / Shorts
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
          <button
            onClick={onRefresh}
            className="p-2.5 px-3.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors text-xs font-bold flex items-center gap-2 border border-slate-700 cursor-pointer"
            title="รีเฟรชคลังวิดีโอ"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>รีเฟรช</span>
          </button>
          <button
            onClick={handleOpenExportsFolder}
            className="py-2.5 px-4 rounded-xl bg-[#232A3B] hover:bg-[#323B52] border border-white/10 text-white text-xs font-bold flex items-center gap-2 transition-all shadow-md cursor-pointer hidden sm:flex"
          >
            <Folder className="w-4 h-4 text-[#25F4EE]" />
            <span>เปิดโฟลเดอร์ในเครื่อง</span>
          </button>
        </div>
      </div>

      {/* Responsive Grid of exported videos */}
      {exportsList && exportsList.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 sm:gap-5">
          {exportsList.map((item, idx) => (
            <div
              key={item.rel_path || idx}
              className="glass-card overflow-hidden hover:border-[#25F4EE]/50 flex flex-col justify-between transition-all hover:scale-[1.01] group relative"
            >
              <div>
                {/* Video Player (9:16 vertical TikTok ratio) */}
                <div className="bg-black aspect-[9/16] max-h-[380px] w-full flex items-center justify-center border-b border-white/10 relative overflow-hidden">
                  <video
                    key={item.rel_path}
                    controls
                    playsInline
                    preload="metadata"
                    src={`/api/media/${encodeURI(item.rel_path.replace(/\\/g, '/'))}`}
                    className="w-full h-full object-contain"
                  />
                  {/* Quick Delete Floating Button */}
                  <button
                    onClick={() => setDeleteTarget(item)}
                    className="absolute top-2.5 right-2.5 p-2 rounded-xl bg-black/60 hover:bg-red-600 text-slate-300 hover:text-white backdrop-blur-md opacity-80 group-hover:opacity-100 transition-all cursor-pointer shadow-lg z-10"
                    title="ลบคลิปวิดีโอนี้"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Video Info */}
                <div className="p-3.5 sm:p-4 space-y-2">
                  <h3 className="font-bold text-xs sm:text-sm text-white truncate" title={item.name}>
                    📹 {item.name}
                  </h3>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1 font-mono text-[#25F4EE]">
                      <HardDrive className="w-3 h-3 flex-shrink-0" />
                      {item.size_mb} MB
                    </span>
                    <span className="flex items-center gap-1 text-slate-400 truncate">
                      <Calendar className="w-3 h-3 flex-shrink-0" />
                      {item.modified_time}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-3.5 sm:p-4 pt-0 flex items-center gap-2">
                <a
                  href={`/api/media/${item.rel_path}`}
                  download={item.name}
                  className="flex-1 py-2.5 px-3 rounded-xl bg-[#232A3B] hover:bg-[#FE2C55] text-white text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>ดาวน์โหลด .MP4</span>
                </a>
                <button
                  onClick={() => setDeleteTarget(item)}
                  className="p-2.5 rounded-xl bg-red-500/10 hover:bg-red-600 text-red-400 hover:text-white border border-red-500/20 transition-all cursor-pointer"
                  title="ลบคลิปวิดีโอ"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16 p-8 glass-card space-y-3">
          <Film className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-300">ยังไม่มีวิดีโอในคลัง Exports</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            สร้างคลิปรีวิวป้ายยาแรกในแท็บ <b>1. Studio Creator</b> แล้วไฟล์พร้อมโพสต์จะมาปรากฏที่นี่ครับ!
          </p>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="relative w-full max-w-sm p-6 glass-panel border border-red-500/40 shadow-2xl rounded-3xl text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-red-500/20 text-red-400 flex items-center justify-center mx-auto border border-red-500/30">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-white">ยืนยันการลบวิดีโอ?</h3>
              <p className="text-xs text-slate-300 font-mono break-all bg-black/40 p-2.5 rounded-xl border border-white/5 mt-2">
                {deleteTarget.name}
              </p>
              <p className="text-[11px] text-slate-400 pt-1">
                ไฟล์จะถูกลบออกจากเครื่องอย่างถาวร
              </p>
            </div>

            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition-colors cursor-pointer"
              >
                ยกเลิก
              </button>
              <button
                onClick={confirmDelete}
                disabled={deleting}
                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-600/30 transition-all cursor-pointer"
              >
                {deleting ? 'กำลังลบ...' : 'ยืนยันลบไฟล์'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
