#!/usr/bin/env python3
"""
AI 개발환경 퀘스트 — 환경 검증 서버
사용법: 이 파일(또는 verify_server.exe)을 vscode-lecture.html과 같은 폴더에 두고 실행
"""
import json
import subprocess
import sys
import os
import webbrowser
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── stdout UTF-8 (Windows 콘솔 깨짐 방지) ────────────────────
try:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 3001
IS_WIN = sys.platform == "win32"

# ── exe 실행 위치 찾기 ────────────────────────────────────────
def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# ── 시스템 명령 실행 ─────────────────────────────────────────
def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

CMDS = {
    "vscode":     "code --version",
    "python":     "python --version" if IS_WIN else "python3 --version || python --version",
    "node":       "node -v",
    "npm":        "npm -v",
    "git":        "git --version",
    "git_config": "git config --global user.name",
    "claude":     "claude --version",
}

def check_one(key):
    if key not in CMDS:
        return {"ok": False, "error": "unknown check"}
    ok, out = run(CMDS[key])
    ver = out.split("\n")[0].strip() if ok else ""
    return {"ok": ok, "name": key, "version": ver, "error": "" if ok else out}

def check_all():
    return {k: check_one(k) for k in CMDS}

# ── VS Code 확장 검증 ─────────────────────────────────────────
# publisher.name 형식의 확장 ID 목록
EXT_S2 = {"korean": "ms-ceintl.vscode-language-pack-ko"}
EXT_S3 = {
    "prettier":  "esbenp.prettier-vscode",
    "icons":     "pkief.material-icon-theme",
    "liveserver":"ritwickdey.liveserver",
    "gitlens":   "eamodio.gitlens",
}

def check_ext(required: dict):
    """required = {name: "publisher.ext-id"}"""
    ok, out = run("code --list-extensions")
    if not ok:
        return {"ok": False, "error": "code 명령 실패 — PATH에 code가 없거나 VS Code가 설치되지 않음"}
    installed = {line.strip().lower() for line in out.splitlines() if line.strip()}
    results = {}
    all_ok = True
    for name, ext_id in required.items():
        found = ext_id.lower() in installed
        results[name] = {"id": ext_id, "ok": found}
        if not found:
            all_ok = False
    return {"ok": all_ok, "extensions": results}

# ── VS Code 사용자 설정 검증 ──────────────────────────────────
def _strip_jsonc(text):
    """Remove // line-comments from JSONC, skipping // inside strings."""
    out, i, in_str = [], 0, False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\" and i + 1 < len(text):
                out.append(c); out.append(text[i+1]); i += 2; continue
            if c == '"':
                in_str = False
            out.append(c)
        else:
            if c == '"':
                in_str = True; out.append(c)
            elif c == "/" and i + 1 < len(text) and text[i+1] == "/":
                while i < len(text) and text[i] != "\n":
                    i += 1
                continue
            else:
                out.append(c)
        i += 1
    return "".join(out)

def check_vssettings():
    import pathlib
    if IS_WIN:
        base = pathlib.Path(os.environ.get("APPDATA", ""))
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    else:
        base = pathlib.Path.home() / ".config"
    path = base / "Code" / "User" / "settings.json"

    if not path.exists():
        return {"ok": False, "error": f"settings.json 없음: {path}"}
    try:
        content = _strip_jsonc(path.read_text(encoding="utf-8"))
        settings = json.loads(content)
        fmt  = bool(settings.get("editor.formatOnSave", False))
        auto = settings.get("files.autoSave", "off")
        ok = fmt or auto != "off"
        return {"ok": ok, "formatOnSave": fmt, "autoSave": auto,
                "error": "" if ok else "formatOnSave 또는 autoSave 설정이 필요합니다"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── HTTP Handler ─────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.cors()
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, content: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        # ── 강의 HTML 서빙 ────────────────────────────────────
        if path in ("/", "/vscode-lecture.html"):
            html_path = os.path.join(base_dir(), "vscode-lecture.html")
            if os.path.exists(html_path):
                with open(html_path, "rb") as f:
                    self.send_html(f.read())
            else:
                self.send_json({"error": "vscode-lecture.html not found in same folder"}, 404)
            return

        # ── API ───────────────────────────────────────────────
        if path == "/api/ping":
            self.send_json({"ok": True})
        elif path == "/api/check/all":
            self.send_json(check_all())
        elif path == "/api/check/korean":
            self.send_json(check_ext(EXT_S2))
        elif path == "/api/check/extensions":
            self.send_json(check_ext(EXT_S3))
        elif path == "/api/check/vssettings":
            self.send_json(check_vssettings())
        elif path.startswith("/api/check/"):
            key = path[len("/api/check/"):]
            self.send_json(check_one(key))
        else:
            self.send_json({"ok": False, "error": "not found"}, 404)


# ── 포트 사용 중인지 확인 ─────────────────────────────────────
def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


if __name__ == "__main__":
    if not port_free(PORT):
        print(f"[ERROR] Port {PORT} is already in use.")
        print("        다른 verify_server 가 이미 실행 중이거나 포트가 점유됨.")
        print("        기존 프로세스를 종료 후 다시 시작하세요.")
        input("\nEnter 키를 눌러 종료...")
        sys.exit(1)

    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"

    print(f"\n[OK] AI DevEnv Quest verification server running!")
    print(f"     {url}")
    print(f"     Stop: Ctrl+C\n")

    # 1초 후 브라우저 자동 오픈
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
