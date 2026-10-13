# İndirilenler Düzenleyici

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Lisans](https://img.shields.io/badge/lisans-MIT-green)

İndirilenler klasörünü dosya türlerine göre otomatik ayıran, arayüzlü (GUI) bir araç.

`setup.exe` ve `kurulum.msi` → **Programlar ve Betikler**,
`foto.jpg` ve `logo.png` → **Resimler**,
`klip.mp4` → **Videolar** ... gibi.

![Uygulama ikonu](ikon_onizleme.png)

---

## Başlatma

| Dosya | Ne yapar |
|---|---|
| `masaustu_kisayolu_olustur.bat` | Masaüstüne tek tıklamalı kısayol ekler. **Bir kez çalıştırın.** Kısayol doğrudan `pythonw.exe`'yi hedefler, hiç konsol penceresi açılmaz ve uygulama ikonunu kullanır. |
| `baslat.bat` | Programı açar. Python PATH'te değilse de çalışır. |

Kapatmak için pencerenin sağ üst köşesindeki **X** yeterlidir. Klasörü açık
bırakırsanız pencere durumunu ve ayarlarını hatırlar.

---

## Nasıl kullanılır

1. Program açılır açılmaz **İndirilenler** klasörünü kendisi bulur (OneDrive
   yönlendirmesi varsa onu kullanır).
2. **Tara** (F5) → dosyalar türlerine göre gruplanır.
3. Tablodaki satırın **başındaki kutucuğa** tıklayarak o kategorinin taşınmasını
   aç/kapa yapar. Satırı **çift tıklayınca** o klasör açılır.
   *Diğer Dosyalar* varsayılan olarak kapalıdır.
4. **Düzenle** → dosyalar taşınır.

### Güvenlik: kuru çalıştırma

**Kuru çalıştırma** işaretliyken (varsayılan) hiçbir dosya taşınmaz; sadece
"ne olacak" bilgisi sağdaki loga yazılır ve düğmenin adı **Önizle** olur.                  *******************!!!!!!!!!!!!DİKKAT!!!!!!!!!!!!*******************
İşareti kaldırınca düğme **Düzenle** olur ve taşımadan önce onay penceresi çıkar.

### Geri alma

**Son taşımayı geri al** düğmesi, taşınan dosyaları eski yerine döndürür ve
programın oluşturduğu boş klasörleri temizler. Kayıt `veri\gecmis.jsonl`
dosyasında tutulur — program kapansa da sonraki açılışta geri alma çalışır.

---

## Kategoriler

| Klasör | Örnekler |
|---|---|
| Programlar ve Betikler | exe, msi, apk, bat, cmd, jar, ps1 |
| Disk Görüntüleri | iso, img, dmg, vhd |
| Resimler | jpg, png, gif, webp, svg, heic, tiff |
| Videolar | mp4, mkv, avi, mov, webm, m4v |
| Ses ve Müzik | mp3, wav, flac, aac, m4a |
| Belgeler | pdf, doc, docx, txt, epub, mobi |
| Tablolar | xls, xlsx, csv, ods |
| Sunumlar | ppt, pptx, odp, key |
| Çizim ve Tasarım | psd, ai, eps, sketch |
| 3B Modeller | blend, obj, stl, fbx, glb |
| Fontlar | ttf, otf, woff2 |
| Arşivler | zip, rar, 7z, tar, gz, cab |
| Kod Dosyaları | py, js, html, css, json, sql, java |
| Sertifikalar | pem, crt, p12, pfx |
| Diğer Dosyalar | tanınmayan uzantılar ve uzantısız dosyalar |

### Kuralları değiştirmek

**Seçenekler > Kuralları düzenle** → `veri\kurallar.json` Not Defteri'nde açılır:

```json
{
  "Programlar ve Betikler": ["exe", "msi", "bat"],
  "Resimler": ["jpg", "jpeg", "png"]
}
```

Kaydedip kapat, ardından **Seçenekler > Kuralları yeniden yükle**.

Dosyayı yoksa oluşturur — bozuk JSON olursa varsayılan kurallara döner.

---

## Verilerin nerede duruyor

Uygulama **kendi klasörünün dışına hiçbir dosya yazmaz.** Ürettiği her şey tek bir
yerde, `veri\` klasöründe toplanır:

| Dosya | İçerik |
|---|---|
| `veri\ayarlar.json` | Hangi klasör seçili, kuru çalıştırma açık mı |
| `veri\gecmis.jsonl` | Geri alma için taşıma kayıtları |
| `veri\kurallar.json` | Senin kuralların (yoksa varsayılanlar) |
| `veri\log_*.txt` | "Logu kaydet" ile dışa aktardığın loglar |

Bu klasörü silmek uygulamayı sıfırlar — kod dosyalarına dokunmadan tamamen
temiz bir başlangıç verir. GitHub'a yüklerken de `veri/` paylaşılmaz
(`.gitignore` içinde), çünkü içinde senin klasör yolların bulunur.

---

## Dokunulmayanlar

- Yarım inmiş indirmeler: `.crdownload`, `.part`, `.tmp`, `.download`
- Gizli/sistem dosyalar: `desktop.ini`, `Thumbs.db`, `~$...`, `.` ile başlayanlar
- **Alt klasörlerin içi** — yalnızca seçtiğiniz klasörün üst düzeyi taranır
- Aynı isimli dosya varsa numara eklenir: `rapor.pdf` → `rapor (1).pdf`

---

## Kısayollar

| Tuş | İşlev |
|---|---|
| `F5` | Tara |
| `Ctrl+O` | Klasör seç |
| Çift tıkla | Kategori klasörünü aç |

İşlem sürerken **İptal** gerçekten durdurur; o ana kadar taşınanlar geri alınabilir.

---

## Dosya düzeni

```
indirilenler_duzenleyici.py     uygulama (tek dosya, ek paket gerekmez)
baslat.bat                      başlatıcı (çift tıkla)
masaustu_kisayolu_olustur.bat   masaüstü kısayolu oluşturur
masaustu_kisayolu.ps1           kısayol betiği (.bat bunu çağırır)
ikon.ico                        uygulama ikonu (16–256 px, 7 boyut)
ikon_uret.py                    ikonu yeniden üretir (Pillow gerekir)
ikon_onizleme.png               ikon önizlemesi
veri/kurallar.json              (opsiyonel) kendi kuralların
veri/ayarlar.json               pencere tercihleri
veri/gecmis.jsonl               geri alma kayıtları
veri/log_*.txt                  kaydedilen loglar
test_sinama.py                  kendi kendini sınama (53 kontrol)
LICENSE                         MIT lisansı
```

### İkonu değiştirmek

`ikon_uret.py` ikonu sıfırdan çizer. Rengi ya da şekli değiştirmek için dosyanın
üstündeki paleti düzenleyip yeniden üretin:

```bat
pip install pillow
python ikon_uret.py
```

`ikon.ico` otomatik olarak `ikon_onizleme.png` önizlemesiyle birlikte yenilenir.
Kısayol eski ikonu önbelleğe alabileceği için değişiklikten sonra
`masaustu_kisayolu_olustur.bat`'ı bir kez daha çalıştırın.

**Gereksinim:** Python 3.8+ (Windows'ta standart gelen tkinter ile birlikte gelir).
Kurulum gerekmez, `pip install` yok — sadece Python yeterlidir.

## Testler

```
python test_sinama.py
```

Tarama, taşıma, geri alma, çakışma çözümü, iptal ve hatalı dosya senaryolarını
geçici klasörlerde deneyip sonunda hepsini temizler. Gerçek İndirilenler
klasörünüze dokunmaz.

## Lisans

[MIT](LICENSE) — kopyala, değiştir, dağıt; ticari kullanım dahil. Tek şart:
telif bildirimini dosyada bırakmak.

## Güvenlik notu

Uygulama **hiçbir veriyi dışarı göndermez**, internet bağlantısı kurmaz ve
başka bir yere kod yazmaz. Tek yaptığı iş, seçtiğiniz klasördeki dosyaları
alt klasörlere **taşımaktır** — bu yüzden kuru çalıştırma, onay penceresi ve
geri alma özellikleri vardır.
