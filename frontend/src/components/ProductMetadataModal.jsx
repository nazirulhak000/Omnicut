import React, { useEffect, useMemo, useState } from 'react';
import {
  Database, FileText, ImagePlus, ListChecks, RefreshCw, Sparkles, Trash2, Upload, X
} from 'lucide-react';
import { Modal } from './ui';
import { toMediaUrl } from '../lib/mediaUrl';
import { listFieldFromText, listFieldText, listLineCount } from '../lib/productListFields';

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
  if (Array.isArray(value)) return value.length ? listFieldText(value).split('\n').join(' · ') : 'ไม่มีข้อมูล';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

function DataRow({ label, value }) {
  return (
    <div className="grid grid-cols-[minmax(100px,0.28fr)_minmax(0,0.72fr)] gap-3 py-2 border-b border-white/[0.06] last:border-b-0">
      <dt className="text-[11px] font-semibold text-slate-400">{label}</dt>
      <dd className="text-xs text-slate-200 break-words">{displayValue(value)}</dd>
    </div>
  );
}

function Section({ icon: Icon, title, hint, children }) {
  return (
    <section className="rounded-2xl border border-white/[0.08] bg-[#0D111A] overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/[0.08]">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="w-4 h-4 text-[#25F4EE] flex-shrink-0" aria-hidden="true" />
          <h4 className="text-sm font-bold text-white truncate">{title}</h4>
        </div>
        {hint && <span className="text-[11px] text-slate-400 text-right">{hint}</span>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

const FIELD_INPUT = 'mt-1.5 w-full rounded-xl border border-white/[0.1] bg-black/40 px-3 py-2.5 text-white outline-none transition focus:border-[#25F4EE]';
const FIELD_LABEL = 'block text-xs font-semibold text-slate-300';

// List fields of the form, edited as text with one item per line.
const LIST_FIELDS = [
  ['specs', 'สเปก', 'เช่น ความจุ: 30,000mAh'],
  ['selling_points', 'จุดขาย', 'เช่น ชาร์จไว 22.5W'],
  ['pain_points', 'Pain points', 'เช่น แบตหมดระหว่างวัน'],
];

function formFromProduct(product) {
  return {
    name: product.name || product.title || '',
    url: product.url || '',
    tiktok_product_id: product.tiktok_product_id || '',
    price_note: product.price_note || '',
    description: product.description || '',
    raw_text: product.raw_text || '',
    specs: listFieldText(product.specs),
    selling_points: listFieldText(product.selling_points),
    pain_points: listFieldText(product.pain_points),
  };
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
  const saved = useMemo(() => (product ? formFromProduct(product) : {}), [product]);
  const [draft, setDraft] = useState({});
  const [previewDraft, setPreviewDraft] = useState({});
  const [selectedPreviewFields, setSelectedPreviewFields] = useState({});

  useEffect(() => { setDraft(saved); }, [saved]);

  useEffect(() => {
    const changed = sourcePreview?.changed_fields || [];
    setSelectedPreviewFields(Object.fromEntries(changed.map((field) => [field, true])));
    setPreviewDraft({
      description: sourcePreview?.incoming?.description || '',
      raw_text: sourcePreview?.incoming?.raw_text || '',
    });
  }, [sourcePreview]);

  const updateDraft = (field, value) => setDraft((current) => ({ ...current, [field]: value }));
  const dirty = Object.keys(saved).some((field) => (draft[field] ?? '') !== (saved[field] ?? ''));
  const nameMissing = !String(draft.name || '').trim();
  const canSave = Boolean(onSaveMetadata) && dirty && !savingMetadata && !nameMissing;

  const handleSave = () => {
    if (!canSave) return;
    Promise.resolve(onSaveMetadata({
      name: String(draft.name || '').trim(),
      url: String(draft.url || '').trim(),
      tiktok_product_id: String(draft.tiktok_product_id || '').trim() || null,
      price_note: String(draft.price_note || '').trim(),
      description: String(draft.description || '').trim(),
      raw_text: String(draft.raw_text || '').trim(),
      ...Object.fromEntries(LIST_FIELDS.map(([field]) => [field, listFieldFromText(draft[field], product[field])])),
    })).catch(() => { /* the page already showed why the save failed */ });
  };

  const previewValue = (value) => {
    if (Array.isArray(value)) return value.length ? listFieldText(value) : 'ไม่มีข้อมูล';
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
  const sourceIncomplete = Boolean(product && (product.metadata_source === 'slug_fallback' || product.source_warning));

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="ข้อมูลสินค้าและแหล่งข้อมูล AI"
      subtitle="ข้อมูลชุดนี้คือสิ่งที่ AI อ่านตอนสร้างและรีสคริปต์ แก้แล้วกดบันทึกด้านล่าง"
      maxWidth="max-w-5xl"
    >
      {!product ? null : (
        <div className="space-y-4">
          {/* Where the data came from, and the two ways to read it again. */}
          <div className={`rounded-2xl border p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${sourceIncomplete ? 'border-amber-500/30 bg-amber-500/10' : 'border-white/[0.08] bg-[#0D111A]'}`}>
            <div className="flex items-start gap-2.5 min-w-0">
              <Database className={`w-4 h-4 mt-0.5 flex-shrink-0 ${sourceIncomplete ? 'text-amber-400' : 'text-[#25F4EE]'}`} aria-hidden="true" />
              <div className="min-w-0">
                <p className={`text-xs font-bold ${sourceIncomplete ? 'text-amber-200' : 'text-white'}`}>
                  {sourceIncomplete ? 'ข้อมูลสินค้ายังไม่สมบูรณ์ — ดึงจากหน้าเว็บไม่สำเร็จ หรือติดระบบป้องกันของแพลตฟอร์ม' : sourceMethod}
                </p>
                <p className={`text-[11px] mt-0.5 ${sourceIncomplete ? 'text-amber-200/80' : 'text-slate-400'}`}>
                  {product.source_warning
                    ? `หมายเหตุ: ${product.source_warning}`
                    : sourceIncomplete ? 'ดึงข้อมูลใหม่อีกครั้ง หรือแก้รายละเอียดเองในฟอร์มด้านล่าง' : 'ดึงใหม่ได้ ระบบจะให้ตรวจข้อมูลใหม่ก่อนบันทึกทุกครั้ง'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
              {(draft.url || product.url) && onPreviewSource && (
                <button
                  type="button"
                  onClick={() => onPreviewSource({ url: draft.url || product.url })}
                  disabled={refreshingSource}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold transition disabled:cursor-wait disabled:opacity-60 cursor-pointer ${sourceIncomplete ? 'bg-amber-400 text-slate-950 hover:bg-amber-300' : 'border border-[#25F4EE]/30 bg-[#25F4EE]/10 text-[#25F4EE] hover:bg-[#25F4EE]/20'}`}
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshingSource ? 'animate-spin' : ''}`} />
                  <span>{refreshingSource ? 'กำลังอ่านหน้าเว็บ...' : 'ดึงข้อมูลจาก URL ใหม่'}</span>
                </button>
              )}
              {images.length > 0 && onPreviewImages && (
                <button
                  type="button"
                  onClick={onPreviewImages}
                  disabled={refreshingSource}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-violet-400/30 bg-violet-400/10 px-3 py-2 text-xs font-bold text-violet-300 transition hover:bg-violet-400/20 disabled:cursor-wait disabled:opacity-60 cursor-pointer"
                >
                  <ImagePlus className="h-3.5 w-3.5" />
                  <span>{refreshingSource ? 'กำลังอ่านรูปอ้างอิง' : 'อ่านสรรพคุณจากรูป'}</span>
                </button>
              )}
            </div>
          </div>

          {sourcePreview && onApplySource && (
            <section className="rounded-2xl border border-amber-500/30 bg-[#0D111A] overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.08] px-4 py-3">
                <div>
                  <h4 className="text-sm font-bold text-white">ตรวจข้อมูลใหม่ก่อนบันทึก</h4>
                  <p className="mt-1 text-[11px] text-amber-200/80">ข้อมูลเดิมจะไม่เปลี่ยนจนกว่าจะกดยืนยัน เลือกเฉพาะฟิลด์ที่ต้องการรับเข้า</p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedPreviewFields(Object.fromEntries((sourcePreview.changed_fields || []).map((field) => [field, true])))}
                  className="rounded-lg border border-amber-400/30 px-2.5 py-1.5 text-[11px] font-bold text-amber-200 transition hover:bg-amber-400/10 cursor-pointer"
                >
                  เลือกทั้งหมดที่เปลี่ยน
                </button>
              </div>
              <div className="space-y-2 p-4">
                {(sourcePreview.changed_fields || []).map((field) => {
                  const definition = previewFields.find(([key]) => key === field);
                  const label = definition?.[1] || field;
                  return (
                    <div key={field} className="rounded-xl border border-white/[0.08] bg-black/40 p-3">
                      <label className="flex items-center gap-2 text-xs font-bold text-white cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(selectedPreviewFields[field])}
                          onChange={(event) => setSelectedPreviewFields((current) => ({ ...current, [field]: event.target.checked }))}
                          className="h-4 w-4 accent-[#25F4EE] cursor-pointer"
                        />
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
                          <span className="mb-1 block text-[10px] font-bold text-[#25F4EE]">
                            ใหม่ · แก้ไขได้ก่อนบันทึก
                          </span>
                          <textarea
                            value={previewDraft[field] || ''}
                            onChange={(event) => setPreviewDraft((current) => ({ ...current, [field]: event.target.value }))}
                            rows={field === 'description' ? 6 : 8}
                            className="w-full resize-y rounded-lg border border-[#25F4EE]/30 bg-black/40 p-2 text-[11px] leading-relaxed text-cyan-50 outline-none transition focus:border-[#25F4EE]"
                          />
                        </label>
                      ) : (
                        <div className="mt-2 grid gap-2 sm:grid-cols-2">
                          <div className="min-w-0">
                            <div className="mb-1 text-[10px] font-bold text-slate-400">เดิม</div>
                            <pre className="max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/40 border border-white/[0.06] p-2 text-[11px] leading-relaxed text-slate-400">{previewValue(sourcePreview.current?.[field])}</pre>
                          </div>
                          <div className="min-w-0">
                            <div className="mb-1 text-[10px] font-bold text-[#25F4EE]">ใหม่</div>
                            <pre className="max-h-32 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/40 border border-[#25F4EE]/20 p-2 text-[11px] leading-relaxed text-cyan-50">{previewValue(sourcePreview.incoming?.[field])}</pre>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
                {(sourcePreview.changed_fields || []).length === 0 && <p className="rounded-xl bg-black/40 border border-white/[0.06] p-3 text-xs text-slate-400">ไม่พบข้อมูลที่ต่างจากเดิม</p>}
                <div className="flex flex-wrap justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={onCancelPreview}
                    className="rounded-xl border border-white/[0.08] bg-white/[0.04] hover:bg-white/[0.08] px-3 py-2 text-xs font-bold text-slate-300 transition cursor-pointer"
                  >
                    ยกเลิก preview
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const fields = Object.keys(selectedPreviewFields).filter((field) => selectedPreviewFields[field]);
                      const overrides = Object.fromEntries(
                        ['description', 'raw_text']
                          .filter((field) => fields.includes(field))
                          .map((field) => [field, String(previewDraft[field] || '').trim()])
                      );
                      onApplySource({ url: sourcePreview.url, fields, overrides });
                    }}
                    disabled={refreshingSource || !Object.values(selectedPreviewFields).some(Boolean)}
                    className="rounded-xl bg-amber-400 hover:bg-amber-300 px-4 py-2 text-xs font-bold text-slate-950 transition disabled:cursor-wait disabled:opacity-50 cursor-pointer"
                  >
                    {refreshingSource ? 'กำลังบันทึกข้อมูล' : 'ยืนยันและบันทึกข้อมูลที่เลือก'}
                  </button>
                </div>
              </div>
            </section>
          )}

          <Section icon={FileText} title="ข้อมูลหลัก">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={`sm:col-span-2 ${FIELD_LABEL}`}>
                ชื่อสินค้า / หัวข้อสั้น
                <input
                  value={draft.name || ''}
                  onChange={(event) => updateDraft('name', event.target.value)}
                  maxLength={180}
                  aria-invalid={nameMissing}
                  className={`${FIELD_INPUT} text-sm`}
                  placeholder="เช่น GoChek GC-ULTRA S24"
                />
                {nameMissing && <span className="mt-1 block text-[11px] font-medium text-amber-300">ต้องมีชื่อสินค้าก่อนบันทึก</span>}
              </label>
              <label className={`sm:col-span-2 ${FIELD_LABEL}`}>
                URL ต้นทาง
                <input
                  type="url"
                  value={draft.url || ''}
                  onChange={(event) => updateDraft('url', event.target.value)}
                  className={`${FIELD_INPUT} text-xs`}
                  placeholder="https://shop.tiktok.com/..."
                />
              </label>
              <label className={FIELD_LABEL}>
                ราคา / โปรโมชั่น
                <input
                  value={draft.price_note || ''}
                  onChange={(event) => updateDraft('price_note', event.target.value)}
                  maxLength={240}
                  className={`${FIELD_INPUT} text-sm`}
                />
              </label>
              <label className={FIELD_LABEL}>
                รหัสสินค้าสำหรับปักตะกร้า (TikTok Product ID)
                <input
                  value={draft.tiktok_product_id || ''}
                  onChange={(event) => updateDraft('tiktok_product_id', event.target.value)}
                  maxLength={60}
                  inputMode="numeric"
                  className={`${FIELD_INPUT} text-sm font-mono`}
                  placeholder="เช่น 1737230577125983588"
                />
              </label>
            </div>
          </Section>

          <Section icon={Sparkles} title="เนื้อหาที่ส่งให้ AI" hint="ใช้ตอนสร้างและรีสคริปต์">
            <div className="grid gap-3 lg:grid-cols-2">
              {[
                ['description', 'คำอธิบายสินค้า'],
                ['raw_text', 'ข้อความต้นฉบับ'],
              ].map(([field, label]) => (
                <label key={field} className={FIELD_LABEL}>
                  {label}
                  <textarea
                    value={draft[field] || ''}
                    onChange={(event) => updateDraft(field, event.target.value)}
                    rows={9}
                    className={`${FIELD_INPUT} resize-y text-xs leading-relaxed`}
                  />
                </label>
              ))}
            </div>
          </Section>

          <Section icon={ListChecks} title="สรุปสำหรับสคริปต์" hint="1 รายการต่อ 1 บรรทัด">
            <div className="grid gap-3 md:grid-cols-3">
              {LIST_FIELDS.map(([field, label, placeholder]) => (
                <label key={field} className={FIELD_LABEL}>
                  <span className="flex items-center justify-between gap-2">
                    <span>{label}</span>
                    <span className="font-mono tabular-nums text-[11px] font-medium text-slate-400">
                      {listLineCount(draft[field])} รายการ
                    </span>
                  </span>
                  <textarea
                    value={draft[field] || ''}
                    onChange={(event) => updateDraft(field, event.target.value)}
                    rows={8}
                    placeholder={placeholder}
                    className={`${FIELD_INPUT} resize-y text-xs leading-relaxed placeholder-slate-500`}
                  />
                </label>
              ))}
            </div>
          </Section>

          <Section icon={ImagePlus} title="รูปอ้างอิงสินค้า" hint={`${images.length}/${maxImages} รูป`}>
            <div className="flex items-center justify-between gap-3 pb-3">
              <p className="text-[11px] text-slate-400 leading-relaxed">
                รูปจาก URL ใช้เป็นภาพที่ scraper พบจากหน้าเว็บ ส่วนรูปที่แนบเพิ่มจะถูกเก็บเป็นไฟล์ในเครื่องและส่งให้ Vision ตอนสร้างหรือรีสคริปต์
              </p>
              <label className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#25F4EE]/10 hover:bg-[#25F4EE]/20 border border-[#25F4EE]/30 text-[#25F4EE] text-xs font-bold cursor-pointer flex-shrink-0 transition-colors">
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
                    <div key={`${reference}-${index}`} className="group relative overflow-hidden rounded-xl border border-white/[0.08] bg-black/40">
                      <div className="aspect-square">
                        {reference ? (
                          <img loading="lazy" decoding="async" src={toMediaUrl(reference)} alt={getImageName(image, index)} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-slate-500 text-xs">ไม่มี path</div>
                        )}
                      </div>
                      <div className="p-2 min-w-0">
                        <p className="text-[10px] text-slate-200 truncate" title={getImageName(image, index)}>{getImageName(image, index)}</p>
                        <p className="text-[10px] text-slate-400 truncate" title={imageOrigin(image)}>{imageOrigin(image)}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemoveImage(index)}
                        disabled={removingIndex === index}
                        title="เอารูปนี้ออกจากข้อมูลสินค้า"
                        aria-label={`เอารูป ${index + 1} ออกจากข้อมูลสินค้า`}
                        className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-lg bg-black/75 text-rose-300 opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:bg-rose-500/80 hover:text-white disabled:cursor-wait disabled:opacity-100 cursor-pointer"
                      >
                        {removingIndex === index ? <span className="text-[10px]">รอ</span> : <Trash2 className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-white/[0.14] px-4 py-6 text-center text-xs text-slate-400">
                ยังไม่มีรูปอ้างอิง · กด “เพิ่มรูป” เพื่อแนบย้อนหลังได้
              </div>
            )}
          </Section>

          <details className="rounded-2xl border border-white/[0.08] bg-[#0D111A]">
            <summary className="cursor-pointer px-4 py-3 text-xs font-bold text-slate-300 hover:text-white">
              ข้อมูลระบบและ JSON ของ source
            </summary>
            <div className="border-t border-white/[0.08] px-4 py-2">
              <dl>
                <DataRow label="รหัสสินค้า" value={product.product_code} />
                <DataRow label="แพลตฟอร์ม" value={product.platform} />
                <DataRow label="หมวดหมู่" value={product.category} />
                <DataRow label="กลุ่มเป้าหมาย" value={product.target_buyer} />
                <DataRow label="สร้างข้อมูลเมื่อ" value={product.created_at} />
                <DataRow label="แก้ไขล่าสุด" value={product.updated_at} />
              </dl>
            </div>
            <pre className="max-h-80 overflow-auto border-t border-white/[0.08] p-4 text-[10px] leading-relaxed text-slate-400 whitespace-pre-wrap break-all">
              {JSON.stringify(sourceSnapshot, null, 2)}
            </pre>
          </details>

          {/* Save stays in reach at the bottom of the scrolling body; the
              negative offset cancels the body's padding so nothing scrolls under it. */}
          <div className="sticky -bottom-4 sm:-bottom-6 z-10 -mx-4 sm:-mx-6 -mb-4 sm:-mb-6 px-4 sm:px-6 py-3 border-t border-white/[0.08] bg-[#0A0D14]/95 backdrop-blur-xl flex items-center justify-between gap-3">
            <p role="status" className={`text-xs font-medium ${dirty ? 'text-amber-300' : 'text-slate-400'}`}>
              {savingMetadata ? 'กำลังบันทึก...' : dirty ? 'มีการแก้ไขที่ยังไม่บันทึก' : 'ข้อมูลตรงกับที่บันทึกไว้'}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-slate-200 text-xs font-bold cursor-pointer transition-colors border border-white/[0.08]"
              >
                <X className="w-3.5 h-3.5" />
                ปิด
              </button>
              {onSaveMetadata && (
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!canSave}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#25F4EE] hover:bg-[#20ded8] px-4 py-2 text-xs font-bold text-slate-950 transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {savingMetadata ? 'กำลังบันทึก' : 'บันทึกการแก้ไข'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
