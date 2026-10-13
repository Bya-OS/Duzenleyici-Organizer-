# -*- coding: utf-8 -*-
"""
Uygulama ikonunu üretir:  ikon.ico  ve  ikon_onizleme.png

Tasarım: turkuaz klasör, içinden çıkan üç renkli dosya kartı ve
klasöre doğru işaret eden ok. 1024 px tasarım, 2048 px'de çizilip
ihtiyaç olan tüm boyutlara küçültülerek .ico içine gömülür.

Kullanım:   pip install pillow   (yalnızca ikonu üretmek için)
             python ikon_uret.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# ------------------------------------------------------------------ palet
TURKUAZ_ACIK = (34, 197, 176)      # #22C5B0  (daha doygun, küçük boyutta okunsun)
TURKUAZ_KOYU = (13, 130, 121)      # #0A8279
TURKUAZ_DERIN = (13, 110, 103)     # #0D6E67
ACIK_MAVI = (236, 254, 255)        # #ECFEFF
BEYAZ = (255, 255, 255)
KEHRIBAR = (251, 191, 36)          # #FBBF24
GUL = (244, 63, 94)                # #F43F5E

BOYUTLAR = [16, 24, 32, 48, 64, 128, 256]
CIZIM = 2048                       # 2 kat çizip küçült (pürüzsüz kenar)


def p(deger: float) -> int:
    """0..1 arası tasarım koordinatını çizim pikseline çevirir."""
    return int(round(deger * CIZIM))


def kutu(degerler: tuple) -> tuple:
    return tuple(p(v) for v in degerler)


def dikey_gradyan(genislik: int, yukseklik: int,
                  ust: tuple, alt: tuple) -> Image.Image:
    serit = Image.new("RGB", (1, max(1, yukseklik)))
    nokta = max(1, yukseklik - 1)
    for y in range(yukseklik):
        t = y / nokta
        serit.putpixel((0, y), tuple(
            int(ust[i] + (alt[i] - ust[i]) * t) for i in range(3)))
    return serit.resize((max(1, genislik), max(1, yukseklik)), Image.BILINEAR)


def katman_ekle(resim: Image.Image, kutu_degerleri: tuple, yaricap: int,
                dolgu) -> None:
    """Yuvarlak dikdörtgeni yeni bir katmana çizip ana resme ekler."""
    x0, y0, x1, y1 = kutu(kutu_degerleri)
    maske = Image.new("L", resim.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle(
        (x0, y0, x1, y1), radius=max(1, yaricap), fill=255)

    if callable(dolgu):
        ic = dikey_gradyan(x1 - x0, y1 - y0, *dolgu()).convert("RGBA")
        carpan = 255
    else:
        renk = tuple(dolgu)
        carpan = renk[3] if len(renk) == 4 else 255
        if len(renk) == 3:
            renk = renk + (255,)
        ic = Image.new("RGBA", (max(1, x1 - x0), max(1, y1 - y0)), renk)

    gecici = Image.new("RGBA", ic.size, (0, 0, 0, 0))
    gecici.paste(ic, (0, 0))
    tampon = Image.new("RGBA", resim.size, (0, 0, 0, 0))
    tampon.paste(gecici, (x0, y0))
    # keskin yuvarlak kenar yarı saydam renklerde de korunsun
    tampon.putalpha(maske.point(lambda a: a * carpan // 255))
    resim.alpha_composite(tampon)


def ok_noktalari(merkez: tuple, uzunluk: float, aci: float,
                 olcek: float = 1.0) -> list:
    """
    Kalın okun köşe noktaları.

    Taban yön "sağa bakıyor" (0°). Görüntü koordinatlarında y aşağı
    gittiği için pozitif açı saat yönündedir: 135° = sol-aşağı.
    """
    import math
    cx, cy = merkez
    kuyruk = p(uzunluk * olcek)
    kafa = p(0.060 * olcek)
    govde_k = p(0.042 * olcek)
    kafa_k = p(0.105 * olcek)

    noktalar = [
        (cx - kuyruk, cy - govde_k / 2),
        (cx + kuyruk - kafa, cy - govde_k / 2),
        (cx + kuyruk - kafa, cy - kafa_k / 2),
        (cx + kuyruk, cy),
        (cx + kuyruk - kafa, cy + kafa_k / 2),
        (cx + kuyruk - kafa, cy + govde_k / 2),
        (cx - kuyruk, cy + govde_k / 2),
    ]
    rad = math.radians(aci)
    cos, sin = math.cos(rad), math.sin(rad)
    donmus = []
    for x, y in noktalar:
        dx, dy = x - cx, y - cy
        donmus.append((cx + dx * cos - dy * sin, cy + dx * sin + dy * cos))
    return donmus


def ok_ekle(resim: Image.Image, merkez: tuple, uzunluk: float, aci: float) -> None:
    """Oku koyu dış hatla çevirip ekler; açık duvarlarda da görünür."""
    for olcek, renk in ((1.18, TURKUAZ_DERIN + (235,)), (1.0, BEYAZ + (255,))):
        katman = Image.new("RGBA", resim.size, (0, 0, 0, 0))
        ImageDraw.Draw(katman).polygon(
            ok_noktalari(merkez, uzunluk, aci, olcek), fill=renk)
        resim.alpha_composite(katman)


def ikon_uret() -> Image.Image:
    """Tasarımı CIZIM pikselinde çizer."""
    resim = Image.new("RGBA", (CIZIM, CIZIM), (0, 0, 0, 0))

    # --- klasörün altına yumuşak gölge (küçük boyutlarda leke yapmasın)
    golge = Image.new("RGBA", resim.size, (0, 0, 0, 0))
    ImageDraw.Draw(golge).rounded_rectangle(
        kutu((0.115, 0.455, 0.905, 0.875)), radius=p(0.085),
        fill=(7, 89, 82, 46),
    )
    resim.alpha_composite(golge.filter(ImageFilter.GaussianBlur(p(0.010))))

    # --- klasör arka paneli (koyu turkuaz)
    katman_ekle(resim, (0.10, 0.30, 0.90, 0.80), p(0.085),
                lambda: (TURKUAZ_DERIN, TURKUAZ_KOYU))

    # --- klasörün sol üst sekmesi
    katman_ekle(resim, (0.10, 0.255, 0.42, 0.42), p(0.055), TURKUAZ_DERIN)

    # --- klasörden çıkan dosya kartları
    for kutu_degerleri, renk in [
        ((0.145, 0.155, 0.305, 0.60), BEYAZ),
        ((0.350, 0.095, 0.510, 0.60), KEHRIBAR),
        ((0.555, 0.155, 0.715, 0.60), GUL),
    ]:
        katman_ekle(resim, kutu_degerleri, p(0.022), renk)

    # --- beyaz kartın üstüne turkuaz satırlar (kâğıt hissi)
    for sira in range(2):
        y = 0.235 + sira * 0.105
        katman_ekle(resim, (0.178, y, 0.274, y + 0.034), p(0.017),
                    TURKUAZ_DERIN)

    # --- klasör ön yüzü (turkuaz degrade). Parlaklık şeridi
    #     bilerek yok: küçük boyutlarda ikonu soluk gösteriyordu.
    katman_ekle(resim, (0.08, 0.42, 0.92, 0.885), p(0.09),
                lambda: (TURKUAZ_ACIK, TURKUAZ_KOYU))

    # --- sağ üstte, klasöre doğru işaret eden ok (135° = sol-aşağı)
    ok_ekle(resim, (p(0.845), p(0.185)), 0.095, 135)

    return resim


def main() -> int:
    burada = Path(__file__).resolve().parent
    buyuk = ikon_uret()

    onizleme_yolu = burada / "ikon_onizleme.png"
    buyuk.resize((512, 512), Image.LANCZOS).save(onizleme_yolu)
    print(f"onizleme : {onizleme_yolu}")

    ico_yolu = burada / "ikon.ico"
    buyuk.save(ico_yolu, format="ICO", sizes=[(b, b) for b in BOYUTLAR])
    print(f"ikon     : {ico_yolu}  ({ico_yolu.stat().st_size} bayt)")
    print(f"boyutlar : {', '.join(map(str, BOYUTLAR))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
