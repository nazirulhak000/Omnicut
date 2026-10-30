"""
OmniCut Pro Studio - PC Local Runner with Mobile Studio Wi-Fi Bridge
Runs FastAPI server with NVIDIA GPU support, Ultra-Lite API, and prints
a scannable QR Code and mobile link for instant phone connection.
"""
import os
import sys
import socket
from pathlib import Path

# Configure UTF-8 for console output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    BASE_DIR = Path(__file__).resolve().parent.parent
    os.chdir(BASE_DIR)
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    lan_ip = get_lan_ip()
    port = int(os.environ.get("PORT", "8000"))
    local_url = f"http://localhost:{port}"
    mobile_url = f"http://{lan_ip}:{port}"

    # Default password for LAN mobile authentication if not configured
    if not os.environ.get("OMNICUT_APP_PASSWORD"):
        os.environ["OMNICUT_APP_PASSWORD"] = "12345678"

    password = os.environ["OMNICUT_APP_PASSWORD"]

    print("=" * 64)
    print("🚀 OmniCut Pro Studio — PC Master Engine & Mobile Studio")
    print("=" * 64)
    print(f"🖥️  เข้าใช้งานบนคอมพิวเตอร์:  {local_url}")
    print(f"📱  เข้าใช้งานบนมือถือ (Wi-Fi): {mobile_url}")
    print(f"🔑  รหัสผ่านสำหรับมือถือ:       {password}")
    print("⚡  โหมด Ultra-Lite:          เปิดใช้งาน (ขนาด <40KB โหลดไว 0ms)")
    print("-" * 64)

    # Print ASCII QR Code for phone camera scanning
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(mobile_url)
        print("📲 สแกน QR Code นี้ด้วยกล้องมือถือ เพื่อเปิดสตูดิโอทันที:")
        qr.print_ascii(invert=True)
    except Exception:
        pass

    print("-" * 64)
    print("💡 เคล็ดลับ: ส่งคลิปเข้ามือถือผ่าน Wi-Fi ในบ้าน ไม่เสียโควตาเน็ตบ้าน 100%")
    print("=" * 64 + "\n")

    import uvicorn
    uvicorn.run("scripts.api_server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
