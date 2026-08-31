#!/usr/bin/env python3
"""Генератор иконок TG Manager в стиле SCARP (монохром, графит/белый).

Выдаёт:
  icon.png / icon_256 / icon_128 — app-icon: графитовый squircle + белый самолётик
  logo_mark.png                  — белая плашка с тёмным знаком (для шапки, .logo-icon)
Только Pillow, без внешних зависимостей.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

GRAPHITE = (20, 20, 20)      # #141414
BORDER = (42, 42, 42)        # #2A2A2A
WHITE = (255, 255, 255)
INK = (10, 10, 10)           # #0A0A0A

# Силуэт бумажного самолётика (в долях холста)
_BODY = [(0.205, 0.520), (0.820, 0.255), (0.660, 0.760), (0.470, 0.605)]
_FOLD = [(0.470, 0.605), (0.660, 0.760), (0.470, 0.855)]


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def _plane(size: int, main, fold_col):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon([(x * size, y * size) for x, y in _BODY], fill=main)
    d.polygon([(x * size, y * size) for x, y in _FOLD], fill=fold_col)
    return layer


def _compose(size: int, bg, border, plane_main, plane_fold, radius_frac=0.235, border_px=0.0):
    scale = 4
    S = size * scale
    radius = int(S * radius_frac)

    base = Image.new("RGBA", (S, S), bg + (255,))
    if border_px:
        bw = max(1, int(S * border_px))
        ImageDraw.Draw(base).rounded_rectangle(
            [bw // 2, bw // 2, S - 1 - bw // 2, S - 1 - bw // 2],
            radius=radius, outline=border + (255,), width=bw)

    plane = _plane(S, plane_main + (255,), plane_fold + (255,))
    # мягкая тень под самолётиком
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    shadow.putalpha(plane.split()[3].filter(ImageFilter.GaussianBlur(S * 0.010)).point(lambda a: int(a * 0.25)))
    off = int(S * 0.010)
    base.alpha_composite(shadow, (off, off))
    base = Image.alpha_composite(base, plane)

    base.putalpha(_rounded_mask(S, radius))
    return base.resize((size, size), Image.LANCZOS)


def build_app_icon(size: int) -> Image.Image:
    # графитовый squircle, белый самолётик, тонкая светлая рамка
    return _compose(size, GRAPHITE, BORDER, WHITE, (210, 210, 210),
                    radius_frac=0.235, border_px=0.012)


def build_logo_mark(size: int) -> Image.Image:
    # белая плашка, тёмный знак (как .logo-icon SCARP)
    return _compose(size, WHITE, WHITE, INK, (40, 40, 40),
                    radius_frac=0.22, border_px=0.0)


def main() -> None:
    for sz, name in ((512, "icon.png"), (256, "icon_256.png"), (128, "icon_128.png")):
        build_app_icon(sz).save(os.path.join(HERE, name))
        print("wrote", name)
    build_logo_mark(256).save(os.path.join(HERE, "logo_mark.png"))
    print("wrote logo_mark.png")


if __name__ == "__main__":
    main()
