# -*- coding: utf-8 -*-
"""Arayuz acmadan kutuphane mantigini sinar: test_sinama.py"""
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indirilenler_duzenleyici as mod  # noqa: E402

GECICI = Path(tempfile.gettempdir()) / f"dl_test_{uuid.uuid4().hex[:8]}"
hatalar = []


def kontrol(kosul, mesaj):
    print(("  OK   " if kosul else "  HATA ") + mesaj)
    if not kosul:
        hatalar.append(mesaj)


print("1) Kural haritasi")
harita, sira = mod.kurallari_yukle()
kontrol(harita.get("exe") == "Programlar ve Betikler", "exe -> Programlar ve Betikler")
kontrol(harita.get("jpg") == "Resimler", "jpg -> Resimler")
kontrol(harita.get("png") == "Resimler", "png -> Resimler")
kontrol(harita.get("mp4") == "Videolar", "mp4 -> Videolar")
kontrol(harita.get("zip") == "Arşivler", "zip -> Arşivler")
kontrol(len(sira) >= 10, f"{len(sira)} kategori tanimli")

print("2) Örnek klasör kurulumu")
GECICI.mkdir(parents=True, exist_ok=True)
(GECICI / "setup.exe").write_bytes(b"MZ" + b"\0" * 500)
(GECICI / "kurulum.msi").write_bytes(b"\0" * 200)
(GECICI / "tatli.jpg").write_bytes(b"\xff\xd8\xff" + b"\0" * 900)
(GECICI / "manzara.png").write_bytes(b"\x89PNG" + b"\0" * 300)
(GECICI / "video.mp4").write_bytes(b"\0" * 5000)
(GECICI / "arsiv.zip").write_bytes(b"PK" + b"\0" * 100)
(GECICI / "notlar.txt").write_bytes(b"merhaba")
(GECICI / "sunum.pptx").write_bytes(b"\0" * 100)
(GECICI / "veri.csv").write_bytes(b"a,b")
(GECICI / "font.ttf").write_bytes(b"\0" * 100)
(GECICI / "kod.py").write_bytes(b"print(1)")
(GECICI / "bilinmeyen.xyz").write_bytes(b"\0" * 10)
(GECICI / "uzantisiz").write_bytes(b"\0" * 10)
(GECICI / "yarim.crdownload").write_bytes(b"\0" * 9999)
(GECICI / "desktop.ini").write_bytes(b"[.ShellClassInfo]")
(GECICI / "~$gecici.docx").write_bytes(b"\0" * 10)
(GECICI / "AltKlasor").mkdir(exist_ok=True)
(GECICI / "AltKlasor" / "ic.mp4").write_bytes(b"\0" * 10)
print(f"   {GECICI} icinde {len(list(GECICI.iterdir()))} oge")

print("3) Tarama")
sonuc = mod.klasoru_tara(GECICI, harita)
kategoriler = {}
for oge in sonuc.gecerli:
    kategoriler.setdefault(oge["kategori"], []).append(oge["ad"])

kontrol(len(sonuc.gecerli) == 13, f"13 dosya tarandi (bulunan: {len(sonuc.gecerli)})")
kontrol(len(kategoriler.get("Programlar ve Betikler", [])) == 2, "2 exe/msi ayrildi")
kontrol(len(kategoriler.get("Resimler", [])) == 2, "2 gorsel ayrildi")
kontrol(kategoriler.get("Diğer Dosyalar") == ["bilinmeyen.xyz", "uzantisiz"],
        "bilinmeyen + uzantisiz -> Diger Dosyalar")
kontrol("yarim.crdownload" not in [o["ad"] for o in sonuc.gecerli],
        "yarim indirme atlandi")
kontrol("desktop.ini" not in [o["ad"] for o in sonuc.gecerli], "desktop.ini atlandi")
kontrol("~$gecici.docx" not in [o["ad"] for o in sonuc.gecerli], "~$ gecici dosya atlandi")
kontrol(sonuc.klasor_sayisi == 1, "1 alt klasor sayildi")
kontrol("ic.mp4" not in [o["ad"] for o in sonuc.gecerli], "alt klasor icine girilmedi")
kontrol(sonuc.toplam_boyut == sum(p.stat().st_size for p in GECICI.iterdir() if p.is_file()
                                 and p.name not in ("yarim.crdownload", "desktop.ini",
                                                    "~$gecici.docx")),
        f"toplam boyut sadece gecerli dosyalari iceriyor ({sonuc.toplam_boyut})")

print("4) Kuru calistirma (tasima yapilmamali)")
onceki = sorted(p.name for p in GECICI.iterdir())
kontrol(len(onceki) == 17, f"klasorde 17 oge var ({len(onceki)})")

print("5) Tasima")
secilecek = [o for o in sonuc.gecerli if o["kategori"] != "Diğer Dosyalar"]
sonuc_tasma = mod.dosyalari_tasi(secilecek, GECICI)
kontrol(len(sonuc_tasma["tasinan"]) == 11, f"11 dosya tasindi ({len(sonuc_tasma['tasinan'])})")
kontrol(not sonuc_tasma["hatali"], f"hata yok ({sonuc_tasma['hatali']})")
for kategori in ("Programlar ve Betikler", "Resimler", "Videolar", "Arşivler",
                 "Belgeler", "Sunumlar", "Tablolar", "Fontlar", "Kod Dosyaları"):
    kontrol((GECICI / kategori).is_dir(), f"klasor olustu: {kategori}")
kontrol((GECICI / "Programlar ve Betikler" / "setup.exe").is_file(), "setup.exe yerinde")
kontrol((GECICI / "Resimler" / "tatli.jpg").is_file(), "tatli.jpg yerinde")
kontrol((GECICI / "tatli.jpg").exists() is False, "eski yerde kopyasi kalmadi")
kontrol((GECICI / "Diğer Dosyalar" / "bilinmeyen.xyz").exists() is False,
        "Diger Dosyalar tasinmadi")
kontrol((GECICI / "AltKlasor" / "ic.mp4").is_file(), "alt klasor icerigi yerinde")

print("6) Ikinci taramada temizlik")
sonuc2 = mod.klasoru_tara(GECICI, harita)
kalan = sorted(o["ad"] for o in sonuc2.gecerli)
kontrol(kalan == ["bilinmeyen.xyz", "uzantisiz"],
        f"yalnizca secilmeyenler kaldi ({kalan})")
kontrol(sonuc2.klasor_sayisi == 10, f"10 klasor tespit edildi ({sonuc2.klasor_sayisi})")

print("7) Gecmis + geri alma")
mod.gecmise_ekle("tasindi", GECICI, sonuc_tasma["tasinan"])
kayit = mod.son_tasima_kaydi()
kontrol(kayit is not None and len(kayit["dosyalar"]) == 11, "gecmis kaydi olustu")
geri = mod.geri_al(kayit)
kontrol(geri["geri"] == 11, f"11 dosya geri alindi ({geri['geri']})")
kontrol(not geri["hatali"], "geri almada hata yok")
kontrol(len(geri["silinen_klasor"]) == 9,
        f"9 bos kategori klasoru kaldirildi ({len(geri['silinen_klasor'])})")
kontrol(sorted(p.name for p in GECICI.iterdir()) == onceki,
        f"klasor orijinal haline dondu ({sorted(p.name for p in GECICI.iterdir())})")

print("8) Cakisma cozumu (ayni adli dosya)")
(GECICI / "Resimler").mkdir(exist_ok=True)
(GECICI / "Resimler" / "yeni.jpg").write_bytes(b"\xff\xd8\xff\xff")
(GECICI / "yeni.jpg").write_bytes(b"\xff\xd8\xff\xfe")
hedef = mod.benzersiz_hedef(GECICI, "yeni.jpg")
kontrol(hedef.name == "yeni (1).jpg", f"cakisma cozuldu: {hedef.name}")
(GECICI / "yeni (1).jpg").write_bytes(b"\xff\xd8\xff\xfd")
hedef2 = mod.benzersiz_hedef(GECICI, "yeni.jpg")
kontrol(hedef2.name == "yeni (2).jpg", f"ikinci cakisma da cozuldu: {hedef2.name}")
(GECICI / "yeni (1).jpg").unlink()
(GECICI / "yeni.jpg").unlink()
shutil.rmtree(GECICI / "Resimler")
kontrol(sorted(p.name for p in GECICI.iterdir()) == onceki,
        "cakisma testi sonrasi klasor yine orijinal")

print("9) Bozuk / eksik dosyalara dayaniklik")
bozuk = Path(tempfile.gettempdir()) / "bozuk_kurallar.json"
eski = mod.kurallar_dosyasi()
yedek = eski.with_suffix(".json.bak") if eski.is_file() else None
if yedek and yedek.exists():
    yedek.unlink()
if eski.is_file():
    eski.rename(yedek)
eski.write_text("{ bu gecerli json degil", encoding="utf-8")
harita2, sira2 = mod.kurallari_yukle()
kontrol(harita2.get("exe") == "Programlar ve Betikler", "bozuk kurallar.json -> varsayilanlar")
eski.unlink()
if yedek and yedek.exists():
    yedek.rename(eski)

print("10) Boyut bicimi")
kontrol(mod.boyut_metni(512) == "512 B", "512 B")
kontrol(mod.boyut_metni(2048) == "2.0 KB", "2.0 KB")
kontrol(mod.boyut_metni(5 * 1024 ** 3) == "5.0 GB", "5.0 GB")

print("11) Indirilenler klasoru algilama")
bulunan = mod.varsayilan_indirilenler_klasoru()
kontrol(bulunan.is_dir(), f"varsayilan klasor bulundu: {bulunan}")

shutil.rmtree(GECICI, ignore_errors=True)
bozuk.unlink(missing_ok=True)

print("12) Iptal (yarida kesme)")
iptal_klasor = Path(tempfile.gettempdir()) / f"iptal_{uuid.uuid4().hex[:8]}"
iptal_klasor.mkdir()
for i in range(400):
    (iptal_klasor / f"dosya_{i:03d}.jpg").write_bytes(b"\0" * 10)


class IptalSonucu:
    """25 dosyada bir 'False' donen ilerleme geri cagirmasi."""
    def __init__(self):
        self.sayac = 0

    def __call__(self, simdi, toplam, metin):
        self.sayac += 1
        return simdi < 60          # ~60 dosyadan sonra dur


iptal = IptalSonucu()
sonuc_iptal = mod.klasoru_tara(iptal_klasor, harita, iptal)
kontrol(sonuc_iptal.iptal is True, "tarama iptal edildi olarak isaretlendi")
kontrol(0 < len(sonuc_iptal.gecerli) < 400,
        f"kismi sonuc dondu ({len(sonuc_iptal.gecerli)}/400 dosya)")

tasima_ogeleri = sonuc_iptal.gecerli
iptal2 = IptalSonucu()
sonuc_iptal2 = mod.dosyalari_tasi(tasima_ogeleri, iptal_klasor, iptal2)
kontrol(sonuc_iptal2["iptal"] is True, "tasima iptal edildi olarak isaretlendi")
kontrol(0 < len(sonuc_iptal2["tasinan"]) < 400,
        f"kismi tasindi ({len(sonuc_iptal2['tasinan'])}/400)")
kontrol((iptal_klasor / "Resimler").is_dir(), "kismi tasima icin klasor olustu")

# yarida kesilen tasima geri alinabilmeli
mod.gecmise_ekle("tasindi", iptal_klasor, sonuc_iptal2["tasinan"])
kayit_iptal = mod.son_tasima_kaydi()
geri_iptal = mod.geri_al(kayit_iptal)
kontrol(geri_iptal["geri"] == len(sonuc_iptal2["tasinan"]), "kismi tasima geri alindi")
kontrol(not (iptal_klasor / "Resimler").exists(), "bos klasor temizlendi")
kontrol(len([p for p in iptal_klasor.iterdir() if p.is_file()]) == 400,
        "iptal klasoru 400 dosyaya dondu")
shutil.rmtree(iptal_klasor, ignore_errors=True)
mod.gecmis_dosyasi().unlink(missing_ok=True)

print("13) Guvenlik: var olan dosya EZILMEZ")
guv = Path(tempfile.gettempdir()) / f"guv_{uuid.uuid4().hex[:8]}"
(guv / "Resimler").mkdir(parents=True)
kontrol(guv.is_dir(), "hazirlik klasoru")

# hedefte zaten bir dosya var ve ORIJINAL icerigi farkli
(guv / "Resimler" / "rapor.pdf").write_bytes(b"ESKI VE KIYMETLI ICERIK")
# kaynakta ayni isimli baska bir dosya var
(guv / "rapor.pdf").write_bytes(b"yeni")

ogeler = [{"kaynak": guv / "rapor.pdf", "ad": "rapor.pdf",
           "kategori": "Belgeler", "uzanti": "pdf", "boyut": 4}]
sonuc_guv = mod.dosyalari_tasi(ogeler, guv)
kontrol(len(sonuc_guv["tasinan"]) == 1, "dosya tasindi")
kontrol((guv / "Belgeler" / "rapor.pdf").read_bytes() == b"yeni",
        "yeni dosya kendi yerine tasindi")
kontrol((guv / "Resimler" / "rapor.pdf").read_bytes() == b"ESKI VE KIYMETLI ICERIK",
        "MEVCUT DOSYA EZILMEDI - icerik aynen korundu")
kontrol((guv / "rapor.pdf").exists() is False, "kaynak yerinden kalkti")

# tasinamayan dosya kaybolmaz, hata olarak bildirilir
import stat as _stat
kilitli = guv / "kilitli.txt"
kilitli.write_bytes(b"KILITLI ICERIK")
og_kilitli = {"kaynak": kilitli, "ad": "kilitli.txt",
              "kategori": "Belgeler", "uzanti": "txt", "boyut": 14}
os.chmod(kilitli, _stat.S_IREAD)
sonuc_kilitli = mod.dosyalari_tasi([og_kilitli], guv)
if kilitli.exists():
    os.chmod(kilitli, _stat.S_IWRITE)      # temizlik icin kilidi ac
if sonuc_kilitli["hatali"]:
    kontrol(kilitli.is_file(), "TASINAMAYAN DOSYA KAYBOLMADI, yerinde duruyor")
    kontrol(kilitli.read_bytes() == b"KILITLI ICERIK", "iceriği bozulmadi")
    kontrol(not (guv / "Belgeler" / "kilitli.txt").exists(),
            "hedefe yarim kopyalanmadi")
else:
    kontrol((guv / "Belgeler" / "kilitli.txt").is_file(),
            "salt okunur dosya tasindi, hedefte duruyor")

shutil.rmtree(guv, ignore_errors=True)

print()
if hatalar:
    print(f"{len(hatalar)} HATA:")
    for h in hatalar:
        print("  - " + h)
    sys.exit(1)
print("TUM TESTLER BASARILI")
