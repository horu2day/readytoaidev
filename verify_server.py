#!/usr/bin/env python3
"""
AI 개발환경 퀘스트 — 환경 검증 서버
사용법:
  - macOS / Linux: python3 verify_server.py [--mac]
  - Windows:       python verify_server.py [--win] (또는 verify_server.exe)
  - 옵션: --os [auto|mac|win|linux], --port [PORT], --no-browser
"""
import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── stdout UTF-8 (Windows 콘솔 깨짐 방지) ────────────────────
try:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 3001
HOST = "localhost"
CURRENT_OS = "mac" if sys.platform == "darwin" else ("win" if sys.platform == "win32" else "linux")

# ── exe 실행 위치 찾기 ────────────────────────────────────────
def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def html_path():
    # --add-data 번들 시 sys._MEIPASS, 개발 환경은 base_dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "vscode-lecture.html")
    return os.path.join(base_dir(), "vscode-lecture.html")

# ── OS별 환경 변수(PATH) 보강 ────────────────────────────────
def get_system_env():
    env = os.environ.copy()
    if CURRENT_OS == "mac":
        path_parts = env.get("PATH", "").split(":")
        extra_paths = [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/usr/local/sbin",
            os.path.expanduser("~/.npm-global/bin"),
            os.path.expanduser("~/npm-global/bin"),
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/.cargo/bin"),
        ]
        # nvm 설치 노드 버전 경로 추가
        nvm_node_dir = os.path.expanduser("~/.nvm/versions/node")
        if os.path.isdir(nvm_node_dir):
            try:
                for v in sorted(os.listdir(nvm_node_dir), reverse=True):
                    b_dir = os.path.join(nvm_node_dir, v, "bin")
                    if os.path.isdir(b_dir):
                        extra_paths.append(b_dir)
            except Exception:
                pass

        for ep in extra_paths:
            if os.path.isdir(ep) and ep not in path_parts:
                path_parts.insert(0, ep)
        env["PATH"] = ":".join(path_parts)
    return env

# ── 시스템 명령 실행 ─────────────────────────────────────────
def run(cmd):
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            env=get_system_env()
        )
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

# ── VS Code 바이너리 위치 탐색 (Mac 호환) ─────────────────────
_CACHED_VSCODE_CMD = None

def get_vscode_cmd():
    global _CACHED_VSCODE_CMD
    if _CACHED_VSCODE_CMD:
        return _CACHED_VSCODE_CMD

    # 1. PATH에서 code 명령 탐색
    ok, _ = run("code --version")
    if ok:
        _CACHED_VSCODE_CMD = "code"
        return _CACHED_VSCODE_CMD

    # 2. macOS 전용: 앱 번들 내부 바이너리 탐색
    if CURRENT_OS == "mac":
        candidates = [
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
            os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
            os.path.expanduser("~/Downloads/Visual Studio Code.app/Contents/Resources/app/bin/code"),
        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                _CACHED_VSCODE_CMD = f'"{c}"'
                return _CACHED_VSCODE_CMD

        # 3. Spotlight (mdfind) 탐색
        try:
            r = subprocess.run(
                ["mdfind", "kMDItemCFBundleIdentifier == 'com.microsoft.VSCode'"],
                capture_output=True,
                text=True,
                timeout=3
            )
            for line in r.stdout.strip().splitlines():
                app_path = line.strip()
                bin_path = os.path.join(app_path, "Contents", "Resources", "app", "bin", "code")
                if os.path.isfile(bin_path) and os.access(bin_path, os.X_OK):
                    _CACHED_VSCODE_CMD = f'"{bin_path}"'
                    return _CACHED_VSCODE_CMD
        except Exception:
            pass

    _CACHED_VSCODE_CMD = "code"
    return _CACHED_VSCODE_CMD

def get_cmds():
    code_bin = get_vscode_cmd()
    is_win = CURRENT_OS == "win"
    return {
        "vscode":     f"{code_bin} --version",
        "python":     "python --version" if is_win else "python3 --version || python --version",
        "node":       "node -v",
        "npm":        "npm -v",
        "git":        "git --version",
        "git_config": "git config --global user.name",
        "claude":     "claude --version",
    }

def check_one(key):
    cmds = get_cmds()
    if key not in cmds:
        return {"ok": False, "error": "unknown check"}
    ok, out = run(cmds[key])

    # Windows: npm global bin may not be in inherited PATH
    if not ok and key == "claude" and CURRENT_OS == "win":
        claude_cmd = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
        if os.path.exists(claude_cmd):
            ok, out = run(f'"{claude_cmd}" --version')

    # macOS: npm global / homebrew fallback
    if not ok and key == "claude" and CURRENT_OS == "mac":
        mac_claude_candidates = [
            "/opt/homebrew/bin/claude",
            "/usr/local/bin/claude",
            os.path.expanduser("~/.npm-global/bin/claude"),
            os.path.expanduser("~/npm-global/bin/claude"),
            os.path.expanduser("~/.local/bin/claude"),
        ]
        for p in glob.glob(os.path.expanduser("~/.nvm/versions/node/*/bin/claude")):
            mac_claude_candidates.append(p)
        for cpath in mac_claude_candidates:
            if os.path.isfile(cpath) and os.access(cpath, os.X_OK):
                ok, out = run(f'"{cpath}" --version')
                if ok:
                    break

    ver = out.split("\n")[0].strip() if ok else ""
    return {"ok": ok, "name": key, "version": ver, "error": "" if ok else out}

def check_all():
    cmds = get_cmds()
    result = {k: check_one(k) for k in cmds}
    result['korean']     = check_ext(EXT_S2)
    result['extensions'] = check_ext(EXT_S3)
    result['vssettings'] = check_vssettings()
    return result

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
    code_bin = get_vscode_cmd()
    ok, out = run(f"{code_bin} --list-extensions")
    if not ok:
        err_msg = "code 명령 실패 — PATH에 code가 없거나 VS Code가 설치되지 않음"
        if CURRENT_OS == "mac":
            err_msg += " (macOS의 경우 VS Code에서 Cmd+Shift+P → 'Shell Command: Install code' 실행 권장)"
        return {"ok": False, "error": err_msg}
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
    """Remove // and /* */ comments and trailing commas from JSONC."""
    import re
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
            elif c == "/" and i + 1 < len(text) and text[i+1] == "*":
                i += 2
                while i + 1 < len(text) and not (text[i] == "*" and text[i+1] == "/"):
                    i += 1
                i += 2
                continue
            else:
                out.append(c)
        i += 1
    result = "".join(out)
    result = re.sub(r',(\s*[}\]])', r'\1', result)
    return result

def check_vssettings():
    import pathlib
    if CURRENT_OS == "win":
        base = pathlib.Path(os.environ.get("APPDATA", ""))
    elif CURRENT_OS == "mac":
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
            p = html_path()
            if os.path.exists(p):
                with open(p, "rb") as f:
                    self.send_html(f.read())
            else:
                self.send_json({"error": "vscode-lecture.html not found"}, 404)
            return

        # ── API ───────────────────────────────────────────────
        if path == "/api/ping":
            self.send_json({"ok": True, "os": CURRENT_OS})
        elif path == "/api/info":
            self.send_json({
                "ok": True,
                "os": CURRENT_OS,
                "port": PORT,
                "vscode_bin": get_vscode_cmd(),
                "python": sys.executable
            })
        elif path == "/api/check/all":
            self.send_json(check_all())
        elif path == "/api/check/terminal":
            self.send_json({"ok": True, "name": "terminal", "version": f"터미널 사용 확인됨 ({CURRENT_OS.upper()})"})
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
def port_free(port, host="localhost"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI 개발환경 퀘스트 — 환경 검증 서버",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""예시:
  python3 verify_server.py --mac          # macOS 모드로 실행 (단축)
  python3 verify_server.py --win          # Windows 모드로 실행 (단축)
  python3 verify_server.py --os mac       # OS 명시적 지정
  python3 verify_server.py --port 3002    # 포트 직접 지정
  python3 verify_server.py --no-browser   # 브라우저 자동 오픈 안 함
"""
    )
    parser.add_argument(
        "--os",
        choices=["auto", "mac", "win", "linux"],
        default="auto",
        help="대상 운영체제 지정 (기본: auto 감지)"
    )
    parser.add_argument(
        "--mac", "-m",
        action="store_true",
        help="macOS 모드로 실행 (단축 옵션)"
    )
    parser.add_argument(
        "--win", "-w",
        action="store_true",
        help="Windows 모드로 실행 (단축 옵션)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="서버 포트 번호 (기본: 3001, 사용 중일 경우 다음 가용 포트 자동 선택)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="서버 바인드 호스트 (기본: localhost)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="브라우저 자동 열기 비활성화"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    HOST = args.host

    # OS 결정
    if args.mac:
        CURRENT_OS = "mac"
    elif args.win:
        CURRENT_OS = "win"
    elif args.os != "auto":
        CURRENT_OS = args.os
    else:
        CURRENT_OS = "mac" if sys.platform == "darwin" else ("win" if sys.platform == "win32" else "linux")

    # 포트 결정 (명시 지정 또는 자동 탐색)
    if args.port is not None:
        PORT = args.port
        if not port_free(PORT, HOST):
            print(f"[ERROR] Port {PORT} is already in use on {HOST}.")
            print("        다른 프로세스가 포트를 점유 중입니다. 다른 포트를 지정하세요: --port <PORT>")
            if sys.stdin.isatty():
                try:
                    input("\nEnter 키를 눌러 종료...")
                except (EOFError, KeyboardInterrupt):
                    pass
            sys.exit(1)
    else:
        PORT = 3001
        original_port = PORT
        while not port_free(PORT, HOST) and PORT < 3010:
            PORT += 1
        if not port_free(PORT, HOST):
            print(f"[ERROR] Port 3001~3010이 모두 사용 중입니다. --port 옵션으로 다른 포트를 지정하세요.")
            sys.exit(1)
        if PORT != original_port:
            print(f"[INFO] 포트 {original_port}이(가) 이미 사용 중이어서 가용 포트 {PORT}(으)로 자동 연결되었습니다.")

    server = HTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"

    os_label = {"mac": "macOS 🍎", "win": "Windows 🪟", "linux": "Linux 🐧"}.get(CURRENT_OS, CURRENT_OS)
    print(f"\n[OK] AI DevEnv Quest verification server running! ({os_label})")
    print(f"     URL : {url}")
    print(f"     VSCode CLI: {get_vscode_cmd()}")
    print(f"     Stop: Ctrl+C\n")

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

