import React from 'react';
import HookVariationModal from './HookVariationModal';

/**
 * HookHeaderModal - Consolidated with HookVariationModal into the unified Hook & Header Studio.
 * Preserves backwards compatibility with any existing imports while providing full tabbed studio access.
 */
export default function HookHeaderModal({
  isOpen,
  onClose,
  product,
  angles = [],
  currentAngleIndex = 0,
  onSaveHookHeader,
  showToast,
}) {
  const currentAngle = angles[currentAngleIndex] || {};

  return (
    <HookVariationModal
      isOpen={isOpen}
      onClose={onClose}
      product={product}
      angle={currentAngle}
      angles={angles}
      currentAngleIndex={currentAngleIndex}
      onSaveHookHeader={onSaveHookHeader}
      initialTab="header"
      showToast={showToast}
    />
  );
}
