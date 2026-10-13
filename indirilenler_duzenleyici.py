# -*- coding: utf-8 -*-
# Required Notice: Copyright (C) 2026  by3727265-debug
#
# Licensed under the PolyForm Noncommercial License 1.0.0
# <https://polyformproject.org/licenses/noncommercial/1.0.0>
#
# Kullanim, degistirme ve dagitma serbesttir. TICARI AMACLA SATIS YASAKTIR.
# Tam metin: LICENSE dosyasi
r"""
İndirilenler Klasörü Düzenleyici
================================
İndirilenler klasörünü dosya türlerine göre alt klasörlere ayırır.

  * Kuru çalıştırma (önizleme) varsayılan olarak AÇIK
  * Taşımadan önce onay penceresi
  * İlerleme çubuğu + canlı log
  * Son taşıma işlemini tek tıkla geri al
  * Kurallar `veri\kurallar.json` ile değiştirilebilir (exe -> Programlar vb.)

Çalıştırmak için:  baslat.bat   (konsol penceresi açmadan)
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ------------------------------------------------------------------ sabitler

UYGULAMA_ADI = "İndirilenler Düzenleyici"
SURUM = "1.0"

#: kategori adı -> o kategoriye gidecek uzantılar
VARSAYILAN_KURALLAR: dict[str, list[str]] = {
    "Programlar ve Betikler": [
        "exe", "msi", "msix", "appx", "apk", "appimage", "deb", "rpm",
        "bat", "cmd", "com", "jar", "msu", "run", "ps1", "vbs", "sh",
    ],
    "Disk Görüntüleri": ["iso", "img", "dmg", "vhd", "vhdx", "wim", "esd"],
    "Resimler": [
        "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "tif", "tiff",
        "ico", "heic", "heif", "avif", "jfif", "raw",
    ],
    "Videolar": [
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg",
        "mpeg", "ts", "m2ts", "3gp", "ogv", "vob", "rmvb", "divx",
    ],
    "Ses ve Müzik": [
        "mp3", "wav", "flac", "aac", "ogg", "oga", "m4a", "wma", "opus",
        "aiff", "aif", "mid", "midi",
    ],
    "Belgeler": ["pdf", "doc", "docx", "odt", "rtf", "txt", "epub", "mobi", "azw3"],
    "Tablolar": ["xls", "xlsx", "xlsm", "ods", "csv", "tsv", "numbers"],
    "Sunumlar": ["ppt", "pptx", "odp", "key"],
    "Çizim ve Tasarım": ["psd", "ai", "eps", "sketch", "fig", "xd"],
    "3B Modeller": ["blend", "obj", "stl", "fbx", "dae", "glb", "gltf", "3ds", "max"],
    "Fontlar": ["ttf", "otf", "woff", "woff2", "eot"],
    "Arşivler": ["zip", "rar", "7z", "tar", "gz", "tgz", "bz2", "xz", "zst", "cab", "lz4"],
    "Kod Dosyaları": [
        "py", "js", "mjs", "ts", "tsx", "jsx", "html", "htm", "css", "scss",
        "json", "xml", "yml", "yaml", "toml", "java", "c", "h", "cpp", "hpp",
        "cs", "go", "rs", "php", "rb", "swift", "kt", "lua", "sql", "ipynb",
    ],
    "Sertifikalar": ["pem", "crt", "cer", "der", "p12", "pfx", "pub"],
    "Diğer Dosyalar": [],
}

#: yarım inmiş indirmeler ve geçici dosyalar -> hiç dokunulmaz
ATLANACAK_UZANTILAR = {
    "crdownload", "part", "partial", "tmp", "temp", "download", "opdownload",
    "swp", "swo", "bak", "old", "downloads",
}

#: adı ne olursa olsun atlanacak dosyalar
ATLANACAK_ADLAR = {"desktop.ini", "thumbs.db", ".ds_store", "libraryfolder.txt"}

#: sistem dosyaları / gizli dosyalar
GIZLI_ONEK = "."

TICK = "\u2611"   # ☑
BOX = "\u2610"    # ☐


# -------------------------------------------------------------- yardımcılar

def uygulama_klasoru() -> Path:
    """Betiğin bulunduğu klasör (paketlenmişse exe klasörü)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def veri_klasoru() -> Path:
    """Ayar ve geçmiş dosyalarının tutulduğu klasör."""
    aday = uygulama_klasoru() / "veri"
    try:
        aday.mkdir(parents=True, exist_ok=True)
        probe = aday / ".yazma_testi"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return aday
    except OSError:
        yedek = Path(os.environ.get("APPDATA", Path.home())) / "IndirilenlerDuzenleyici"
        yedek.mkdir(parents=True, exist_ok=True)
        return yedek


def kurallar_hedefi() -> Path:
    """Kullanıcı kurallarının yazılacağı yer. Bütün veriler veri/ içinde."""
    return veri_klasoru() / "kurallar.json"


def kurallar_dosyasi() -> Path:
    """
    Kuralların okunacağı dosya.

    Yeni yer veri/kurallar.json. Eskiden uygulama klasörüne yazılıyordu;
    orada bir dosya varsa (eski sürümden kalmış olabilir) okunmaya devam eder.
    """
    yeni = kurallar_hedefi()
    if yeni.is_file():
        return yeni
    eski = uygulama_klasoru() / "kurallar.json"
    return eski if eski.is_file() else yeni


def ayar_dosyasi() -> Path:
    return veri_klasoru() / "ayarlar.json"


def gecmis_dosyasi() -> Path:
    return veri_klasoru() / "gecmis.jsonl"


def varsayilan_indirilenler_klasoru() -> Path:
    """OneDrive yönlendirmesi varsa onu, yoksa klasik Downloads klasörünü bulur."""
    adaylar = []
    onedrive = os.environ.get("OneDrive") or os.environ.get("OneDriveConsumer")
    if onedrive:
        adaylar.append(Path(onedrive) / "Downloads")
        adaylar.append(Path(onedrive) / "İndirilenler")
    profil = os.environ.get("USERPROFILE")
    if profil:
        adaylar.append(Path(profil) / "Downloads")
        adaylar.append(Path(profil) / "İndirilenler")
    for aday in adaylar:
        if aday.is_dir():
            return aday
    return Path.home()


def klasoru_ac(yol: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(yol))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(yol)])
        else:
            subprocess.Popen(["xdg-open", str(yol)])
    except OSError:
        pass


def boyut_metni(bayt: int) -> str:
    birim = ["B", "KB", "MB", "GB", "TB"]
    deger = float(bayt)
    for birim_ad in birim:
        if deger < 1024 or birim_ad == birim[-1]:
            if birim_ad == "B":
                return f"{int(deger)} {birim_ad}"
            return f"{deger:.1f} {birim_ad}"
        deger /= 1024
    return f"{bayt} B"


def benzersiz_hedef(klasor: Path, ad: str) -> Path:
    """Aynı isimli dosya varsa ' (1)', ' (2)' ekleyerek boş ad bulur."""
    hedef = klasor / ad
    if not hedef.exists():
        return hedef
    govde = Path(ad).stem
    sonlu = Path(ad).suffix
    sayac = 1
    while True:
        aday = klasor / f"{govde} ({sayac}){sonlu}"
        if not aday.exists():
            return aday
        sayac += 1


# ------------------------------------------------------------ kural katmanı

def varsayilan_kural_haritasi() -> tuple[dict[str, str], list[str]]:
    """(uzanti -> kategori, kategori sırası) döner."""
    sira = list(VARSAYILAN_KURALLAR.keys())
    harita: dict[str, str] = {}
    for kategori, uzantilar in VARSAYILAN_KURALLAR.items():
        for uzanti in uzantilar:
            harita[uzanti] = kategori
    return harita, sira


def kurallari_yukle() -> tuple[dict[str, str], list[str]]:
    """kurallar.json varsa onu, yoksa varsayılanları kullanır."""
    dosya = kurallar_dosyasi()
    if not dosya.is_file():
        return varsayilan_kural_haritasi()
    try:
        veri = json.loads(dosya.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return varsayilan_kural_haritasi()

    sira = [k for k in veri if isinstance(veri[k], list)]
    harita: dict[str, str] = {}
    for kategori, uzantilar in veri.items():
        if not isinstance(uzantilar, list):
            continue
        for uzanti in uzantilar:
            if isinstance(uzanti, str):
                harita[uzanti.strip().lstrip(".").lower()] = kategori
    if not harita:
        return varsayilan_kural_haritasi()
    return harita, sira


def kurallari_kaydet(harita: dict[str, str], sira: list[str]) -> None:
    """Haritayı kurallar.json biçimine çevirip kaydeder."""
    gruplar: dict[str, list[str]] = {k: [] for k in sira}
    for uzanti, kategori in harita.items():
        gruplar.setdefault(kategori, []).append(uzanti)
    for uzantilar in gruplar.values():
        uzantilar.sort()
    kurallar_hedefi().write_text(
        json.dumps(gruplar, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# -------------------------------------------------------------- tarama katmanı

class TaramaSonucu:
    def __init__(self) -> None:
        self.gecerli: list[dict] = []          # taşınmaya aday dosyalar
        self.atlanan: list[tuple[str, str]] = []   # (ad, neden)
        self.klasor_sayisi = 0
        self.toplam_boyut = 0
        self.iptal = False                     # kullanıcı işlemi yarıda kesti mi


def klasoru_tara(klasor: Path, harita: dict[str, str],
                 ilerleme=None) -> TaramaSonucu:
    """Klasörün üst düzeyindeki dosyaları uzantılarına göre sınıflandırır."""
    sonuc = TaramaSonucu()
    varsayilan = harita.get("__diger__", "Diğer Dosyalar")

    try:
        girdiler = list(os.scandir(klasor))
    except OSError as hata:
        raise RuntimeError(f"Klasör okunamadı: {hata}") from hata

    toplam = len(girdiler)
    for sira, girdi in enumerate(girdiler, start=1):
        if ilerleme is not None and (sira % 25 == 0 or sira == toplam):
            if ilerleme(sira, toplam, f"Taranıyor... {sira}/{toplam}") is False:
                sonuc.iptal = True
                break

        ad = girdi.name
        if girdi.is_dir(follow_symlinks=False):
            sonuc.klasor_sayisi += 1
            sonuc.atlanan.append((ad, "klasör"))
            continue

        if ad.lower() in ATLANACAK_ADLAR or ad.startswith("~$") or ad.startswith(GIZLI_ONEK):
            sonuc.atlanan.append((ad, "sistem/gizli"))
            continue

        uzanti = Path(ad).suffix.lstrip(".").lower()
        if uzanti in ATLANACAK_UZANTILAR:
            sonuc.atlanan.append((ad, "yarım indirme/geçici"))
            continue

        kategori = harita.get(uzanti, varsayilan)
        try:
            boyut = girdi.stat(follow_symlinks=False).st_size
        except OSError:
            boyut = 0

        sonuc.gecerli.append({
            "kaynak": Path(girdi.path),
            "ad": ad,
            "kategori": kategori,
            "uzanti": uzanti or "(uzantisiz)",
            "boyut": boyut,
        })
        sonuc.toplam_boyut += boyut

    return sonuc


def tasima_hedefi(kaynak: Path, kategori: str, kok: Path) -> Path:
    return kok / kategori / kaynak.name


def dosyalari_tasi(ogeler: list[dict], kok: Path,
                   ilerleme=None) -> dict:
    """Seçili dosyaları taşır, çakışmalarda numara ekler."""
    sonuc = {"tasinan": [], "hatali": [], "boyut": 0, "iptal": False}
    toplam = len(ogeler)
    for sira, oge in enumerate(ogeler, start=1):
        if ilerleme is not None:
            if ilerleme(sira, toplam, f"Taşınıyor: {oge['ad']}") is False:
                sonuc["iptal"] = True
                break
        kaynak: Path = oge["kaynak"]
        hedef = benzersiz_hedef(tasima_hedefi(kaynak, oge["kategori"], kok).parent,
                                kaynak.name)
        try:
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(kaynak), str(hedef))
        except (OSError, shutil.Error) as hata:
            sonuc["hatali"].append((kaynak.name, str(hata)))
            continue
        sonuc["tasinan"].append({"kaynak": str(kaynak), "hedef": str(hedef),
                                 "kategori": oge["kategori"], "ad": kaynak.name})
        sonuc["boyut"] += oge.get("boyut", 0)
    return sonuc


def gecmise_ekle(islem: str, kok: Path, kayitlar: list[dict]) -> None:
    kayit = {
        "zaman": datetime.now().isoformat(timespec="seconds"),
        "islem": islem,
        "klasor": str(kok),
        "dosyalar": kayitlar,
    }
    try:
        with gecmis_dosyasi().open("a", encoding="utf-8") as dosya:
            dosya.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except OSError:
        pass


def son_tasima_kaydi() -> dict | None:
    """Geri alınacak son başarılı taşıma kaydını bulur."""
    dosya = gecmis_dosyasi()
    if not dosya.is_file():
        return None
    son: dict | None = None
    try:
        with dosya.open("r", encoding="utf-8") as akis:
            for satir in akis:
                satir = satir.strip()
                if not satir:
                    continue
                kayit = json.loads(satir)
                if kayit.get("islem") == "tasindi":
                    son = kayit
    except (OSError, json.JSONDecodeError):
        return None
    return son


def geri_al(kayit: dict, ilerleme=None) -> dict:
    """Taşınmış dosyaları eski yerine geri koyar, boş kalan klasörleri temizler."""
    sonuc = {"geri": 0, "eksik": [], "hatali": [], "silinen_klasor": []}
    dosyalar = kayit.get("dosyalar", [])
    kok = Path(kayit.get("klasor", "."))
    toplam = len(dosyalar)
    dokunulan: set[Path] = set()

    for sira, kaydi in enumerate(dosyalar, start=1):
        if ilerleme is not None:
            ilerleme(sira, toplam, f"Geri alınıyor: {kaydi.get('ad', '')}")
        kaynak = Path(kaydi["hedef"])
        hedef = Path(kaydi["kaynak"])
        if not kaynak.exists():
            sonuc["eksik"].append(kaydi.get("ad", kaynak.name))
            continue
        try:
            hedef.parent.mkdir(parents=True, exist_ok=True)
            yeni = benzersiz_hedef(hedef.parent, hedef.name)
            shutil.move(str(kaynak), str(yeni))
        except (OSError, shutil.Error) as hata:
            sonuc["hatali"].append((kaydi.get("ad", kaynak.name), str(hata)))
            continue
        dokunulan.add(kaynak.parent)
        sonuc["geri"] += 1

    # yalnızca bizim oluşturduğumuz ve şimdi boş kalan klasörleri kaldır
    for klasor in dokunulan:
        try:
            if klasor.parent != kok or not klasor.is_dir():
                continue
            if any(klasor.iterdir()):
                continue
            klasor.rmdir()
            sonuc["silinen_klasor"].append(klasor.name)
        except OSError:
            pass

    return sonuc


# ------------------------------------------------------------------- arayüz

class Uygulama(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{UYGULAMA_ADI}  v{SURUM}")
        self.minsize(940, 620)
        self.geometry("1040x700")

        # durum
        self.tarama: TaramaSonucu | None = None
        self.secili: dict[str, bool] = {}          # kategori -> taşınacak mı
        self.klasor_yoğunluk: dict[str, int] = {}  # kategori -> dosya sayısı
        self.klasor_boyut: dict[str, int] = {}
        self.sira_no: dict[str, int] = {}
        self.plan: list[dict] = []
        self.kuyruk: queue.Queue = queue.Queue()
        self.calisiyor = False
        self.son_kayit: dict | None = None
        self.iptal_edildi = False
        self.sirali_alan = "adet"
        self.sirali_yon = True

        self.kurallar, self.kategori_sirasi = kurallari_yukle()

        self._ayarlari_yukle()
        self._arayuzu_kur()
        self._menu_kur()
        self.protocol("WM_DELETE_WINDOW", self._kapat)
        self.after(100, self._kuyruk_isle)
        self.after(300, self._otomatik_tara)
        self.bind("<F5>", lambda _e: self.tara())
        self.bind("<Control-o>", lambda _e: self.klasor_sec())

    # ------------------------------------------------------------ ayarlar

    def _ayarlari_yukle(self) -> None:
        veri = {
            "klasor": str(varsayilan_indirilenler_klasoru()),
            "kuru_calistirma": True,
            "sonra_ac": True,
            "sutun": 1.15,
        }
        try:
            kayitli = json.loads(ayar_dosyasi().read_text(encoding="utf-8"))
            if isinstance(kayitli, dict):
                veri.update({k: v for k, v in kayitli.items() if k in veri})
        except (OSError, json.JSONDecodeError):
            pass
        self.klasor_var = tk.StringVar(value=veri["klasor"])
        self.kuru_var = tk.BooleanVar(value=veri["kuru_calistirma"])
        self.sonra_ac_var = tk.BooleanVar(value=veri["sonra_ac"])
        self.geometri_var = tk.DoubleVar(value=veri["sutun"])

    def _ayarlari_kaydet(self) -> None:
        veri = {
            "klasor": self.klasor_var.get(),
            "kuru_calistirma": self.kuru_var.get(),
            "sonra_ac": self.sonra_ac_var.get(),
            "sutun": self.geometri_var.get(),
        }
        try:
            ayar_dosyasi().write_text(
                json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError:
            pass

    # ----------------------------------------------------------- arayüz kur

    def _arayuzu_kur(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # --- üst: klasör seçimi
        ust = ttk.Frame(self, padding=(12, 12, 12, 6))
        ust.grid(row=0, column=0, sticky="ew")
        ust.columnconfigure(1, weight=1)

        ttk.Label(ust, text="Klasör:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.girdi = ttk.Entry(ust, textvariable=self.klasor_var, font=("Segoe UI", 10))
        self.girdi.grid(row=0, column=1, sticky="ew")
        self.girdi.bind("<Return>", lambda _e: self.tara())
        ttk.Button(ust, text="Gözat...", command=self.klasor_sec).grid(
            row=0, column=2, padx=(8, 0))
        ttk.Button(ust, text="Aç", command=lambda: klasoru_ac(self.klasor_yolu)
                   ).grid(row=0, column=3, padx=(6, 0))

        # --- orta: düğmeler
        ara = ttk.Frame(self, padding=(12, 0, 12, 6))
        ara.grid(row=1, column=0, sticky="ew")
        ara.columnconfigure(5, weight=1)

        self.tara_btn = ttk.Button(ara, text="Tara  (F5)", command=self.tara)
        self.tara_btn.grid(row=0, column=0, padx=(0, 6))
        self.duzenle_btn = ttk.Button(ara, text="Düzenle", command=self.duzenle,
                                      state="disabled")
        self.duzenle_btn.grid(row=0, column=1, padx=6)
        self.geri_btn = ttk.Button(ara, text="Son taşımayı geri al",
                                   command=self.geri_al, state="disabled")
        self.geri_btn.grid(row=0, column=2, padx=6)
        self.iptal_btn = ttk.Button(ara, text="İptal", command=self.durdur,
                                    state="disabled")
        self.iptal_btn.grid(row=0, column=3, padx=6)

        ttk.Checkbutton(ara, text="Kuru çalıştırma (sadece önizle)",
                        variable=self.kuru_var, command=self.duzenle_metin_guncelle
                        ).grid(row=0, column=5, sticky="e")
        ttk.Checkbutton(ara, text="Bitince klasörü aç", variable=self.sonra_ac_var
                        ).grid(row=0, column=6, sticky="e", padx=(12, 0))

        # --- ilerleme
        self.ilerleme = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.ilerleme.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 0))
        self.durum = ttk.Label(self, text="Hazır", anchor="w", padding=(12, 4))
        self.durum.grid(row=2, column=0, sticky="ew")

        # --- gövde: tablo + log
        govde = ttk.PanedWindow(self, orient="horizontal")
        govde.grid(row=3, column=0, sticky="nsew", padx=12, pady=8)

        sol = ttk.Frame(govde)
        sol.rowconfigure(0, weight=1)
        sol.columnconfigure(0, weight=1)

        self.tablo = ttk.Treeview(
            sol,
            columns=("sec", "klasor", "adet", "boyut", "ornek", "durum"),
            show="headings", selectmode="browse",
        )
        basliklar = {
            "sec": ("", 34, "center"),
            "klasor": ("Klasör", 190, "w"),
            "adet": ("Dosya", 70, "center"),
            "boyut": ("Boyut", 90, "e"),
            "ornek": ("Örnek dosyalar", 260, "w"),
            "durum": ("Durum", 90, "center"),
        }
        for ad, (baslik, genislik, hiza) in basliklar.items():
            self.tablo.heading(ad, text=baslik,
                               command=lambda a=ad: self.sirala(a))
            self.tablo.column(ad, width=genislik, anchor=hiza,
                              stretch=(ad in ("ornek", "klasor")))
        self.tablo.grid(row=0, column=0, sticky="nsew")

        kaydirma = ttk.Scrollbar(sol, orient="vertical", command=self.tablo.yview)
        kaydirma.grid(row=0, column=1, sticky="ns")
        self.tablo.configure(yscrollcommand=kaydirma.set)

        self.tablo.tag_configure("secili", background="#dce9ff")
        self.tablo.tag_configure("pasif", foreground="#9a9a9a")
        self.tablo.tag_configure("diger", foreground="#7a5c00")
        self.tablo.bind("<Button-1>", self.tikla)
        self.tablo.bind("<Double-1>", self.cift_tikla)
        self.tablo.bind("<Return>", self.cift_tikla)

        govde.add(sol, weight=3)

        sag = ttk.Frame(govde)
        sag.rowconfigure(0, weight=1)
        sag.columnconfigure(0, weight=1)
        self.log = tk.Text(sag, height=10, wrap="word", state="disabled",
                           font=("Consolas", 9), background="#fbfbfb",
                           relief="flat", borderwidth=1)
        self.log.grid(row=0, column=0, sticky="nsew")
        log_kaydirma = ttk.Scrollbar(sag, orient="vertical", command=self.log.yview)
        log_kaydirma.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=log_kaydirma.set)

        govde.add(sag, weight=2)

        # --- alt
        alt = ttk.Frame(self, padding=(12, 0, 12, 10))
        alt.grid(row=4, column=0, sticky="ew")
        alt.columnconfigure(2, weight=1)
        self.ozet = ttk.Label(alt, text="Henüz taranmadı.", anchor="w")
        self.ozet.grid(row=0, column=0, sticky="w")
        ttk.Button(alt, text="Logu kaydet", command=self.logu_kaydet).grid(
            row=0, column=3, padx=(8, 0))
        ttk.Button(alt, text="Yardım", command=self.yardim).grid(
            row=0, column=4, padx=(6, 0))

    def _menu_kur(self) -> None:
        menubar = tk.Menu(self, tearoff=0)

        dosya = tk.Menu(menubar, tearoff=0)
        dosya.add_command(label="Klasör seç...", accelerator="Ctrl+O",
                          command=self.klasor_sec)
        dosya.add_separator()
        dosya.add_command(label="Logu kaydet...", command=self.logu_kaydet)
        dosya.add_command(label="Geçmişi metin olarak aç",
                          command=lambda: klasoru_ac(veri_klasoru()))
        dosya.add_separator()
        dosya.add_command(label="Kapat", command=self._kapat)
        menubar.add_cascade(label="Dosya", menu=dosya)

        duzenle = tk.Menu(menubar, tearoff=0)
        duzenle.add_command(label="Tara (F5)", command=self.tara)
        duzenle.add_command(label="Düzenle", command=self.duzenle)
        duzenle.add_command(label="Son taşımayı geri al", command=self.geri_al)
        menubar.add_cascade(label="Düzenle", menu=duzenle)

        secenek = tk.Menu(menubar, tearoff=0)
        secenek.add_command(label="Kuralları düzenle (kurallar.json)",
                            command=self.kurallari_duzenle)
        secenek.add_command(label="Kuralları yeniden yükle", command=self.kurallari_yenile)
        secenek.add_separator()
        secenek.add_command(label="Tümünü seç", command=lambda: self.tumunu_sec(True))
        secenek.add_command(label="Tümünü bırak", command=lambda: self.tumunu_sec(False))
        menubar.add_cascade(label="Seçenekler", menu=secenek)

        yardim = tk.Menu(menubar, tearoff=0)
        yardim.add_command(label="Kullanım", command=self.yardim)
        yardim.add_command(label="Hakkında", command=self.hakkinda)
        menubar.add_cascade(label="Yardım", menu=yardim)

        self.config(menu=menubar)

    # -------------------------------------------------------------- olaylar

    @property
    def klasor_yolu(self) -> Path:
        """Kutuya yapıştırılan yolu temizlenmiş hâlde döner."""
        return Path(self.klasor_var.get().strip().strip('"'))

    def _kapat(self) -> None:
        self._ayarlari_kaydet()
        self.destroy()

    def durdur(self) -> None:
        """Arka plandaki işlemi gerçekten keser."""
        if not self.calisiyor:
            return
        self.iptal_edildi = True
        self.iptal_btn.configure(state="disabled")
        self.durum.configure(text="İptal ediliyor, lütfen bekleyin...")

    def klasor_sec(self) -> None:
        secilen = filedialog.askdirectory(
            title="Düzenlenecek klasörü seç",
            initialdir=self.klasor_var.get() or str(Path.home()),
            mustexist=True,
        )
        if secilen:
            self.klasor_var.set(secilen)
            self.tara()

    def _otomatik_tara(self) -> None:
        if self.klasor_yolu.is_dir():
            self.tara()

    # -------------------------------------------------------------- tarama

    def tara(self) -> None:
        if self.calisiyor:
            return
        klasor = self.klasor_yolu
        if not klasor.is_dir():
            messagebox.showwarning("Klasör bulunamadı",
                                   f"Şu klasör yok:\n{klasor}\n\nGözat ile seçebilirsin.")
            return
        self._ayarlari_kaydet()
        self.tablo.delete(*self.tablo.get_children())
        self.log_temizle()
        self.log_yaz(f"Taranan klasör: {klasor}")
        self._baslat(
            isim="tara",
            islev=lambda: klasoru_tara(klasor, self.kurallar, self._ilerleme_guncelle),
            basari=lambda sonuc: self._tarama_bitti(sonuc),
        )

    def _tarama_bitti(self, sonuc: TaramaSonucu) -> None:
        self.tarama = sonuc
        gruplar: dict[str, list[dict]] = {}
        for oge in sonuc.gecerli:
            gruplar.setdefault(oge["kategori"], []).append(oge)

        self.klasor_yoğunluk.clear()
        self.klasor_boyut.clear()
        self.secili.clear()

        for kategori, ogeler in gruplar.items():
            self.klasor_yoğunluk[kategori] = len(ogeler)
            self.klasor_boyut[kategori] = sum(o["boyut"] for o in ogeler)
            # "Diğer" ve tahmin edilemeyen gruplar varsayılan kapalı
            self.secili[kategori] = kategori != "Diğer Dosyalar"

        self._tabloyu_doldur()
        self.duzenle_btn.configure(state="normal")
        self.geri_btn.configure(state="normal" if son_kayit_var() else "disabled")

        toplam_adet = len(sonuc.gecerli)
        secili_adet = sum(len(gruplar[k]) for k, v in self.secili.items() if v)
        atlanan = len(sonuc.atlanan)
        self.log_yaz(
            f"Bitti. {toplam_adet} dosya bulundu, {secili_adet} dosya taşınmaya hazır, "
            f"{atlanan} öğe atlandı ({sonuc.klasor_sayisi} klasör dahil)."
        )
        if sonuc.iptal:
            self.log_yaz("Tarama yarıda kesildi; taramak için tekrar F5'e basın.")
            self.durum.configure(text="Tarama iptal edildi")
            self.ilerleme.configure(value=0)
        else:
            self.durum.configure(text="Tarama tamamlandı — düzenlemek için 'Düzenle'ye bas")
        self.ozet.configure(
            text=f"{toplam_adet} dosya · {boyut_metni(sonuc.toplam_boyut)} · "
                 f"{secili_adet} dosya seçili · {atlanan} öğe atlandı"
        )
        self._ozet_guncelle()

    def _tabloyu_doldur(self) -> None:
        self.tablo.delete(*self.tablo.get_children())
        if not self.klasor_yoğunluk:
            return
        sira = {k: i for i, k in enumerate(self.kategori_sirasi)}
        satirlar = sorted(self.klasor_yoğunluk.keys(),
                          key=lambda k: sira.get(k, 999))
        for kategori in satirlar:
            self._satir_ekle(kategori)
        self.sirala(self.sirali_alan)

    def _satir_ekle(self, kategori: str) -> None:
        adet = self.klasor_yoğunluk.get(kategori, 0)
        boyut = self.klasor_boyut.get(kategori, 0)
        secili = self.secili.get(kategori, False)
        ornekler = [o["ad"] for o in (self.tarama.gecerli if self.tarama else [])
                    if o["kategori"] == kategori][:3]
        etiketler = []
        if self.duzenle_btn["state"] != "disabled" and adet:
            etiketler.append("secili" if secili else "pasif")
        if kategori == "Diğer Dosyalar":
            etiketler.append("diger")
        self.tablo.insert(
            "", "end", iid=kategori,
            values=(TICK if secili else BOX, kategori, adet,
                    boyut_metni(boyut),
                    ", ".join(ornekler) + (" …" if adet > len(ornekler) else ""),
                    "seçilecek" if secili else "kalacak"),
            tags=tuple(etiketler),
        )

    def _satirlari_yenile(self) -> None:
        for kategori in self.klasor_yoğunluk:
            if self.tablo.exists(kategori):
                degerler = list(self.tablo.item(kategori, "values"))
                degerler[0] = TICK if self.secili.get(kategori) else BOX
                degerler[5] = "seçilecek" if self.secili.get(kategori) else "kalacak"
                etiketler = [t for t in ("secili", "pasif", "diger")
                             if t in self.tablo.item(kategori, "tags")]
                if kategori == "Diğer Dosyalar" and "diger" not in etiketler:
                    etiketler.append("diger")
                self.tablo.item(kategori, values=degerler, tags=tuple(etiketler))
            else:
                self._satir_ekle(kategori)

    def tikla(self, olay) -> None:
        if olay.x < 40 and self.tablo.identify_region(olay.x, olay.y) == "cell":
            satir = self.tablo.identify_row(olay.y)
            if satir:
                self.secili[satir] = not self.secili.get(satir, False)
                self._satirlari_yenile()
                self._ozet_guncelle()
                return
        return None

    def cift_tikla(self, _olay=None) -> None:
        secili = self.tablo.selection()
        if secili:
            klasoru_ac(self.klasor_yolu / secili[0])

    def sirala(self, alan: str) -> None:
        if alan == "sec":
            return
        if self.sirali_alan == alan:
            self.sirali_yon = not self.sirali_yon
        else:
            self.sirali_alan = alan
            self.sirali_yon = False

        def anahtar(iid: str):
            if alan == "adet":
                return self.klasor_yoğunluk.get(iid, 0)
            if alan == "boyut":
                return self.klasor_boyut.get(iid, 0)
            return iid.casefold()

        cocuklar = list(self.tablo.get_children())
        sirali = sorted(cocuklar, key=anahtar, reverse=self.sirali_yon)
        for konum, iid in enumerate(sirali):
            self.tablo.move(iid, "", konum)

    def tumunu_sec(self, deger: bool) -> None:
        for kategori in self.klasor_yoğunluk:
            if deger or kategori != "Diğer Dosyalar":
                self.secili[kategori] = deger
        self._satirlari_yenile()
        self._ozet_guncelle()

    def _ozet_guncelle(self) -> None:
        if not self.tarama:
            return
        adet = sum(1 for o in self.tarama.gecerli if self.secili.get(o["kategori"]))
        boyut = sum(o["boyut"] for o in self.tarama.gecerli
                    if self.secili.get(o["kategori"]))
        kategori_sayisi = sum(1 for v in self.secili.values() if v)
        self.ozet.configure(
            text=f"Seçili: {kategori_sayisi} kategori · {adet} dosya · {boyut_metni(boyut)}"
        )

    # -------------------------------------------------------------- düzenle

    def duzenle_metin_guncelle(self) -> None:
        if self.kuru_var.get():
            self.duzenle_btn.configure(text="Önizle")
        else:
            self.duzenle_btn.configure(text="Düzenle")

    def duzenle(self) -> None:
        if self.calisiyor or not self.tarama:
            return
        secili_ogeler = [o for o in self.tarama.gecerli if self.secili.get(o["kategori"])]
        if not secili_ogeler:
            messagebox.showinfo("Seçim yok",
                                "Taşınacak dosya seçmediniz.\n\n"
                                "Tablodaki satırın başındaki kutucuğa tıklayarak "
                                "kategorileri işaretleyin.")
            return

        kuru = self.kuru_var.get()
        gruplar: dict[str, list[dict]] = {}
        for oge in secili_ogeler:
            gruplar.setdefault(oge["kategori"], []).append(oge)

        if kuru:
            self.log_temizle()
            self.log_yaz("KURU ÇALIŞTIRMA — hiçbir dosya taşınmadı.\n")
            for kategori in sorted(gruplar, key=lambda k: -len(gruplar[k])):
                ogeler = gruplar[kategori]
                boyut = sum(o["boyut"] for o in ogeler)
                self.log_yaz(f"\n[{kategori}]  {len(ogeler)} dosya · {boyut_metni(boyut)}")
                for oge in ogeler[:12]:
                    self.log_yaz(f"    {oge['ad']}")
                if len(ogeler) > 12:
                    self.log_yaz(f"    … ve {len(ogeler) - 12} dosya daha")
            self.durum.configure(text="Önizleme tamamlandı — hiçbir dosya taşınmadı")
            messagebox.showinfo(
                "Önizleme",
                f"{len(secili_ogeler)} dosya, {len(gruplar)} klasöre taşınacak.\n\n"
                "Sağdaki logda ayrıntıları görebilirsiniz.\n"
                "Gerçekten taşımak için 'Kuru çalıştırma' işaretini kaldırıp "
                "'Düzenle'ye basın.")
            return

        # gerçek taşıma
        toplam = len(secili_ogeler)
        boyut = sum(o["boyut"] for o in secili_ogeler)
        kok = self.klasor_yolu          # Tk değişkeni yalnızca ana iş parçacığında okunur
        cevap = messagebox.askyesno(
            "Onay",
            f"{toplam} dosya ({boyut_metni(boyut)}) taşınacak.\n\n"
            f"Klasör: {kok}\n\n"
            "İşlem 'Dosya > Son taşımayı geri al' ile geri alınabilir.\n"
            "Devam edilsin mi?",
            icon="question",
        )
        if not cevap:
            return

        self.log_temizle()
        self.log_yaz(f"Taşınıyor: {toplam} dosya → {len(gruplar)} klasör")
        self._baslat(
            isim="tasima",
            islev=lambda: dosyalari_tasi(secili_ogeler,
                                        kok,
                                        self._ilerleme_guncelle),
            basari=lambda sonuc: self._tasima_bitti(sonuc, toplam),
        )

    def _tasima_bitti(self, sonuc: dict, beklenen: int) -> None:
        tasinan = sonuc["tasinan"]
        if tasinan:
            gecmise_ekle("tasindi", self.klasor_yolu, tasinan)
            gecmisi = {}
            for kaydi in tasinan:
                gecmisi[kaydi["kategori"]] = gecmisi.get(kaydi["kategori"], 0) + 1
            self.log_yaz("\nÖzet:")
            for kategori, adet in sorted(gecmisi.items(), key=lambda kv: -kv[1]):
                self.log_yaz(f"    {kategori:<22} {adet} dosya")
            self.geri_btn.configure(state="normal")

        self.log_yaz(f"\nTamamlandı: {len(tasinan)}/{beklenen} dosya taşındı.")
        if sonuc.get("iptal"):
            self.log_yaz("İşlem iptal edildi; o ana kadar taşınanlar geri alınabilir.")
        if sonuc["hatali"]:
            self.log_yaz(f"{len(sonuc['hatali'])} dosya taşınamadı:")
            for ad, hata in sonuc["hatali"][:10]:
                self.log_yaz(f"    ! {ad}: {hata}")

        self.durum.configure(text=f"{len(tasinan)} dosya taşındı."
                                 + (" (iptal edildi)" if sonuc.get("iptal") else ""))
        if self.sonra_ac_var.get():
            klasoru_ac(self.klasor_yolu)
        self.after(200, self.tara)

    # ------------------------------------------------------------ geri alma

    def geri_al(self) -> None:
        if self.calisiyor:
            return
        kayit = son_tasima_kaydi()
        if not kayit:
            messagebox.showinfo("Geri alınacak işlem yok",
                                "Bu klasör için kayıtlı bir taşıma işlemi bulunamadı.")
            self.geri_btn.configure(state="disabled")
            return
        zaman = kayit.get("zaman", "?")
        cevap = messagebox.askyesno(
            "Geri al",
            f"{zaman} tarihli taşıma geri alınacak.\n"
            f"{len(kayit.get('dosyalar', []))} dosya eski yerine dönecek.\n\nDevam edilsin mi?",
            icon="question",
        )
        if not cevap:
            return
        self.log_temizle()
        self.log_yaz(f"Geri alınıyor ({zaman})...")
        self._baslat(
            isim="geri",
            islev=lambda: geri_al(kayit, self._ilerleme_guncelle),
            basari=self._geri_al_bitti,
        )

    def _geri_al_bitti(self, sonuc: dict) -> None:
        self.log_yaz(f"\n{sonuc['geri']} dosya eski yerine döndü.")
        if sonuc["silinen_klasor"]:
            self.log_yaz(f"{len(sonuc['silinen_klasor'])} bos klasor kaldirildi: "
                         + ", ".join(sonuc["silinen_klasor"]))
        if sonuc["eksik"]:
            self.log_yaz(f"{len(sonuc['eksik'])} dosya artık yok (taşınmamış):")
            for ad in sonuc["eksik"][:10]:
                self.log_yaz(f"    - {ad}")
        if sonuc["hatali"]:
            self.log_yaz(f"{len(sonuc['hatali'])} dosyada hata oluştu.")
            for ad, hata in sonuc["hatali"][:10]:
                self.log_yaz(f"    ! {ad}: {hata}")
        self.durum.configure(text=f"{sonuc['geri']} dosya geri alındı.")
        if self.sonra_ac_var.get():
            klasoru_ac(self.klasor_yolu)
        self.after(200, self.tara)

    # ---------------------------------------------------------- arka plan

    def _baslat(self, isim: str, islev, basari) -> None:
        """Arka plan işini başlatır. Tk'ye yalnızca ana iş parçacığı dokunur."""
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("Arayüz güncellemeleri ana iş parçacığında yapılmalı")
        self.calisiyor = True
        self.iptal_edildi = False
        self.tara_btn.configure(state="disabled")
        self.duzenle_btn.configure(state="disabled")
        self.geri_btn.configure(state="disabled")
        self.iptal_btn.configure(state="normal")
        self.ilerleme.configure(mode="determinate", value=0)

        def dolgu():
            try:
                sonuc = islev()
            except Exception as hata:  # noqa: BLE001
                self.kuyruk.put(("hata", f"{type(hata).__name__}: {hata}\n"
                                          f"{traceback.format_exc()}"))
                return
            self.kuyruk.put(("bitti", (isim, sonuc, basari)))

        threading.Thread(target=dolgu, daemon=True).start()

    def _ilerleme_guncelle(self, simdi: int, toplam: int, metin: str) -> bool:
        """Arka plan iş parçacığından çağrılır. False dönerse işlem durur."""
        if self.iptal_edildi:
            return False
        self.kuyruk.put(("ilerleme", (simdi, toplam, metin)))
        return True

    def _kuyruk_isle(self) -> None:
        try:
            while True:
                tur, veri = self.kuyruk.get_nowait()
                if tur == "ilerleme":
                    simdi, toplam, metin = veri
                    yuzde = (simdi / toplam * 100) if toplam else 100
                    self.ilerleme.configure(value=yuzde)
                    self.durum.configure(text=f"{metin}  ({yuzde:.0f}%)")
                elif tur == "bitti":
                    isim, sonuc, basari = veri
                    self.calisiyor = False
                    self.ilerleme.configure(value=100)
                    self.tara_btn.configure(state="normal")
                    self.duzenle_btn.configure(state="normal")
                    self.iptal_btn.configure(state="disabled")
                    if isim == "tara":
                        self.duzenle_btn.configure(state="normal")
                    try:
                        basari(sonuc)
                    except Exception as hata:  # noqa: BLE001
                        self.log_yaz(f"Hata: {hata}")
                        messagebox.showerror("Hata", str(hata))
                elif tur == "hata":
                    self.calisiyor = False
                    self.ilerleme.configure(value=0)
                    self.tara_btn.configure(state="normal")
                    self.duzenle_btn.configure(state="normal")
                    self.iptal_btn.configure(state="disabled")
                    self.durum.configure(text="Hata oluştu")
                    self.log_yaz(str(veri))
                    messagebox.showerror("İşlem hatası", str(veri).splitlines()[0])
        except queue.Empty:
            pass
        self.after(80, self._kuyruk_isle)

    # ------------------------------------------------------------------ log

    def log_yaz(self, metin: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", metin + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def log_temizle(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def logu_kaydet(self) -> None:
        """Logu veri/ klasörüne yazar; dışarıda hiçbir dosya bırakmaz."""
        kayit = self.log.get("1.0", "end-1c")
        damga = datetime.now().strftime("%Y-%m-%d_%H-%M")
        hedef = veri_klasoru() / f"log_{damga}.txt"
        try:
            hedef.write_text(kayit, encoding="utf-8")
        except OSError as hata:
            messagebox.showerror("Kaydedilemedi", str(hata))
            return
        self.log_yaz(f"\nLog kaydedildi: {hedef}")
        messagebox.showinfo("Log kaydedildi", f"{hedef}\n\nBütün veriler "
                            "veri\\ klasöründe tutulur.")

    # -------------------------------------------------------------- seçenek

    def kurallari_duzenle(self) -> None:
        dosya = kurallar_dosyasi()
        if not dosya.is_file():
            kurallari_kaydet(self.kurallar, self.kategori_sirasi)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(dosya))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(dosya)])
        except OSError as hata:
            messagebox.showerror("Açılamadı", str(hata))
            return
        messagebox.showinfo(
            "Kurallar",
            "JSON dosyası Not Defteri'nde açıldı.\n\n"
            'Örnek:  "Resimler": ["jpg", "png"]\n\n'
            "Kaydedip kapatın, ardından 'Seçenekler > Kuralları yeniden yükle' "
            "menüsünü kullanın.")

    def kurallari_yenile(self) -> None:
        self.kurallar, self.kategori_sirasi = kurallari_yukle()
        self.log_yaz(f"{len(self.kurallar)} uzantı kuralı yüklendi.")
        if self.tarama:
            self.tara()

    # ---------------------------------------------------------------- ekran

    def yardim(self) -> None:
        pencere = tk.Toplevel(self)
        pencere.title("Kullanım")
        pencere.geometry("640x560")
        metin = tk.Text(pencere, wrap="word", padx=14, pady=14,
                        font=("Segoe UI", 10), relief="flat")
        metin.pack(fill="both", expand=True)
        metin.insert("1.0", KULLANIM_METNI)
        metin.configure(state="disabled")
        ttk.Button(pencere, text="Kapat",
                   command=pencere.destroy).pack(pady=(0, 12))

    def hakkinda(self) -> None:
        messagebox.showinfo(
            "Hakkında",
            f"{UYGULAMA_ADI}  v{SURUM}\n\n"
            "İndirilenler klasörünü dosya türlerine göre düzenler.\n"
            "Kurallar: kurallar.json\n"
            f"Ayar ve geçmiş: {veri_klasoru()}")


def son_kayit_var() -> bool:
    return son_tasima_kaydi() is not None


KULLANIM_METNI = """\
NASIL KULLANILIR
────────────────
1. Üstteki kutuda düzenlenecek klasörü yazın veya "Gözat" ile seçin.
   Program açılır açılmaz İndirilenler klasörünü kendisi bulur.
2. "Tara" (F5) düğmesine basın. Dosyalar türlerine göre gruplanır:
   exe/msi → Programlar ve Betikler,  jpg/png → Resimler,  mp4/mkv → Videolar ...
3. Tablodaki satırın başındaki kutucuğa tıklayarak o kategorinin taşınmasını
   açın/kapatın. Satırı çift tıklayınca o klasör açılır.
   "Diğer Dosyalar" varsayılan olarak kapalıdır.
4. "Düzenle" düğmesine basın.

KURU ÇALIŞTIRMA
" Kuru çalıştırma " işaretliyken hiçbir dosya taşınmaz; sadece ne olacağını
sağdaki loga yazar. İşaretı kaldırıp "Düzenle"ye basınca onay penceresi çıkar
ve dosyalar taşınır.

GERİ ALMA
Taşıma sonrası "Son taşımayı geri al" düğmesi, taşınan tüm dosyaları eski
yerine döndürür. Kayıt veri\\gecmis.jsonl dosyasında tutulur, program kapansa
da sonraki açılışta geri alma çalışır.

KURALLAR
Seçenekler > Kuralları düzenle ile kurallar.json dosyası Not Defteri'nde
açılır. Biçim:
    {
      "Programlar ve Betikler": ["exe", "msi", "bat"],
      "Resimler": ["jpg", "jpeg", "png"]
    }
Dosyayı kaydedip kapatın ve "Kuralları yeniden yükle"ye basın.

DOKUNULMAYANLAR
• Yarım inmiş indirmeler (.crdownload, .part, .tmp) ve geçici dosyalar
• Gizli/sistem dosyaları (desktop.ini, Thumbs.db, ~$...)
• Alt klasörlerin içi (yalnızca klasörün üst düzeyi taranır)
• Aynı adlı dosya varsa numara eklenir: "rapor.pdf", "rapor (1).pdf"
"""


def main() -> None:
    uygulama = Uygulama()
    uygulama.duzenle_metin_guncelle()
    uygulama.mainloop()


if __name__ == "__main__":
    main()
