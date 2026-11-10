"""Open Bolda Khata on your phone: starts the app (if needed) and a free Cloudflare quick tunnel,
then prints the https link and a QR code to scan.

    .venv/bin/python scripts/phone.py

Press Ctrl+C to close the link. The link changes every time you run this. The app must have a PIN
(APP_PIN in .env), because anyone who gets the link reaches the login screen.
"""
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import auth  # noqa: E402  (loads .env)

PORT = 8000


def port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    if not auth.enabled():
        sys.exit("Refusing to open a public link without a PIN. Add APP_PIN=<digits> to .env first.")
    procs = []
    if not port_open(PORT):
        print("Starting the app on port", PORT, "...")
        env = {**os.environ, "HF_HUB_DISABLE_XET": "1"}
        procs.append(subprocess.Popen([str(ROOT / ".venv/bin/uvicorn"), "app.main:app", "--port", str(PORT)],
                                      cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for _ in range(120):
            if port_open(PORT):
                break
            time.sleep(0.5)
    print("Opening a secure link (Cloudflare quick tunnel) ...")
    tunnel = subprocess.Popen(["cloudflared", "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORT}"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    procs.append(tunnel)
    url = None
    deadline = time.time() + 60
    for line in tunnel.stdout:
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m:
            url = m.group(0)
            break
        if time.time() > deadline:
            break
    if not url:
        for p in procs:
            p.terminate()
        sys.exit("Could not open the tunnel. Check your internet connection and try again.")

    import qrcode
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make()
    print("\nScan this with your phone camera:\n")
    qr.print_ascii(invert=True)
    out = ROOT / "data" / "phone_qr.png"
    qr.make_image().save(out)
    print(f"\n  {url}\n")
    print("  1. Open the link on your phone and enter the PIN (APP_PIN in .env).")
    print("  2. Allow the microphone when asked.")
    print("  3. Android Chrome: menu ⋮ → Install app.  iPhone Safari: Share → Add to Home Screen.")
    print(f"  QR code also saved to {out}")
    print("\nPress Ctrl+C to close the link.\n")

    def stop(*_):
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    for _ in tunnel.stdout:   # keep the tunnel's output drained while it runs
        pass
    stop()


if __name__ == "__main__":
    main()
