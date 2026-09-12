import React, { useEffect, useMemo, useState } from 'react';
import {
  Database, FileText, Globe2, ImagePlus, Link2, RefreshCw, Trash2, Upload, X
} from 'lucide-react';
import { Modal } from './ui';
import { toMediaUrl } from '../lib/mediaUrl';

function getImageReference(image) {
  if (!image) return '';
  if (typeof image === 'string') return image;
  return image.rel_path || image.path || image.local_path || image.url || image.src || '';
}

function getImageName(image, index) {
  if (typeof image === 'object' && image?.name) return image.name;
  const ref = getImageReference(image);
  return ref.split(/[\\/]/).pop() || `รูปอ้างอิง ${index + 1}`;
}

function imageOrigin(image) {
  const ref = getImageReference(image);
  if (/^https?:\/\//i.test(ref)) return 'URL จากหน้าเว็บสินค้า';
  if (typeof image === 'object' && (image.rel_path || image.path || image.local_path)) {
    return 'ไฟล์ที่แนบจากเครื่องนี้';
  }
  return 'ข้อมูลรูปภาพจากสินค้า';
}

function displayValue(value) {
  if (value === null || value === undefined || value === '') return 'ไม่มีข้อมูล';
  if (Array.isArray(value)) {
    return value.length
      ? value.map((item) => typeof item === 'object' ? JSON.stringify(item) : String(item)).join(' · ')
      : 'ไม่มีข้อมูล';
  }
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

function sourceTextWithoutDuplicate(description, rawText) {
  const duplicateLines = new Set(
    String(description || '')
      .split(/\r?\n/)
      .map((line) => line.replace(/\s+/g, ' ').trim().toLocaleLowerCase())
      .filter(Boolean)
  );
  return String(rawText || '')
    .split(/\r?\n/)
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter((line) => line && !duplicateLines.has(line.toLocaleLowerCase()))
    .join('\n');
}

function DataRow({ label, value, multiline = false }) {
  const rendered = displayValue(value);
  return (
    <div className="grid grid-cols-[minmax(100px,0.28fr)_minmax(0,0.72fr)] gap-3 py-2.5 border-b border-white/[0.06] last:border-b-0">
      <dt className="text-[11px] font-semibold text-slate-500">{label}</dt>
      <dd className={`text-xs text-slate-200 break-words ${multiline ? 'whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto' : ''}`}>
        {rendered}
      </dd>
    </div>
  );
}

function Section({ icon: Icon, title, hint, children }) {
  return (
    <section className="rounded-2xl border border-white/[0.08] bg-white/[0.025] overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/[0.07]">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="w-4 h-4 text-[#25F4EE] flex-shrink-0" />
          <h4 className="text-sm font-bold text-white truncate">{title}</h4>
        </div>
        {hint && <span className="text-[10px] text-slate-500 text-right">{hint}</span>}
      </div>
      <div className="px-4 py-2">{children}</div>
    </section>
  );
}

export default function ProductMetadataModal({
  product,
  isOpen,
  onClose,
  onAddImages,
  onRemoveImage,
  onPreviewSource,
  onPreviewImages,
  onApplySource,
  onSaveMetadata,
  sourcePreview,
  onCancelPreview,
  imageInputRef,
  uploading,
  refreshingSource,
  savingMetadata,
  removingIndex,
  maxImages = 20,
}) {
  const images = Array.isArray(product?.images) ? product.images : [];
  const [draft, setDraft] = useState({});
  const [previewDraft, setPreviewDraft] = useState({});
  const [selectedPreviewFields, setSelectedPreviewFields] = useState({});

  useEffect(() => {
    if (!product) return;
    setDraft({
      name: product.name || product.title || '',
      url: product.url || '',
      tiktok_product_id: product.tiktok_product_id || '',
      price_note: product.price_note || '',
      description: product.description || '',
      raw_text: product.raw_text || '',
      specs: Array.isArray(product.specs) ? product.specs.join('\n') : product.specs || '',
      selling_points: Array.isArray(product.selling_points) ? product.selling_points.join('\n') : product.selling_points || '',
      pain_points: Array.isArray(product.pain_points) ? product.pain_points.join('\n') : product.pain_points || '',
    });
  }, [product]);

  useEffect(() => {
    const changed = sourcePreview?.changed_fields || [];
    setSelectedPreviewFields(Object.fromEntries(changed.map((field) => [field, true])));
    setPreviewDraft({
      description: sourcePreview?.incoming?.description || '',
      raw_text: sourcePreview?.incoming?.raw_text || '',
    });
  }, [sourcePreview]);

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));
  const lines = (value) => String(value || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const previewValue = (value) => {
    if (Array.isArray(value)) return value.length ? value.join('\n') : 'ไม่มีข้อมูล';
    if (value && typeof value === 'object') return JSON.stringify(value, null, 2);
    return value || 'ไม่มีข้อมูล';
  };
  const previewFields = [
    ['name', 'ชื่อ/หัวข้อ'], ['url', 'URL ต้นทาง'], ['description', 'คำอธิบาย'],
    ['raw_text', 'ข้อความต้นฉบับ'], ['price_note', 'ราคา'], ['specs', 'สเปก'],
    ['selling_points', 'จุดขาย'], ['pain_points', 'Pain points'], ['images', 'รูปอ้างอิง'],
  ];
  const sourceSnapshot = useMemo(() => {
    if (!product) return {};
    const sourceKeys = [
      'id', 'product_code', 'name', 'url', 'platform', 'category',
      'price_note', 'target_buyer', 'description', 'raw_text', 'specs',
      'pain_points', 'selling_points', 'thumbnail', 'images',
      'created_at', 'updated_at', 'metadata_source', 'source_warning'
    ];
    return Object.fromEntries(sourceKeys.map((key) => [key, product[key] ?? null]));
  }, [product]);

  const sourceMethod = product?.metadata_source === 'derived_from_angles'
      ? 'ข้อมูลชุดนี้สรุปย้อนกลับจาก key features และ pain points ในสคริปต์เดิม ไม่ใช่ raw data จากหน้าเว็บ'
    : product?.metadata_source === 'vision_image'
      ? 'อ่านจากรูปอ้างอิงสินค้าด้วย Vision — ตรวจสอบตัวเลขและรุ่นใน preview ก่อนบันทึก'
      : product?.metadata_source === 'html_body'
      ? 'อ่านจากรายละเอียดสินค้าที่อยู่ใน HTML โดยตรง'
      : product?.metadata_source === 'browser_dom'
      ? 'ดึงจากข้อความที่มองเห็นจริงหลังหน้าเว็บ render ด้วย JavaScript'
      : product?.metadata_source === 'html_meta'
        ? 'ดึงจาก metadata ที่หน้าเว็บประกาศใน HTML'
        : product?.url
          ? 'ข้อมูลหลักมาจากการดึงหน้าเว็บตาม URL สินค้า'
          : product?.raw_text
            ? 'ข้อมูลหลักมาจากข้อความที่ผู้ใช้กรอก'
            : images.length
              ? 'ข้อมูลหลักมาจากรูปอ้างอิงที่แนบ'
              : 'ยังไม่มีแหล่งข้อมูลต้นทางที่บันทึกไว้';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="ข้อมูลสินค้าและแหล่งข้อมูล AI"
      subtitle="ตรวจสอบได้ว่าระบบดึงอะไรมา และข้อมูลใดถูกเก็บไว้ใช้สร้างสคริปต์"
      maxWidth="max-w-5xl"
    >
      {!product ? null : (
        <div className="space-y-4">
          {onSaveMetadata && (
            <Section icon={FileText} title="แก้ไขข้อมูลก่อนส่งให้ AI" hint="บันทึกเฉพาะเมื่อกดปุ่ม">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="sm:col-span-2 text-xs font-semibold text-slate-300">
                  ชื่อสินค้า / หัวข้อสั้น
                  <input value={draft.name || ''} onChange={(event) => updateDraft('name', event.target.value)} maxLength={180} className="mt-1 w-full rounded-xl border border-white/[0.1] bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/60" placeholder="เช่น GoChek GC-ULTRA S24" />
                </label>
                <label className="sm:col-span-2 text-xs font-semibold text-slate-300">
                  URL ต้นทาง
                  <input type="url" value={draft.url || ''} onChange={(event) => updateDraft('url', event.target.value)} className="mt-1 w-full rounded-xl border border-white/[0.1] bg-black/30 px-3 py-2.5 text-xs text-white outline-none transition focus:border-cyan-300/60" placeholder="https://shop.tiktok.com/..." />
                </label>
                <label className="text-xs font-semibold text-slate-300">
                  ราคา / โปรโมชั่น
                  <input value={draft.price_note || ''} onChange={(event) => updateDraft('price_note', event.target.value)} maxLength={240} className="mt-1 w-full rounded-xl border border-white/[0.1] bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/60" />
                </label>
                <label className="text-xs font-semibold text-slate-300">
                  รหัสสินค้าสำหรับปักตะกร้า (TikTok Product ID)
                  <input value={draft.tiktok_product_id || ''} onChange={(event) => updateDraft('tiktok_product_id', event.target.value)} maxLength={60} className="mt-1 w-full rounded-xl border border-white/[0.1] bg-black/30 px-3 py-2.5 text-sm text-white font-mono outline-none transition focus:border-cyan-300/60" placeholder="เช่น 1737230577125983588" />
                </label>
                <div className="sm:col-span-2 flex items-end justify-end">
                  <button type="button" onClick={() => onSaveMetadata({
                    name: String(draft.name || '').trim(),
                    url: String(draft.url || '').trim(),
                    tiktok_product_id: String(draft.tiktok_product_id || '').trim() || null,
                    price_note: String(draft.price_note || '').trim(),
                    description: String(draft.description || '').trim(),
                    raw_text: String(draft.raw_text || '').trim(),
                    specs: lines(draft.specs),
                    selling_points: lines(draft.selling_points),
                    pain_points: lines(draft.pain_points),
                  })} disabled={savingMetadata || !String(draft.name || '').trim()} className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2.5 text-xs font-bold text-[#07151d] transition hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-50">
                    {savingMetadata ? 'กำลังบันทึก' : 'บันทึก metadata ที่แก้ไข'}
                  </button>
                </div>
                {[
                  ['description', 'คำอธิบายสินค้า', 5],
                  ['raw_text', 'ข้อความต้นฉบับที่ส่งให้ AI', 6],
                  ['specs', 'สเปกสินค้า — 1 รายการต่อ 1 บรรทัด', 5],
                  ['selling_points', 'จุดขาย — 1 รายการต่อ 1 บรรทัด', 5],
                  ['pain_points', 'Pain points — 1 รายการต่อ 1 บรรทัด', 4],
                ].map(([field, label, rows]) => (
                  <label key={field} className="sm:col-span-2 text-xs font-semibold text-slate-300">
                    {label}
                    <textarea value={draft[field] || ''} onChange={(event) => updateDraft(field, event.target.value)} rows={rows} className="mt-1 w-full resize-y rounded-xl border border-white/[0.1] bg-black/30 px-3 py-2.5 text-xs leading-relaxed text-white outline-none transition focus:border-cyan-300/60" />
                  </label>
                ))}
              </div>
            </Section>
          )}

          {sourcePreview && onApplySource && (
            <section className="rounded-2xl border border-amber-300/25 bg-amber-300/[0.06] overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-300/15 px-4 py-3">
                <div>
                  <h4 className="text-sm font-bold text-white">ตรวจข้อมูลใหม่ก่อนบันทึก</h4>
                  <p className="mt-1 text-[11px] text-amber-100/75">ข้อมูลเดิมจะไม่เปลี่ยนจนกว่าจะกดยืนยัน เลือกเฉพาะฟิลด์ที่ต้องการรับเข้า</p>
                </div>
                <button type="button" onClick={() => setSelectedPreviewFields(Object.fromEntries((sourcePreview.changed_fields || []).map((field) => [field, true])))} className="rounded-lg border border-amber-200/25 px-2.5 py-1.5 text-[11px] font-bold text-amber-100 transition hover:bg-amber-200/10">เลือกทั้งหมดที่เปลี่ยน</button>
              </div>
              <div className="space-y-2 p-4">
                {(sourcePreview.changed_fields || []).map((field) => {
                  const definition = previewFields.find(([key]) => key === field);
                  const label = definition?.[1] || field;
                  return (
                    <div key={field} className="rounded-xl border border-white/[0.08] bg-black/20 p-3">
                      <label className="flex items-center gap-2 text-xs font-bold text-white">
                        <input type="checkbox" checked={Boolean(selectedPreviewFields[field])} onChange={(event) => setSelectedPreviewFields((current) => ({ ...current, [field]: event.target.checked }))} className="h-4 w-4 accent-cyan-300" />
                        {label}
                      </label>
                      {field === 'images' ? (
                        <div className="mt-2 text-[11px] text-slate-300">
                          เดิม {sourcePreview.image_summary?.existing || 0} รูป · ใหม่ {sourcePreview.image_summary?.incoming || 0} รูป · หลังรวมซ้ำ {sourcePreview.image_summary?.merged || 0} รูป
                          <div className="mt-2 grid grid-cols-4 gap-2">
                            {(sourcePreview.incoming?.images || []).slice(0, 8).map((image, index) => {
                              const reference = getImageReference(image);
                              return reference ? <img key={`${reference}-${index}`} src={toMediaUrl(reference)} alt={`รูปใหม่ ${index + 1}`} className="aspect-square w-full rounded-lg object-cover" /> : null;
                            })}
                          </div>
                        </div>
                      ) : (field === 'description' || field === 'raw_text') ? (
                        <label className="mt-2 block">
                          <span className="mb-1 block text-[10px] font-bold text-cyan-300">
                            ใหม่ · แก้ไขได้ก่อนบันทึก
                          </span>
                          <textarea
                            value={previewDraft[field] || ''}
                            onChange={(event) => setPreviewDraft((current) => ({ ...current, [field]: event.target.value }))}
                            rows={field === 'description' ? 6 : 8}
                            className="w-full resize-y rounded-lg border border-cyan-300/20 bg-cyan-300/[0.06] p-2 text-[11px] leading-relaxed text-cyan-50 outline-none transition focus:border-cyan-300/60"
                          />
                        </label>
                      ) : (
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <div className="min-w-0"><div className="mb-1 text-[10px] font-bold text-slate-500">เดิม</div><pre className="max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/25 p-2 text-[11px] leading-relaxed text-slate-400">{previewValue(sourcePreview.current?.[field])}</pre></div>
                          <div className="min-w-0"><div className="mb-1 text-[10px] font-bold text-cyan-300">ใหม่</div><pre className="max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-cyan-300/[0.06] p-2 text-[11px] leading-relaxed text-cyan-50">{previewValue(sourcePreview.incoming?.[field])}</pre></div>
                        </div>
                      )}
                    </div>
                  );
                })}
                {(sourcePreview.changed_fields || []).length === 0 && <p className="rounded-xl bg-black/20 p-3 text-xs text-slate-400">ไม่พบข้อมูลที่ต่างจากเดิม</p>}
                <div className="flex flex-wrap justify-end gap-2 pt-2">
                  <button type="button" onClick={onCancelPreview} className="rounded-xl border border-white/[0.12] px-3 py-2 text-xs font-bold text-slate-300 transition hover:bg-white/[0.06]">ยกเลิก preview</button>
                  <button type="button" onClick={() => {
                    const fields = Object.keys(selectedPreviewFields).filter((field) => selectedPreviewFields[field]);
                    const overrides = Object.fromEntries(
                      ['description', 'raw_text']
                        .filter((field) => fields.includes(field))
                        .map((field) => [field, String(previewDraft[field] || '').trim()])
                    );
                    onApplySource({ url: sourcePreview.url, fields, overrides });
                  }} disabled={refreshingSource || !Object.values(selectedPreviewFields).some(Boolean)} className="rounded-xl bg-amber-300 px-4 py-2 text-xs font-bold text-[#1b1304] transition hover:bg-amber-200 disabled:cursor-wait disabled:opacity-50">{refreshingSource ? 'กำลังบันทึกข้อมูล' : 'ยืนยันและบันทึกข้อมูลที่เลือก'}</button>
                </div>
              </div>
            </section>
          )}
          <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/[0.06] p-4">
            <div className="flex items-start gap-3">
              <Database className="w-5 h-5 text-[#25F4EE] mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <h4 className="text-sm font-bold text-white">{product.name || product.title || 'สินค้า'}</h4>
                <p className="mt-1 text-xs text-cyan-100/75 leading-relaxed">{sourceMethod}</p>
                <p className="mt-2 text-[11px] text-slate-400">
                  เมื่อกดรีสคริปต์ ระบบจะใช้ชื่อ คำอธิบาย ราคาที่บันทึกไว้ ข้อความต้นฉบับ และรูปอ้างอิงชุดนี้เป็น source material ให้ AI
                </p>
                {product.url && onPreviewSource && (
                  <button
                    type="button"
                    onClick={() => onPreviewSource({ url: draft.url || product.url })}
                    disabled={refreshingSource}
                    className="mt-3 inline-flex items-center gap-1.5 rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-3 py-2 text-xs font-bold text-cyan-200 transition hover:bg-cyan-300/20 disabled:cursor-wait disabled:opacity-60"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${refreshingSource ? 'animate-spin' : ''}`} />
                    {refreshingSource ? 'กำลังอ่านหน้าเว็บจริง' : 'ดึงรายละเอียดจาก URL ใหม่'}
                  </button>
                )}
                {images.length > 0 && onPreviewImages && (
                  <button
                    type="button"
                    onClick={onPreviewImages}
                    disabled={refreshingSource}
                    className="mt-3 ml-2 inline-flex items-center gap-1.5 rounded-xl border border-violet-300/30 bg-violet-300/10 px-3 py-2 text-xs font-bold text-violet-200 transition hover:bg-violet-300/20 disabled:cursor-wait disabled:opacity-60"
                  >
                    <ImagePlus className="h-3.5 w-3.5" />
                    {refreshingSource ? 'กำลังอ่านรูปอ้างอิง' : 'อ่านสรรพคุณจากรูป'}
                  </button>
                )}
                {product.source_warning && (
                  <p className="mt-2 text-[11px] text-amber-200/80">หมายเหตุ: {product.source_warning}</p>
                )}
              </div>
            </div>
          </div>

          <Section icon={Globe2} title="แหล่งที่มาและข้อมูลระบุสินค้า" hint="ข้อมูลระดับสินค้า">
            <dl>
              <DataRow label="ชื่อสินค้า" value={product.name || product.title} />
              <DataRow label="รหัสสินค้า" value={product.product_code} />
              <DataRow label="แพลตฟอร์ม" value={product.platform} />
              <DataRow label="หมวดหมู่" value={product.category} />
              <DataRow label="URL ต้นทาง" value={product.url} />
              <DataRow label="ราคา / โปรโมชัน" value={product.price_note} />
              <DataRow label="กลุ่มเป้าหมาย" value={product.target_buyer} />
              <DataRow label="สร้างข้อมูลเมื่อ" value={product.created_at} />
              <DataRow label="แก้ไขล่าสุด" value={product.updated_at} />
            </dl>
          </Section>

          <Section icon={FileText} title="ข้อความที่ดึงมาและข้อมูลสกัด" hint="ส่งต่อเป็นบริบทให้ AI">
            <dl>
              <DataRow label="คำอธิบาย / สรรพคุณ (แก้ไขได้ด้านบน)" value={product.description} multiline />
              <DataRow label="ข้อความต้นฉบับที่ไม่ซ้ำ" value={sourceTextWithoutDuplicate(product.description, product.raw_text)} multiline />
              <DataRow label="สเปก" value={product.specs} multiline />
              <DataRow label="จุดขาย" value={product.selling_points} multiline />
              <DataRow label="Pain points" value={product.pain_points} multiline />
            </dl>
          </Section>

          <Section icon={ImagePlus} title="รูปอ้างอิงสินค้า" hint={`${images.length}/${maxImages} รูป`}>
            <div className="flex items-center justify-between gap-3 pb-3">
              <p className="text-[11px] text-slate-400 leading-relaxed">
                รูปจาก URL ใช้เป็นภาพที่ scraper พบจากหน้าเว็บ ส่วนรูปที่แนบเพิ่มจะถูกเก็บเป็นไฟล์ในเครื่องและส่งให้ Vision ตอนสร้างหรือรีสคริปต์
              </p>
              <label className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold cursor-pointer flex-shrink-0">
                <Upload className="w-3.5 h-3.5" />
                <span>{uploading ? 'กำลังอัปโหลด' : 'เพิ่มรูป'}</span>
                <input
                  ref={imageInputRef}
                  type="file"
                  multiple
                  accept="image/*,.heic,.HEIC,.heif,.HEIF"
                  onChange={onAddImages}
                  disabled={uploading || images.length >= maxImages}
                  className="sr-only"
                />
              </label>
            </div>

            {images.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2">
                {images.map((image, index) => {
                  const reference = getImageReference(image);
                  return (
                    <div key={`${reference}-${index}`} className="group relative overflow-hidden rounded-xl border border-white/[0.1] bg-black/40">
                      <div className="aspect-square">
                        {reference ? (
                          <img src={toMediaUrl(reference)} alt={getImageName(image, index)} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">ไม่มี path</div>
                        )}
                      </div>
                      <div className="p-2 min-w-0">
                        <p className="text-[10px] text-slate-200 truncate" title={getImageName(image, index)}>{getImageName(image, index)}</p>
                        <p className="text-[9px] text-slate-500 truncate" title={imageOrigin(image)}>{imageOrigin(image)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemoveImage(index)}
                        disabled={removingIndex === index}
                        title="เอารูปนี้ออกจากข้อมูลสินค้า"
                        aria-label={`เอารูป ${index + 1} ออกจากข้อมูลสินค้า`}
                        className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-lg bg-black/75 text-rose-300 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-rose-500/80 hover:text-white disabled:cursor-wait disabled:opacity-100"
                      >
                        {removingIndex === index ? <span className="text-[10px]">รอ</span> : <Trash2 className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-white/[0.14] px-4 py-6 text-center text-xs text-slate-500">
                ยังไม่มีรูปอ้างอิง · กด “เพิ่มรูป” เพื่อแนบย้อนหลังได้
              </div>
            )}
          </Section>

          <Section icon={Link2} title="ข้อมูลที่ AI จะได้รับ" hint="สรุปตาม source ที่บันทึกจริง">
            <div className="grid gap-2 sm:grid-cols-2">
              {[
                ['ชื่อสินค้า', product.name || product.title],
                ['คำอธิบาย / raw text', [product.description, sourceTextWithoutDuplicate(product.description, product.raw_text)].filter(Boolean).join('\n')],
                ['ราคา', product.price_note],
                ['สเปกและจุดขาย', [product.specs, product.selling_points, product.pain_points].filter(Boolean).map(displayValue).join('\n')],
                ['รูปอ้างอิง', `${images.length} รูป (${images.map(imageOrigin).join(', ') || 'ไม่มี'})`],
                ['การสร้างสคริปต์', 'Content Matrix หรือรีสคริปต์มุมเดิม โดยอ่าน source ชุดนี้'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border border-white/[0.07] bg-black/20 p-3">
                  <div className="text-[10px] font-bold text-cyan-300 mb-1">{label}</div>
                  <div className="text-xs text-slate-300 whitespace-pre-wrap break-words">{displayValue(value)}</div>
                </div>
              ))}
            </div>
          </Section>

          <details className="rounded-2xl border border-white/[0.08] bg-black/20">
            <summary className="cursor-pointer list-none px-4 py-3 text-xs font-bold text-slate-300 hover:text-white">
              เปิดดู JSON metadata เต็มของ source
            </summary>
            <pre className="max-h-80 overflow-auto border-t border-white/[0.07] p-4 text-[10px] leading-relaxed text-slate-400 whitespace-pre-wrap break-all">
              {JSON.stringify(sourceSnapshot, null, 2)}
            </pre>
          </details>

          <div className="flex items-center justify-end border-t border-white/[0.08] pt-3">
            <button type="button" onClick={onClose} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-slate-200 text-xs font-bold cursor-pointer">
              <X className="w-3.5 h-3.5" />
              ปิดรายละเอียด
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
