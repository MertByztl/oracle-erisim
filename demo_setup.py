#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEMO kurulum — tek başına denemek için.
Throwaway Ed25519 anahtar çifti + gw_config.json üretir (DEMO modu: gerçek VPS/Hermes YOK,
Hermes cevapları kanned). Gerçek kurulumda imza anahtarı PANELDE olur, gateway'de DEĞİL.

Çalıştır:  python demo_setup.py   ->   sonra  ./calistir.sh  (veya calistir.bat)
Tarayıcıda:  /        (misafir: Erişim İste)
             /admin   (sahip: onayla + süre + geri sayım barı)
"""
import base64, json, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

HERE = os.path.dirname(os.path.abspath(__file__))
priv = Ed25519PrivateKey.generate()
priv_raw = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
pub_raw = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

open(os.path.join(HERE, "issuer_priv.b64"), "w").write(base64.b64encode(priv_raw).decode())
cfg = {
    "verify_pubkey_b64": base64.b64encode(pub_raw).decode(),
    "issuer_priv_file": os.path.join(HERE, "issuer_priv.b64"),  # !! DEMO ONLY
    "hermes_relay": None,                                       # DEMO: kanned cevaplar
    "vps": [],
}
open(os.path.join(HERE, "gw_config.json"), "w").write(json.dumps(cfg, indent=2))
print("DEMO hazir. Simdi gateway'i baslat:")
print("  Linux:   ./calistir.sh       Windows: calistir.bat")
print("Tarayicida:  http://127.0.0.1:8095/   (misafir)   ve   /admin   (onay paneli)")
