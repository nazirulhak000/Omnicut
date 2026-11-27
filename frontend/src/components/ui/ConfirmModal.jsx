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
      iconBg: 'bg-[#271417] text-[#F87171] border-[#52232A]',
      btnVariant: 'danger'
    },
    warning: {
      icon: AlertTriangle,
      iconBg: 'bg-[#241D11] text-[#FBBF24] border-[#4D3B19]',
      btnVariant: 'primary'
    },
    info: {
      icon: Info,
      iconBg: 'bg-[#131E33] text-[#60A5FA] border-[#233B66]',
      btnVariant: 'primary'
    }
  }[variant] || iconConfig.danger;

  const IconComponent = iconConfig.icon;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="max-w-md"
      ariaLabel={typeof title === 'string' ? title : 'ยืนยันการดำเนินการ'}
      showCloseButton={!loading}
    >
      <div className="space-y-4 pt-1">
        {/* Header Icon + Title */}
        <div className="flex items-start gap-3.5">
          <div className={`w-11 h-11 rounded-xl flex items-center justify-center border flex-shrink-0 ${iconConfig.iconBg}`}>
            <IconComponent className="w-5 h-5 stroke-[2.2]" />
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="text-base sm:text-lg font-bold text-[#F4F4F5] leading-snug">
              {title}
            </h3>
            {description && (
              <p className="text-xs sm:text-sm text-[#D4D4D8] mt-1 leading-relaxed whitespace-pre-line">
                {description}
              </p>
            )}
          </div>
        </div>

        {/* Item Name Highlight Badge */}
        {itemName && (
          <div className="p-2.5 sm:p-3 rounded-lg bg-[#1B1D22] border border-[#23262D] flex items-center gap-2">
            <span className="text-xs text-[#8E929B] flex-shrink-0">เป้าหมาย:</span>
            <span className="text-xs sm:text-sm font-bold text-[#F4F4F5] font-mono truncate">
              {itemName}
            </span>
          </div>
        )}

        {/* Danger Warning Note */}
        {dangerNote && (
          <div className="p-2.5 rounded-lg bg-[#271417] border border-[#52232A] text-[#F87171] text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-[#F87171]" />
            <span className="leading-snug">{dangerNote}</span>
          </div>
        )}

        {/* Footer Buttons (Fixed Action Area) */}
        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-[#1E2026]">
          {/* Initial focus lands on the safe action, never on the destructive one. */}
          <Button
            variant="secondary"
            onClick={onClose}
            disabled={loading}
            autoFocus
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
