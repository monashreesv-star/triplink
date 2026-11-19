import os
import sys
import time
import socket
import subprocess
import urllib.request

APP_URL = "http://127.0.0.1:8000"
HEALTH_URL = "http://127.0.0.1:8000/api/health"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

def is_server_running(timeout=0.8):
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "TripLinkApp/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status == 200
    except Exception:
        return False

def find_browser():
    candidates = [
        # Microsoft Edge (Standard on Windows 10/11)
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None

def start_server():
    print("Initializing TripLink Core Service on http://127.0.0.1:8000 ...")
    run_py = os.path.join(BASE_DIR, "run.py")
    python_exe = sys.executable

    creationflags = 0
    if sys.platform == "win32":
        # Run detached in background
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [python_exe, run_py],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )
    return proc

def check_dependencies():
    missing = []
    for pkg in ["starlette", "uvicorn", "sqlite3"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("❌ Error: Missing required Python dependencies:", ", ".join(missing))
        print("Please install them using: pip install " + " ".join(missing))
        return False
    return True

def main():
    print("=" * 60)
    print("        TRIPLINK FOR TBO — DESKTOP APPLICATION")
    print("=" * 60)

    if not check_dependencies():
        input("\nPress ENTER to exit...")
        sys.exit(1)

    if not is_server_running():
        start_server()
        print("Waiting for TripLink backend to be ready...")
        ready = False
        for attempt in range(25):
            time.sleep(0.4)
            if is_server_running():
                ready = True
                break
        if ready:
            print("Backend service online!")
        else:
            print("Warning: Backend is still starting up, proceeding with window launch...")
    else:
        print("Backend service already running.")

    browser_exe = find_browser()
    if browser_exe:
        print(f"Launching standalone app window via {os.path.basename(browser_exe)}...")
        # Chromium --app mode: borderless, dedicated window, native taskbar icon
        subprocess.Popen([
            browser_exe,
            f"--app={APP_URL}",
            "--window-size=1440,900"
        ])
    else:
        print("Launching default browser...")
        import webbrowser
        webbrowser.open(APP_URL)

    print()
    print("TripLink Application is now running on your screen.")
    print("=" * 60)

if __name__ == "__main__":
    main()
