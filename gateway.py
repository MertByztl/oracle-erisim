#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Oracle Geçici Erişim — Hermes Sohbet + Talep/Onay Gateway.

Akış: misafir "Erişim İste" -> talep kuyruğa (isim+IP+cihaz, VERI olarak) ->
Mert panelden görür -> süre+kapsam seçip ONAYLAR -> imzalı süreli token iner ->
misafir sohbet eder -> süre dolunca token geçersiz.

Güvenlik:
- Token Ed25519 imzalı; DOGRULAMA public anahtarla. (imza = yalnizca issuer.)
- Misafir girdisi (isim/UA) escape+limit; komut/eval'e girmez -> enjeksiyon yok.
- !! DEMO: mint (imzalama) burada yapiliyor. CANLIDA imza PANELDE olur, gateway yalniz dogrular.
"""
import base64, json, re, time, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey, Ed25519PrivateKey
from cryptography.exceptions import InvalidSignature

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "gw_config.json").read_text(encoding="utf-8"))
PUBKEY = Ed25519PublicKey.from_public_bytes(base64.b64decode(CFG["verify_pubkey_b64"]))
PRIV = None
if CFG.get("issuer_priv_file"):          # DEMO: mint icin ozel anahtar (canlida YOK)
    PRIV = Ed25519PrivateKey.from_private_bytes(base64.b64decode(Path(CFG["issuer_priv_file"]).read_text()))
LIVE = CFG.get("hermes_relay")

app = FastAPI()
REQS = {}          # request_id -> {name, ip, ua, ts, status, token}
GRANTS = []        # [{name, start, exp}]
_SESS = {}         # jti -> {name, n}

SAFE = re.compile(r"[\x00-\x1f\x7f]")
def clean(s, n=120): return SAFE.sub("", str(s or ""))[:n]

def b64url(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _b64url_dec(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_token(tok):
    try:
        p_b64, sig_b64 = tok.split(".", 1)
        pb = _b64url_dec(p_b64)
        PUBKEY.verify(_b64url_dec(sig_b64), pb)
        payload = json.loads(pb)
    except Exception:
        raise HTTPException(401, "gecersiz token")
    if int(payload.get("exp", 0)) < time.time():
        raise HTTPException(401, "token suresi doldu")
    return payload


def mint(name, hours, scope):
    if not PRIV:
        raise HTTPException(500, "mint anahtari yok (canlida panelde)")
    payload = {"exp": int(time.time()) + int(hours * 3600), "scope": scope,
               "name": clean(name, 40), "jti": uuid.uuid4().hex[:10]}
    pb = json.dumps(payload, separators=(",", ":")).encode()
    return b64url(pb) + "." + b64url(PRIV.sign(pb)), payload["exp"]


def _tok(request):
    h = request.headers.get("authorization", "")
    if h.startswith("Bearer "): return h[7:].strip()
    q = request.query_params.get("t")
    if q: return q.strip()
    raise HTTPException(401, "token yok")

def _require_chat(request):
    p = verify_token(_tok(request))
    if "hermes_chat" not in p.get("scope", []):
        raise HTTPException(403, "kapsamda yok")
    return p


# ---------------- sayfalar ----------------
@app.get("/")
def index(): return FileResponse(BASE / "index.html", headers={"Cache-Control": "no-store"})

@app.get("/admin")
def admin(): return FileResponse(BASE / "admin.html", headers={"Cache-Control": "no-store"})


# ---------------- misafir: talep + bekleme ----------------
@app.post("/api/request")
async def req_access(request: Request):
    body = await request.json()
    name = clean(body.get("name", ""), 40) or "isimsiz"
    rid = uuid.uuid4().hex[:8]
    REQS[rid] = {"name": name,
                 "ip": clean(request.client.host if request.client else "?", 45),
                 "ua": clean(request.headers.get("user-agent", ""), 160),
                 "ts": int(time.time()), "status": "pending", "token": None}
    return {"request_id": rid}

@app.get("/api/poll")
def poll(request_id: str):
    r = REQS.get(clean(request_id, 16))
    if not r: raise HTTPException(404, "istek yok")
    return {"status": r["status"], "token": r["token"] if r["status"] == "approved" else None}


# ---------------- sahip: liste / onayla / reddet / grant'lar ----------------
# (DEMO: admin ucları auth'suz; CANLIDA panel auth'u arkasinda olur)
@app.get("/api/requests")
def list_reqs():
    return {"pending": [{"id": k, "name": v["name"], "ip": v["ip"], "ua": v["ua"], "ts": v["ts"]}
                        for k, v in REQS.items() if v["status"] == "pending"]}

@app.post("/api/approve")
async def approve(request: Request):
    body = await request.json()
    rid = clean(body.get("request_id", ""), 16)
    hours = float(body.get("hours", 1)); hours = max(0.05, min(72, hours))
    r = REQS.get(rid)
    if not r or r["status"] != "pending":
        raise HTTPException(404, "istek yok")
    tok, exp = mint(r["name"], hours, ["hermes_chat"])
    r["status"] = "approved"; r["token"] = tok
    GRANTS.append({"name": r["name"], "start": int(time.time()), "exp": exp})
    return {"ok": True, "exp": exp}

@app.post("/api/deny")
async def deny(request: Request):
    body = await request.json()
    r = REQS.get(clean(body.get("request_id", ""), 16))
    if r: r["status"] = "denied"
    return {"ok": True}

@app.get("/api/grants")
def grants():
    now = time.time()
    out = [{"name": g["name"], "kalan_sn": max(0, int(g["exp"] - now)),
            "total_sn": max(1, g["exp"] - g["start"])} for g in GRANTS if g["exp"] > now]
    return {"grants": out}


# ---------------- misafir: sohbet ----------------
@app.get("/api/me")
def me(request: Request):
    p = _require_chat(request)
    return {"name": p.get("name", "misafir"), "exp": p.get("exp"),
            "kalan_sn": max(0, int(p.get("exp", 0) - time.time())), "scope": p.get("scope", [])}

@app.get("/api/hello")
def hello(request: Request):
    p = _require_chat(request); name = p.get("name", "")
    return {"text": f"Selam{(' '+name) if name else ''}! 👋 Ben Hermes, Mert'in asistanıyım. "
                    "Sen kimsin — Mert'in bir arkadaşı mısın? Nasıl hitap edeyim?"}

def demo_reply(sess, name, msg):
    low = msg.lower()
    # Mert hakkinda SORU (giris cumlesinde degil): mert + soru belirteci
    mert_q = ("mert" in low or "sahib" in low) and any(q in low for q in ["kim", "ne ", "nere", "kaç", "kac", "hangi", "?", "yaş", "yas", "adres", "telefon", "iş ", "is "])
    if mert_q or any(w in low for w in ["dosya", "dizin", "klasör", "klasor", "vps", "sunucu", "config", "anahtar", " key", "şifre", "parola"]):
        return ("Misafir olarak kendi sistemime dair bilgi paylaşamam. Ama SENİN bilgisayarında "
                "yardımcı olabilirim — her komutu önce onaylarsın. Ne yapmak istersin? (demo)")
    if sess["n"] == 0:
        sess["n"] = 1
        return (f"Memnun oldum{(' '+name) if name else ''}! 👋 Bilgisayarında bir şey yapmamı istersen "
                "sana bağlanabilirim; ama iznin olmadan hiçbir komut çalışmaz. Ne yapmak istersin? (demo)")
    sess["n"] += 1
    return "Anladım. (demo) Canlı bağlantıda bunu senin PC'nde, her adımı onayına sunarak yaparım. Başka?"

@app.post("/api/chat")
async def chat(request: Request):
    p = _require_chat(request)
    body = await request.json()
    msg = clean(body.get("message", ""), 4000)
    if not msg: raise HTTPException(400, "bos mesaj")
    sess = _SESS.setdefault(p.get("jti", "x"), {"name": p.get("name", ""), "n": 0})
    if LIVE:
        raise HTTPException(503, "canli Hermes henuz baglanmadi")
    return {"reply": demo_reply(sess, sess.get("name", ""), msg)}
