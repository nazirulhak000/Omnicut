import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#080B11] text-slate-100 flex items-center justify-center p-6 select-none font-sans">
          <div className="max-w-lg w-full p-8 rounded-3xl glass-panel border border-rose-500/30 text-center space-y-5 shadow-2xl animate-fadeIn">
            <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto shadow-lg shadow-rose-500/10">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-bold text-white">
                เกิดข้อผิดพลาดที่ไม่คาดคิดในระบบ
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                ระบบตรวจพบข้อผิดพลาดระหว่างการแสดงผลหน้าจอ ได้ทำการกักข้อผิดพลาดไว้เพื่อป้องกันข้อมูลสูญหาย
              </p>
            </div>

            {this.state.error && (
              <div className="text-left p-3.5 rounded-xl bg-black/50 border border-white/[0.08] max-h-36 overflow-y-auto no-scrollbar font-mono text-sm text-rose-300">
                {this.state.error.toString()}
              </div>
            )}

            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="flex-1 py-3 px-4 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/[0.08] text-white text-xs font-bold transition-all cursor-pointer"
              >
                ลองกู้คืนหน้าจอเดิม
              </button>
              <button
                onClick={this.handleReload}
                className="flex-1 py-3 px-4 rounded-xl bg-gradient-to-r from-[#FE2C55] to-[#25F4EE] hover:opacity-90 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-[#FE2C55]/20 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>รีเฟรชหน้าเว็บ</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
