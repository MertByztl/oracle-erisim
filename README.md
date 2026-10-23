# 🔑 Oracle Geçici Erişim — Hafif Panel

3 VPS'i (Honeypot · VPN · Hermes) **geçici, süreli ve kısıtlı** yetkiyle izleyip
temel işlemleri yapmaya yarayan **hafif web arayüzü**. Arkadaşına/bir cihaza
"1 saatlik bak" demek için. **Bu repo public'tir ve içinde HİÇBİR SIR YOKTUR.**

## Güvenlik modeli (önemli)
Üç katman, hepsi "yetki yükseltmeyi" engeller:

1. **Geçici token (Ed25519 imzalı):** Token'ı **yalnızca senin panelin** (özel imza
   anahtarıyla) üretir. Süresi (`exp`) ve kapsamı (`scope`) token'ın içinde yazılı ve
   imzalı — kimse değiştiremez. Gateway yalnızca **public doğrulama anahtarını** tutar,
   yani gateway ele geçse bile **yeni token üretilemez.**
2. **Beyaz liste (operator) işlemleri:** Gateway, hedef VPS'lere **forced-command
   kilitli** anahtarla bağlanır — sadece tanımlı işlemler (durum, başlat/durdur, doktor,
   vpn aç/kapat). **Shell yok, dosya yok, ayar yok, root yok.**
3. **Süre dolunca otomatik biter:** `exp` geçince token her yerde geçersiz. Temizlik yok.

Yani geçici erişen: **operatör**, asla **yönetici** olamaz. Kendine yeni/sınırsız
erişim **yazamaz** — o yetki (imza anahtarı + ayarlar) sadece sende, şifrenin arkasında.

## Parçalar
| Dosya | Nerede çalışır | Sır tutar mı |
|---|---|---|
| `index.html` | Tarayıcı (arkadaşın cihazı) | Hayır — sadece token'ı URL'den okur |
| `gateway.py` | Bir VPS (public port) | Sadece **public** doğrulama anahtarı + forced-command operator anahtarı |
| `operator.sh` | Her VPS (forced-command) | Hayır — beyaz liste komut eşleyici |
| *(issuer)* | **Senin panelin (private repo)** | **Özel imza anahtarı — burada DEĞİL** |

## Nasıl kullanılır (akış)
1. Sen panelden **"Geçici Erişim Oluştur"** → süre (örn. 1s) + kapsam seç → bir **link**
   üretir: `https://<gateway>/#t=<token>`
2. Linki arkadaşına yolla. O açar, 3 VPS'in durumunu görür, izinli işlemleri yapar.
3. Süre dolunca link **çalışmaz** — her yer yine güvenli.

## Kurulum
`gateway.py` için: `cp gw_config.example.json gw_config.json` → doldur (public anahtar,
operator SSH anahtar yolu, VPS adresleri). `gw_config.json` **git'e girmez.**
Ayrıntı: aşağıdaki "Kurulum" bölümü (deploy adımları eklenecek).

> Not: İmza anahtarının **özel** yarısı yalnızca ana panelde (private repo) üretilir ve
> saklanır. Bu repo'ya ne özel anahtar ne token ne parola girer.
