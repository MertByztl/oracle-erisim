# Oracle Gecici Erisim — GATEWAY kurulumu (Windows PowerShell). venv kullanir.
Set-Location $PSScriptRoot
Write-Host "[1/2] venv + bagimliliklar (fastapi, uvicorn, cryptography)..."
python -m venv venv
.\venv\Scripts\python -m pip install --upgrade pip | Out-Null
.\venv\Scripts\python -m pip install -r requirements.txt
if (-not (Test-Path gw_config.json)) {
  Copy-Item gw_config.example.json gw_config.json
  Write-Host "   >> gw_config.json olusturuldu"
}
Write-Host ""
Write-Host "============================================================"
Write-Host "KURULUM BITTI. Sirasiyla:"
Write-Host "  1) gw_config.json'u doldur (verify_pubkey_b64, operator_key, VPS adresleri)"
Write-Host "  2) operator anahtarini koy"
Write-Host "  3) Baslat:  .\calistir.bat   (ya da)"
Write-Host "     .\venv\Scripts\python -m uvicorn gateway:app --host 0.0.0.0 --port 8095"
Write-Host "============================================================"
