#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# .env 파일 확인
if [ ! -f ".env" ]; then
  echo "⚠  .env 파일이 없습니다. .env.example을 복사합니다."
  cp .env.example .env
  echo "✏  .env 파일에 ANTHROPIC_API_KEY를 입력한 뒤 다시 실행하세요."
  exit 1
fi

# 가상환경 확인/생성
if [ ! -d "venv" ]; then
  echo "▶ 가상환경 생성 중..."
  python3 -m venv venv
fi

source venv/bin/activate

# 패키지 설치
echo "▶ 패키지 설치 중..."
pip install -q -r requirements.txt

# 서버 실행
echo ""
echo "=========================================="
echo "  Market Intelligence AI 서버 시작"
echo "  브라우저: http://localhost:8000"
echo "=========================================="
echo ""

python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
