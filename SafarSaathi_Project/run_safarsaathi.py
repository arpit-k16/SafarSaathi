"""SafarSaathi one-click launcher (Windows/Linux). Run: python run_safarsaathi.py"""
import hashlib, os, subprocess, sys, threading, time, urllib.request, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv-win" if os.name == "nt" else ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQ = ROOT / "requirements.txt"
MARK = VENV / ".req-hash"
LOG = ROOT / "logs" / "launcher.log"
URL = "http://localhost:8000"

def step(msg): print(f"\n>> {msg}", flush=True)

def stop_old_server():
    """If an older SafarSaathi server is still on port 8000, stop it so new code loads."""
    try:
        import json as _json
        info = _json.loads(urllib.request.urlopen(URL + "/api/health", timeout=2).read())
    except Exception:
        return
    if info.get("service") != "SafarSaathi" or os.name != "nt":
        return
    out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True).stdout
    pids = {line.split()[-1] for line in out.splitlines() if ":8000 " in line and "LISTENING" in line}
    for pid in pids:
        step(f"Stopping the previous SafarSaathi server (PID {pid}) ...")
        subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    time.sleep(2)


def main():
    print("=" * 45 + "\n  SafarSaathi AI Tourism Platform\n" + "=" * 45)
    print(f"Project: {ROOT}\nPython : {sys.version.split()[0]}")
    if not PY.exists():
        step(f"Creating virtual environment {VENV.name} ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    h = hashlib.sha256(REQ.read_bytes()).hexdigest()
    if not MARK.exists() or MARK.read_text().strip() != h:
        step("Installing Python packages (first run takes a few minutes) ...")
        subprocess.check_call([str(PY), "-m", "pip", "install", "--upgrade", "pip", "-q"])
        subprocess.check_call([str(PY), "-m", "pip", "install", "-r", str(REQ), "--disable-pip-version-check"])
        MARK.write_text(h)
    else:
        step("Packages already installed.")
    if not (ROOT / "web" / "dist" / "index.html").exists():
        print("WARNING: web/dist missing - UI won't load (API still works).")
    stop_old_server()
    step("Starting server - loading ML models (~25s) ...")
    LOG.parent.mkdir(exist_ok=True)
    try:
        logf = open(LOG, "w", encoding="utf-8")
    except OSError:  # an older launcher still holds the log open
        logf = open(LOG.with_name(f"launcher-{int(time.time())}.log"), "w", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUNBUFFERED="1")
    proc = subprocess.Popen([str(PY), "-m", "uvicorn", "safarsaathi_ml.asgi:app",
                             "--host", "127.0.0.1", "--port", "8000"],
                            cwd=ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    def pump():
        for line in proc.stdout:
            print(line, end="", flush=True)
            try:
                logf.write(line); logf.flush()
            except OSError:
                pass
    threading.Thread(target=pump, daemon=True).start()
    for _ in range(120):
        if proc.poll() is not None:
            print(f"\nERROR: server exited with code {proc.returncode}. See {logf.name}")
            return 1
        try:
            urllib.request.urlopen(URL + "/api/health", timeout=2); break
        except Exception:
            time.sleep(1)
    else:
        print("\nServer did not answer within 2 minutes. See", LOG); proc.terminate(); return 1
    print(f"\n{'=' * 45}\n  READY:  {URL}\n  Close this window to stop the server.\n{'=' * 45}\n", flush=True)
    webbrowser.open(URL)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    return proc.returncode or 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: command failed: {e}"); sys.exit(1)
