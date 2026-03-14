# GameChanger (Windows)

GameChanger, oyun oncesi bilgisayari daha akici hale getirmek icin hazirlanmis hafif bir arac.
Amac: gereksiz arka plan sureclerini kapatmak, guc planini yuksek performansa almak ve temp dosyalarini temizlemek.

## Proje Durumu

- Durum: aktif gelistirme
- Hedef: eski veya HDD kullanan sistemlerde guvenli ve geri alinabilir optimizasyonlar
- Yol haritasi: `ROADMAP.md`
- Adim adim urun plani: `SCENARIO_PLAN.md`

## Ne yapiyor?

- Aday arka plan uygulamalarini listeler (Chrome, Discord, Edge, OneDrive vb.)
- Sectiklerini kapatir
- LoL client sureclerinin onceligini dusurerek CPU baskisini azaltir
- CS2/Steam sureclerine oncelik-I/O ayari uygular
- HDD kullaniminda arka plan I/O yukunu dusurur
- LoL/CS2 dosyalarini okuyarak cache isitma yapar
- Windows animasyon ve transparan efektleri azaltan hafif mod sunar
- Dry-run onizleme ile degisiklikleri uygulamadan raporlar
- Kaydedilen guvenli ayarlari rollback ile geri alir
- Hazir profiller sunar: LOL_SAFE, CS2_HDD, DESKTOP_LIGHT
- Her profil icin tek tik uygula/geri al akisi vardir
- Yapilandirilmis loglari JSONL olarak saklar (timestamp + event)
- Aksiyon oncesi/sonrasi CPU-RAM-process snapshot kaydi alir
- Diagnostics export ile tek dosyada sistem ve uygulama ozetini verir
- Guc planini Yuksek Performans moduna alir
- Temp klasorlerinde temizlik yapar
- Tek tusla "Oyun Oncesi Optimize" akisini calistirir

## Gereksinimler

- Windows 10/11
- Python 3.10+

## Calistirma

```bat
py -m pip install -r requirements.txt
py src\main.py
```

## EXE olusturma

Kolay yol:

```bat
build_exe.bat
```

Build script ozellikleri:

- Surumu `src\\version.py` dosyasindan alir
- EXE metadata icine versiyon bilgisini embed eder
- `assets\\app.ico` varsa otomatik ikon ekler
- `dist\\SHA256SUMS.txt` icinde SHA256 checksum uretir
- Ortam degiskenleri verilirse opsiyonel kod imzalama dener

Opsiyonel imzalama degiskenleri:

- `SIGNTOOL_PATH` (ornek: Windows SDK `signtool.exe` yolu)
- `SIGN_CERT_FILE` (pfx dosya yolu)
- `SIGN_CERT_PASSWORD` (pfx sifresi, opsiyonel)
- `SIGN_TIMESTAMP_URL` (ornek: `http://timestamp.digicert.com`)

Manuel yol:

```bat
py -m pip install -r requirements.txt
py -m pip install pyinstaller
py -m PyInstaller --onefile --noconsole --name GameChanger src\main.py
```

Cikti:

- `dist\GameChanger.exe`
- `dist\SHA256SUMS.txt`

## Gelistirici Belgeleri

- Katki rehberi: `CONTRIBUTING.md`
- Guvenlik politikasi: `SECURITY.md`
- Lisans: `LICENSE`
- Release checklist: `RELEASE_CHECKLIST.md`
- Release notes sablonu: `RELEASE_NOTES_TEMPLATE.md`

## Onemli notlar

- En iyi sonuc icin uygulamayi yonetici olarak ac.
- Bu arac donanim overclock yapmaz, sistemde riskli registry hilesi uygulamaz.
- Oyunlarda takilma sadece CPU'dan degil, disk, sicaklik (throttling), surucu ve arka plan overlay yazilimlarindan da kaynaklanabilir.
- Tum tweak'ler varsayilan olarak kullanici seviyesinde tutulur.

## Senin sistemin icin hizli tavsiye (i7-7700K / 16GB / GTX 1070)

- Windows guc plani: Yuksek Performans
- NVIDIA ayarlari: oyun icin "Prefer maximum performance"
- Discord/GeForce overlay kapatma
- CS2 ve LoL dosyalarini SSD'de tutma
- Arka planda tarayici sekme sayisini azaltma
