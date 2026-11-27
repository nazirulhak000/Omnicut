# Master Execution Plan: OmniCut Desktop App (Tauri v2) + Antigravity Profiles v4.2 UI + Mobile HTTPS Bridge

> วันที่: 2026-11-27 · ดำเนินการโดย: Antigravity (Gemini 4 Neon High) + Swarm Workers

## เป้าหมาย
1. หุ้ม OmniCut Pro Studio เป็น Desktop App (`.exe` ด้วย **Tauri v2 + WebView2**) โดยเก็บ FastAPI Python Backend, HyperFrames, และ Editor/FFmpeg Preview=Render Parity ไว้ 100%
2. ปรับโฉม UI จาก Glassmorphism ฟุ้งๆ เป็น **Matte-Dark Utility** สไตล์ **`Antigravity Profiles v4.2`** (`#0C0D10` / `#101114` / `#14161A`, ขอบ `1px`, ปุ่มขาวทึบ `#F4F4F5`, Telemetry + StatusBar)
3. คงและยกระดับการสั่งงาน/ถ่ายคลิปผ่านมือถือด้วย **Two-Tier Mobile HTTPS Bridge** (`Tailscale Serve` + `LAN HTTPS :8443` ในโปรเซส FastAPI เดียวกัน)

## เฟสการดำเนินงาน
- **Phase 0 + 3 (`feat/desktop-backend-mobile-bridge`)**: Backend Production Hardening (Font auth exemption, MIME/Cache-Control, SW Tauri guard, `tauri.localhost` local check) + `scripts/tls_cert_manager.py` (`cryptography`) + `scripts/mobile_bridge.py` / `scripts/api_mobile_bridge.py` (in-process `:8443` + Tailscale detection + local-only password endpoints) + Header Popover & StatusBar integration
- **Phase 1 (`feat/ui-antigravity-matte`)**:
  - Stage A: Token-layer swap in `frontend/index.html`, `frontend/src/index.css`, `frontend/src/lib/themeManager.js`
  - Stage B: Shell chrome (`Sidebar.jsx`, `Topbar.jsx`, `EditorChannelSelector.jsx`, `ActivityCenter.jsx`, `StatusBar.jsx`, `ui/*`) + co-updated contract tests
  - Stage C: Safe Editor chrome reskin (`EditorHeader`, `EditorShell` outer/splitters, `Toolbar`, `Timeline` outer/ruler/playhead, `Inspector` chrome, `SequencePlayer` bezel/controls ONLY — preserving all DO-NOT-TOUCH parity files & math)
- **Phase 2 (`feat/desktop-tauri-shell`)**: Toolchain gate (VS 2022 Build Tools C++ & Windows SDK + `@tauri-apps/cli@^2`) + `src-tauri/` (Win32 Job Object orphan-proof cleanup, FastAPI sidecar health gate, loopback-only `X-API-Key` streaming proxy, `"dragDropEnabled": false`, `tauri-plugin-opener` for `:3002`, thin single-PC `.exe` build)
- **Phase 4**: Full regression gates, Jev pre-commit check, cleanup 100%, merge to `main`, close round into `HISTORY.md`.

## Re-plan / Escalation Triggers
- VS 2022 Build Tools unattended install blocked by UAC/admin -> complete & merge Phase 1 + Phase 0/3, then hand back for toolchain decision (`cargo-xwin` or Electron fallback).
- Any Jev gating `choice`/`score` confidence `< 0.80` or `null` -> stop and ask user.
- Any Preview=Render parity failure or `motionPressContract.test.js` structural conflict -> never relax assertions; hand back.
