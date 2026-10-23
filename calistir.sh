#!/usr/bin/env bash
# Gateway'i baslat. Varsayilan port 8095 (PORT=... ile degistir).
cd "$(dirname "$0")"
[ -x venv/bin/uvicorn ] || { echo "once ./kur.sh calistir." >&2; exit 1; }
echo "Gateway baslatiliyor -> 0.0.0.0:${PORT:-8095}  (Ctrl+C ile durdur)"
exec ./venv/bin/uvicorn gateway:app --host 0.0.0.0 --port "${PORT:-8095}"
