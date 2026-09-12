#!/usr/bin/env bash
# AI 개발환경 퀘스트 — macOS 간편 구동 스크립트

set -e
cd "$(dirname "$0")"

echo "=========================================="
echo "🍎 AI 개발환경 퀘스트 - macOS 구동 스크립트"
echo "=========================================="

# Python 3 확인
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1 && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON_CMD="python"
else
    echo "❌ Python 3이 설치되어 있지 않습니다."
    echo "   https://www.python.org/downloads/ 에서 Python 3을 설치해 주세요."
    exit 1
fi

echo "✔ Python: $($PYTHON_CMD --version)"
echo "✔ verify_server.py 를 macOS 모드로 실행합니다..."
echo "------------------------------------------"

exec $PYTHON_CMD verify_server.py --mac "$@"
