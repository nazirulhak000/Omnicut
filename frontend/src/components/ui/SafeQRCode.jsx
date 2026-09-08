import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { QrCode } from 'lucide-react';

class QRErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.error('SafeQRCode: QRCodeSVG failed to render', error);
  }

  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

// QRCodeSVG throws ("RangeError: Data too long") once `value` exceeds the
// QR format's payload ceiling for the given error-correction `level` --
// e.g. a QuickPost URL carrying an unexpectedly long hook_title/product
// name. That throw used to escape all the way to App.jsx's page-wide
// ErrorBoundary, blanking the entire Export Gallery / Content Tracker page
// behind a generic error screen for what is really just one QR code on one
// video. Catching it here keeps the failure contained to that one QR slot.
export function SafeQRCode({ value, size = 150, level = 'M' }) {
  return (
    <QRErrorBoundary
      fallback={
        <div
          className="flex flex-col items-center justify-center gap-1.5 text-slate-500 bg-slate-100 rounded-lg"
          style={{ width: size, height: size }}
        >
          <QrCode className="w-1/3 h-1/3" />
          <span className="text-[10px] text-center px-2 leading-tight">สร้าง QR ไม่ได้ (ข้อมูลยาวเกินไป)</span>
        </div>
      }
    >
      <QRCodeSVG value={value} size={size} level={level} />
    </QRErrorBoundary>
  );
}
