import React, { useState, useEffect, useMemo } from 'react';
import {
  Smartphone, RefreshCw, Download, CheckCircle2, AlertCircle,
  X, CheckSquare, Square, FolderDown, Sparkles, Search, HardDrive
} from 'lucide-react';
import { getIPhoneStatus, getIPhoneClips, pullIPhoneClips, getProducts } from '../api';

export default function IPhoneDirectModal({ isOpen, onClose, onSuccess }) {
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [loadingClips, setLoadingClips] = useState(false);
  const [transferring, setTransferring] = useState(false);

  const [deviceInfo, setDeviceInfo] = useState(null);
  const [clips, setClips] = useState([]);
  const [selectedNames, setSelectedNames] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all'); // 'all', 'new', 'imported'

  // Destination options
  const [targetType, setTargetType] = useState('inbox'); // 'inbox' or 'product'
  const [products, setProducts] = useState([]);
  const [selectedProductId, setSelectedProductId] = useState('');
  const [resultMsg, setResultMsg] = useState(null);

  // Load device status & clips on open
  useEffect(() => {
    if (!isOpen) return;
    refreshAll();
    loadProducts();
  }, [isOpen]);

  const loadProducts = async () => {
    try {
      const data = await getProducts();
      setProducts(Array.isArray(data) ? data : (data?.products || []));
    } catch {
      // ignore
    }
  };

  const refreshAll = async () => {
    setLoadingStatus(true);
    setResultMsg(null);
    try {
      const status = await getIPhoneStatus();
      setDeviceInfo(status);

      if (status?.connected && status?.accessible) {
        setLoadingClips(true);
        const clipData = await getIPhoneClips(60);
        setClips(clipData?.clips || []);
        // Auto-select new unimported clips by default
        const unimported = (clipData?.clips || []).filter(c => !c.already_imported).map(c => c.name);
        setSelectedNames(new Set(unimported));
      } else {
        setClips([]);
        setSelectedNames(new Set());
      }
    } catch (err) {
      setDeviceInfo({
        connected: false,
        accessible: false,
        error: err.message || 'ไม่สามารถติดต่อ iPhone ได้'
      });
      setClips([]);
    } finally {
      setLoadingStatus(false);
      setLoadingClips(false);
    }
  };

  // Filtered clips
  const filteredClips = useMemo(() => {
    return clips.filter(c => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        if (!c.name.toLowerCase().includes(q) && !c.file_name.toLowerCase().includes(q)) {
          return false;
        }
      }
      if (filterType === 'new') return !c.already_imported;
      if (filterType === 'imported') return c.already_imported;
      return true;
    });
  }, [clips, searchQuery, filterType]);

  const toggleSelect = (name) => {
    const next = new Set(selectedNames);
    if (next.has(name)) {
      next.delete(name);
    } else {
      next.add(name);
    }
    setSelectedNames(next);
  };

  const selectAll = () => {
    setSelectedNames(new Set(filteredClips.map(c => c.name)));
  };

  const selectOnlyNew = () => {
    setSelectedNames(new Set(filteredClips.filter(c => !c.already_imported).map(c => c.name)));
  };

  const clearSelection = () => {
    setSelectedNames(new Set());
  };

  const handlePull = async () => {
    if (selectedNames.size === 0) return;
    setTransferring(true);
    setResultMsg(null);

    try {
      const payload = {
        clip_names: Array.from(selectedNames),
        target_type: targetType,
        product_id: targetType === 'product' ? selectedProductId : null
      };

      const res = await pullIPhoneClips(payload);
      setResultMsg({
        type: 'success',
        text: `ดึงคลิปสำเร็จ ${res.copied_count} ไฟล์ (ข้ามที่มีแล้ว ${res.skipped_count} ไฟล์) บันทึกลง ${res.target_folder}`
      });

      // Refresh clips list to update already_imported indicators
      const clipData = await getIPhoneClips(60);
      setClips(clipData?.clips || []);
      setSelectedNames(new Set());

      if (onSuccess) {
        onSuccess(res);
      }
    } catch (err) {
      setResultMsg({
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'การดึงคลิปล้มเหลว'
      });
    } finally {
      setTransferring(false);
    }
  };

  if (!isOpen) return null;

  const isConnected = deviceInfo?.connected && deviceInfo?.accessible;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden text-slate-200 animate-scaleUp">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Smartphone className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                ดึงคลิปตรงจาก iPhone (USB Direct Ingest)
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium">
                  ความเร็วสูง 100% สายตรง
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                ดึงคลิปวิดีโอต้นฉบับตรงจาก iPhone ผ่านสาย USB เข้าสู่คลังโปรแกรมโดยตรง ไม่ต้องต่อเน็ต ไม่ต้องรอ AI
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-slate-800 active:scale-[0.95] transition-[background-color,border-color,color,transform] duration-150 active:duration-100 ease-out cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Device Status Bar */}
        <div className="px-5 py-3 border-b border-slate-800/80 bg-slate-950/30 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            {loadingStatus ? (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <RefreshCw className="w-4 h-4 animate-spin text-sky-400" />
                กำลังตรวจสอบการเชื่อมต่อ iPhone...
              </div>
            ) : isConnected ? (
              <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
                <span className="inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
                เชื่อมต่อ {deviceInfo?.device_name || 'Apple iPhone'} สำเร็จ
                <span className="text-slate-500">•</span>
                <span className="text-slate-300">โฟลเดอร์ {deviceInfo?.folder} ({deviceInfo?.total_videos} คลิป)</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-xs text-amber-400 font-medium">
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                {deviceInfo?.error || 'กรุณาเสียบสาย USB และปลดล็อกหน้าจอ iPhone (FaceID/Passcode)'}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={refreshAll}
            disabled={loadingStatus || loadingClips || transferring}
            className="px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 hover:text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingStatus ? 'animate-spin' : ''}`} />
            ตรวจจับอุปกรณ์ใหม่
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col p-5 overflow-hidden gap-4">
          
          {/* Result Banner if any */}
          {resultMsg && (
            <div className={`px-4 py-2.5 rounded-xl border text-xs flex items-center gap-2 ${
              resultMsg.type === 'success' 
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300' 
                : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
            }`}>
              {resultMsg.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              )}
              <span>{resultMsg.text}</span>
            </div>
          )}

          {/* Filtering and Selection Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-950/40 p-2.5 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 flex-1 min-w-[200px]">
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="ค้นหาชื่อคลิป เช่น 8212..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-700/80 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              {/* Filter Pills */}
              <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setFilterType('all')}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    filterType === 'all' ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  ทั้งหมด ({clips.length})
                </button>
                <button
                  type="button"
                  onClick={() => setFilterType('new')}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    filterType === 'new' ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  เฉพาะคลิปใหม่ ({clips.filter(c => !c.already_imported).length})
                </button>
                <button
                  type="button"
                  onClick={() => setFilterType('imported')}
                  className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                    filterType === 'imported' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  ในคลังแล้ว ({clips.filter(c => c.already_imported).length})
                </button>
              </div>
            </div>

            {/* Quick Selection Buttons */}
            <div className="flex items-center gap-1.5 text-xs">
              <button
                type="button"
                onClick={selectOnlyNew}
                className="px-2 py-1 text-sky-400 hover:text-sky-300 hover:bg-sky-500/10 rounded transition-colors"
              >
                เลือกเฉพาะคลิปใหม่
              </button>
              <span className="text-slate-600">|</span>
              <button
                type="button"
                onClick={selectAll}
                className="px-2 py-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded transition-colors"
              >
                เลือกทั้งหมด
              </button>
              <span className="text-slate-600">|</span>
              <button
                type="button"
                onClick={clearSelection}
                className="px-2 py-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
              >
                ล้าง
              </button>
              <span className="ml-2 font-medium text-slate-200 px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                เลือก {selectedNames.size} คลิป
              </span>
            </div>
          </div>

          {/* Clips List Table */}
          <div className="flex-1 overflow-y-auto border border-slate-800 rounded-xl bg-slate-950/20 divide-y divide-slate-800/60">
            {loadingClips ? (
              <div className="p-12 flex flex-col items-center justify-center gap-3 text-slate-400">
                <RefreshCw className="w-8 h-8 animate-spin text-sky-400" />
                <p className="text-xs">กำลังสแกนรายชื่อคลิปจาก iPhone ผ่านสาย USB...</p>
              </div>
            ) : !isConnected ? (
              <div className="p-12 flex flex-col items-center justify-center gap-3 text-slate-400">
                <Smartphone className="w-10 h-10 text-slate-600" />
                <p className="text-sm font-medium text-slate-300">ไม่สามารถเชื่อมต่อคลังคลิป iPhone ได้</p>
                <p className="text-xs text-slate-500 text-center max-w-md">
                  กรุณาเสียบสาย USB ระหว่างคอมกับ iPhone แล้วปลดล็อกหน้าจอด้วย FaceID หรือรหัสผ่าน จากนั้นกดปุ่ม "ตรวจจับอุปกรณ์ใหม่"
                </p>
              </div>
            ) : filteredClips.length === 0 ? (
              <div className="p-12 flex flex-col items-center justify-center gap-2 text-slate-400">
                <FolderDown className="w-8 h-8 text-slate-600" />
                <p className="text-xs">ไม่พบคลิปตรงตามตัวกรองที่เลือก</p>
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 sticky top-0 text-slate-400 border-b border-slate-800 font-medium">
                  <tr>
                    <th className="py-2.5 px-4 w-10">
                      <button
                        type="button"
                        onClick={() => {
                          if (selectedNames.size === filteredClips.length) {
                            clearSelection();
                          } else {
                            selectAll();
                          }
                        }}
                        className="text-slate-400 hover:text-slate-200"
                      >
                        {selectedNames.size > 0 && selectedNames.size === filteredClips.length ? (
                          <CheckSquare className="w-4 h-4 text-sky-400" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>
                    </th>
                    <th className="py-2.5 px-3">ชื่อไฟล์คลิป</th>
                    <th className="py-2.5 px-3">ขนาด</th>
                    <th className="py-2.5 px-3">วันที่ถ่าย</th>
                    <th className="py-2.5 px-3">สถานะในระบบ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/40">
                  {filteredClips.map((clip) => {
                    const isSelected = selectedNames.has(clip.name);
                    return (
                      <tr
                        key={clip.name}
                        onClick={() => toggleSelect(clip.name)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-sky-500/10 hover:bg-sky-500/15'
                            : 'hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="py-2.5 px-4" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => toggleSelect(clip.name)}
                            className="text-slate-400 hover:text-slate-200"
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-sky-400" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                        <td className="py-2.5 px-3 font-mono font-medium text-slate-200">
                          {clip.file_name}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {clip.size}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {clip.date}
                        </td>
                        <td className="py-2.5 px-3">
                          {clip.already_imported ? (
                            <span 
                              className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
                              title={`นำเข้าแล้วที่: ${clip.imported_path}`}
                            >
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              ในคลังแล้ว
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-500/10 border border-sky-500/20 text-sky-400">
                              <Sparkles className="w-3 h-3 text-sky-400" />
                              คลิปใหม่
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Destination Target Settings */}
          <div className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex items-center gap-4">
              <span className="font-medium text-slate-300 flex items-center gap-1.5">
                <HardDrive className="w-4 h-4 text-slate-400" />
                โฟลเดอร์ปลายทาง:
              </span>
              <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="radio"
                  name="targetType"
                  value="inbox"
                  checked={targetType === 'inbox'}
                  onChange={() => setTargetType('inbox')}
                  className="text-sky-500 focus:ring-sky-500 bg-slate-800 border-slate-700"
                />
                <span>คลังรับเข้ากลาง (00_Inbox/iPhone_Clips/)</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-slate-300 hover:text-white">
                <input
                  type="radio"
                  name="targetType"
                  value="product"
                  checked={targetType === 'product'}
                  onChange={() => setTargetType('product')}
                  className="text-sky-500 focus:ring-sky-500 bg-slate-800 border-slate-700"
                />
                <span>ระบุสินค้าโดยตรง (01_Raw/&lt;สินค้า&gt;/)</span>
              </label>
            </div>

            {targetType === 'product' && (
              <div className="flex items-center gap-2">
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-sky-500 min-w-[240px]"
                >
                  <option value="">-- เลือกสินค้า --</option>
                  {products.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.name.slice(0, 40)}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-slate-800 bg-slate-950/80">
          <div className="text-xs text-slate-400">
            {selectedNames.size > 0 ? (
              <span>พร้อมดึง <strong className="text-sky-400">{selectedNames.size}</strong> คลิปเข้าคลัง</span>
            ) : (
              <span>กรุณาติ๊กเลือกคลิปที่ต้องการดึงจากรายการด้านบน</span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={transferring}
              className="px-4 py-2 rounded-xl text-xs font-medium border border-slate-700 bg-slate-800 hover:bg-slate-700/80 text-slate-300 transition-colors"
            >
              ปิดหน้าต่าง
            </button>
            <button
              type="button"
              onClick={handlePull}
              disabled={!isConnected || selectedNames.size === 0 || transferring || (targetType === 'product' && !selectedProductId)}
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white shadow-lg shadow-sky-500/20 active:scale-[0.97] disabled:active:scale-100 transition-[background-color,border-color,color,transform,opacity,box-shadow] duration-150 active:duration-100 ease-out flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {transferring ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  กำลังดึงข้อมูลตรงผ่านสาย... (ห้ามถอดสาย)
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  ดึงคลิปที่เลือก ({selectedNames.size})
                </>
              )}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
