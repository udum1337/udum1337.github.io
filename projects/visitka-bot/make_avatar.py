"""Генерирует яркую аватарку для бота: avatar.png (1024x1024).

Запуск: .venv\\Scripts\\python.exe make_avatar.py
Хочешь другие цвета — поменяй STOPS ниже и запусти снова.
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatar.png")

# Цвета градиента: (позиция 0..1, RGB)
STOPS = [
    (0.00, (124, 58, 237)),   # фиолетовый
    (0.45, (236, 72, 153)),   # розовый
    (1.00, (249, 115, 22)),   # оранжевый
]

SYMBOL = "</>"
TEXT_COLOR = (255, 255, 255)


def gradient() -> np.ndarray:
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    t = ((x + y) / (2 * (SIZE - 1))) ** 0.92

    img = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    positions = [p for p, _ in STOPS]
    for channel in range(3):
        values = [c[channel] for _, c in STOPS]
        img[..., channel] = np.interp(t, positions, values)

    # Мягкое свечение сверху слева.
    cx, cy = SIZE * 0.24, SIZE * 0.18
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (SIZE * 0.9)
    glow = np.clip(1 - dist, 0, 1)[..., None] ** 2 * 0.45
    img += glow * 255

    # Лёгкая виньетка по краям.
    d = np.sqrt((x - SIZE / 2) ** 2 + (y - SIZE / 2) ** 2) / (SIZE * 0.78)
    img *= (1 - np.clip(d, 0, 1)[..., None] ** 2 * 0.22)

    # Едва заметное зерно, чтобы градиент не выглядел пластиковым.
    rng = np.random.default_rng(42)
    img += rng.normal(0, 2.2, (SIZE, SIZE, 1))

    return np.clip(img, 0, 255).astype(np.uint8)


def pick_font() -> str:
    for name in ("consolab.ttf", "segoeuib.ttf", "arialbd.ttf"):
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError("Не нашёл жирный шрифт в C:\\Windows\\Fonts")


def fit_font(path: str, target_width: int) -> ImageFont.FreeTypeFont:
    size = 400
    font = ImageFont.truetype(path, size)
    bbox = font.getbbox(SYMBOL)
    width = bbox[2] - bbox[0]
    size = max(10, int(size * target_width / width))
    return ImageFont.truetype(path, size)


def main() -> None:
    base = Image.fromarray(gradient())

    # Глянцевый блик.
    gloss = Image.new("L", (SIZE, SIZE), 0)
    gd = ImageDraw.Draw(gloss)
    gd.ellipse(
        [-SIZE * 0.35, -SIZE * 0.60, SIZE * 0.80, SIZE * 0.30],
        fill=110,
    )
    gloss = gloss.filter(ImageFilter.GaussianBlur(95))
    gloss = gloss.point(lambda v: int(v * 0.5))
    base = Image.composite(Image.new("RGB", (SIZE, SIZE), "white"), base, gloss)

    # Текст с тенью.
    font = fit_font(pick_font(), int(SIZE * 0.58))
    bbox = font.getbbox(SYMBOL)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = ((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1])

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text(
        (pos[0] + 8, pos[1] + 20),
        SYMBOL,
        font=font,
        fill=(35, 0, 60, 190),
        stroke_width=8,
        stroke_fill=(35, 0, 60, 190),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    base = Image.alpha_composite(base.convert("RGBA"), shadow)

    text_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    td.text(
        pos,
        SYMBOL,
        font=font,
        fill=TEXT_COLOR + (255,),
        stroke_width=8,
        stroke_fill=TEXT_COLOR + (255,),
    )
    base = Image.alpha_composite(base, text_layer)

    base.convert("RGB").save(OUT, "PNG")
    print(f"Готово: {OUT}")


if __name__ == "__main__":
    main()
