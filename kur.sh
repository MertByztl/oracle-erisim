#!/usr/bin/env bash
# Oracle Geçici Erişim — GATEWAY kurulumu (Linux). venv kullanir; global pip YOK.
set -e
cd "$(dirname "$0")"
echo "[1/3] python venv + ssh istemcisi..."
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip openssh-client
echo "[2/3] venv + bagimliliklar (fastapi, uvicorn, cryptography)..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip >/dev/null
./venv/bin/pip install -r requirements.txt
echo "[3/3] config..."
[ -f gw_config.json ] || { cp gw_config.example.json gw_config.json; echo "   >> gw_config.json olusturuldu"; }
chmod +x calistir.sh 2>/dev/null || true
cat <<'SON'

============================================================
KURULUM BITTI. Sirasiyla:
  1) gw_config.json'u doldur: verify_pubkey_b64 (panelin verdigi), operator_key yolu, VPS adresleri
  2) operator anahtarini koy (forced-command kilitli SSH anahtari)
  3) Baslat:  ./calistir.sh      (varsayilan port 8095)
============================================================
SON
