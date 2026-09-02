import React from 'react';
import { AlertTriangle, Trash2, Info, AlertCircle } from 'lucide-react';
import { Modal } from './Modal';
import { Button } from './Button';

export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'ยืนยันการดำเนินการ',
  description = 'คุณแน่ใจหรือไม่ว่าต้องการดำเนินการนี้?',
  itemName = null,
  dangerNote = 'การกระทำนี้ไม่สามารถย้อนกลับได้',
  confirmText = 'ยืนยัน',
  cancelText = 'ยกเลิก',
  loading = false,
  variant = 'danger' // 'danger' | 'warning' | 'info'
}) {
  const iconConfig = {
    danger: {
      icon: Trash2,
      iconBg: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
      btnVariant: 'danger',
      glow: 'shadow-rose-500/20'
    },
    warning: {
      icon: AlertTriangle,
      iconBg: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
      btnVariant: 'primary',
      glow: 'shadow-amber-500/20'
    },
    info: {
      icon: Info,
      iconBg: 'bg-[#25F4EE]/15 text-[#25F4EE] border-[#25F4EE]/30',
      btnVariant: 'primary',
      glow: 'shadow-[#25F4EE]/20'
    }
  }[variant] || iconConfig.danger;

  const IconComponent = iconConfig.icon;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="max-w-md"
      showCloseButton={!loading}
    >
      <div className="space-y-4 pt-1">
        {/* Header Icon + Title */}
        <div className="flex items-start gap-3.5">
          <div className={`w-11 h-11 rounded-2xl flex items-center justify-center border flex-shrink-0 shadow-lg ${iconConfig.iconBg} ${iconConfig.glow}`}>
            <IconComponent className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-base sm:text-lg font-bold text-white font-kanit leading-snug">
              {title}
            </h3>
            {description && (
              <p className="text-xs sm:text-sm text-slate-300 mt-1 leading-relaxed">
                {description}
              </p>
            )}
          </div>
        </div>

        {/* Item Name Highlight Badge */}
        {itemName && (
          <div className="p-2.5 sm:p-3 rounded-xl bg-black/40 border border-white/[0.08] flex items-center gap-2">
            <span className="text-xs text-slate-400 flex-shrink-0">เป้าหมาย:</span>
            <span className="text-xs sm:text-sm font-bold text-white font-mono truncate">
              {itemName}
            </span>
          </div>
        )}

        {/* Danger Warning Note */}
        {dangerNote && (
          <div className="p-2.5 rounded-xl bg-rose-500/[0.08] border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
            <span className="leading-snug">{dangerNote}</span>
          </div>
        )}

        {/* Footer Buttons (Fixed Action Area) */}
        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/[0.08]">
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            variant={iconConfig.btnVariant}
            onClick={onConfirm}
            loading={loading}
            icon={variant === 'danger' ? Trash2 : null}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default ConfirmModal;
