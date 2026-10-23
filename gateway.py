#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oracle Geçici Erişim — Gateway.
- Ed25519 imzalı geçici token'ları DOĞRULAR (yalnızca PUBLIC anahtar; imzalamaz).
- Token geçerli + süresi dolmamış + istenen işlem token kapsamında ise,
  hedef VPS'e FORCED-COMMAND kilitli operator anahtarıyla bağlanıp beyaz-liste
  işlemi çalıştırır. Shell/dosya/ayar YOK, yetki yükseltme YOK.
Sır tutmaz: sadece public dogrulama anahtari + forced-command operator anahtari.
"""
import base64, json, subprocess, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "gw_config.json").read_text(encoding="utf-8"))
PUBKEY = Ed25519PublicKey.from_public_bytes(base64.b64decode(CFG["verify_pubkey_b64"]))
OP_KEY = CFG["operator_key"]          # forced-command kilitli SSH anahtari
SSH_PORT = str(CFG.get("ssh_port", 62222))
SSH_USER = CFG.get("ssh_user", "ubuntu")
VPS = {v["id"]: v for v in CFG["vps"]}   # id -> {host, role, ...}

# Beyaz liste: istemci action -> (hedef vps id, operator komutu)
ALLOWED = {
    "status":          None,  # ozel: hepsinden durum
    "hp_hybrid_start": ("honeypot", "hybrid_start"),
    "hp_hybrid_stop":  ("honeypot", "hybrid_stop"),
    "hp_iot_start":    ("honeypot", "iot_start"),
    "hp_iot_stop":     ("honeypot", "iot_stop"),
    "doctor_status":   ("hermes",   "doctor_status"),
    "doctor_restart":  ("hermes",   "doctor_restart"),
    "vpn_up":          ("vpn",      "up"),
    "vpn_down":        ("vpn",      "down"),
    "vpn_direct":      ("vpn",      "direct"),
    "vpn_tor":         ("vpn",      "tor"),
    "vpn_newip":       ("vpn",      "new_ip"),
    "vpn_exitip":      ("vpn",      "exit_ip"),
}

app = FastAPI()


def _b64url_dec(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def verify_token(tok: str) -> dict:
    """tok = b64url(payload).b64url(sig). Dogrula, suresi/kapsami dondur."""
    try:
        p_b64, sig_b64 = tok.split(".", 1)
        payload_bytes = _b64url_dec(p_b64)
        sig = _b64url_dec(sig_b64)
        PUBKEY.verify(sig, payload_bytes)          # imza gecersizse firlatir
        payload = json.loads(payload_bytes)
    except (ValueError, InvalidSignature, Exception):
        raise HTTPException(401, "gecersiz token")
    if int(payload.get("exp", 0)) < time.time():
        raise HTTPException(401, "token suresi doldu")
    return payload


def _bearer(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if h.startswith("Bearer "):
        return h[7:].strip()
    q = request.query_params.get("t")
    if q:
        return q.strip()
    raise HTTPException(401, "token yok")


def op_ssh(vid: str, action: str, timeout: int = 40) -> dict:
    v = VPS.get(vid)
    if not v:
        return {"ok": False, "out": "bilinmeyen vps"}
    cmd = ["ssh", "-i", OP_KEY, "-p", SSH_PORT,
           "-o", "StrictHostKeyChecking=no", "-o", f"ConnectTimeout=12",
           f"{SSH_USER}@{v['host']}", action]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": r.returncode == 0, "out": (r.stdout or r.stderr).strip()[:1200]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "out": "zaman asimi"}


@app.get("/")
def index():
    return FileResponse(BASE / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/me")
def me(request: Request):
    p = verify_token(_bearer(request))
    return {"name": p.get("name", "misafir"), "exp": p.get("exp"),
            "kalan_sn": max(0, int(p.get("exp", 0) - time.time())),
            "scope": p.get("scope", [])}


@app.get("/api/status")
def status(request: Request):
    p = verify_token(_bearer(request))
    if "status" not in p.get("scope", []):
        raise HTTPException(403, "kapsamda yok: status")
    out = {}
    for vid in VPS:
        out[vid] = op_ssh(vid, "status")
    return {"vps": out, "kalan_sn": max(0, int(p.get("exp", 0) - time.time()))}


@app.post("/api/op/{action}")
def do_op(action: str, request: Request):
    p = verify_token(_bearer(request))
    if action not in ALLOWED or ALLOWED[action] is None:
        raise HTTPException(400, "gecersiz islem")
    if action not in p.get("scope", []):
        raise HTTPException(403, f"kapsamda yok: {action}")
    vid, opcmd = ALLOWED[action]
    return JSONResponse(op_ssh(vid, opcmd))
