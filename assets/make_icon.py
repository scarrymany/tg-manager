#!/usr/bin/env python3
"""Генератор иконки приложения (без внешних зависимостей, только Pillow).

Рисует иконку в стиле Telegram: скруглённый квадрат с сине-голубым градиентом,
белый бумажный самолётик и лёгкий «стек окон» — намёк на менеджер аккаунтов.
Сохраняет icon.png (512) и icon_256.png в этой же папке.
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

# Палитра Telegram
TOP = (42, 171, 238)      # #2AABEE
BOTTOM = (34, 158, 217)   # #229ED9


def _vertical_gradient(size: int, top, bottom) -> Image.Image:
    base = Image.new("RGB", (size, size), top)
    draw = ImageDraw.Draw(base)
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    return base


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def _plane(size: int) -> Image.Image:
    """Белый бумажный самолётик на прозрачном слое размером size."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    s = size
    # Координаты самолётика (в долях холста), классический телеграм-силуэт
    body = [
        (0.205, 0.520),  # левый угол (низ)
        (0.820, 0.255),  # правый верхний угол
        (0.660, 0.760),  # правый низ (хвост крыла)
        (0.470, 0.605),  # центральный изгиб
    ]
    pts = [(x * s, y * s) for x, y in body]
    d.polygon(pts, fill=(255, 255, 255, 255))
    # Нижний «клин» (тень крыла) — чуть темнее для объёма
    fold = [
        (0.470, 0.605),
        (0.660, 0.760),
        (0.470, 0.855),
    ]
    pts2 = [(x * s, y * s) for x, y in fold]
    d.polygon(pts2, fill=(210, 234, 248, 255))
    return layer


def build(size: int = 512) -> Image.Image:
    scale = 4  # суперсэмплинг для гладких краёв
    S = size * scale
    radius = int(S * 0.235)  # squircle-подобное скругление

    grad = _vertical_gradient(S, TOP, BOTTOM)

    # Лёгкий «стек окон» на фоне — тонкие полупрозрачные плашки
    deco = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    for i, alpha in enumerate((26, 40)):
        off = int(S * (0.10 + i * 0.055))
        dd.rounded_rectangle(
            [S * 0.30 + off * 0.2, off, S * 0.92, S * 0.30 + off],
            radius=int(S * 0.03),
            fill=(255, 255, 255, alpha),
        )
    grad = Image.alpha_composite(grad.convert("RGBA"), deco)

    # Самолётик с мягкой тенью
    plane = _plane(S)
    alpha = plane.split()[3]
    shadow = Image.new("RGBA", (S, S), (8, 55, 85, 255))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(S * 0.010)).point(lambda a: int(a * 0.30)))
    offset = int(S * 0.012)
    grad.alpha_composite(shadow, (offset, offset))
    grad = Image.alpha_composite(grad, plane)

    # Скругление углов
    mask = _rounded_mask(S, radius)
    grad.putalpha(mask)

    out = grad.resize((size, size), Image.LANCZOS)
    return out


def main() -> None:
    for sz, name in ((512, "icon.png"), (256, "icon_256.png"), (128, "icon_128.png")):
        img = build(sz)
        img.save(os.path.join(HERE, name))
        print("wrote", name)


if __name__ == "__main__":
    main()
