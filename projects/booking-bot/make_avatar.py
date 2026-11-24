"""Аватарка для бота записи: календарь с галочкой. 1024×1024."""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SIZE = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatar.png")

STOPS = [
    (0.00, (11, 18, 32)),     # почти чёрный
    (0.55, (124, 45, 18)),    # тёмно-коричневый
    (1.00, (180, 83, 9)),     # янтарный
]

CREAM = (255, 247, 237)
AMBER = (245, 158, 11)
GRID = (203, 213, 225)


def gradient() -> np.ndarray:
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    t = ((x + y) / (2 * (SIZE - 1))) ** 0.9
    img = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    positions = [p for p, _ in STOPS]
    for channel in range(3):
        values = [c[channel] for _, c in STOPS]
        img[..., channel] = np.interp(t, positions, values)

    cx, cy = SIZE * 0.2, SIZE * 0.15
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (SIZE * 0.75)
    glow = np.clip(1 - dist, 0, 1)[..., None] ** 2 * 0.3
    img += glow * 255

    rng = np.random.default_rng(7)
    img += rng.normal(0, 2.0, (SIZE, SIZE, 1))
    return np.clip(img, 0, 255).astype(np.uint8)


def main() -> None:
    base = Image.fromarray(gradient()).convert("RGBA")

    # Тень под карточкой.
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [230, 260, 820, 860], radius=72, fill=(0, 0, 0, 160)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(45))
    base = Image.alpha_composite(base, shadow)

    draw = ImageDraw.Draw(base)

    # Кольца календаря (видны сверху).
    for x in (340, 650):
        draw.rounded_rectangle([x, 186, x + 34, 300], radius=17, fill=(226, 232, 240, 255))

    # Карточка календаря.
    draw.rounded_rectangle([212, 232, 812, 832], radius=64, fill=CREAM + (255,))

    # Янтарная шапка календаря.
    draw.rounded_rectangle([212, 232, 812, 380], radius=64, fill=AMBER + (255,))
    draw.rectangle([212, 320, 812, 380], fill=AMBER + (255,))

    # Сетка дней.
    for row, y in enumerate((460, 580, 700)):
        for col, x in enumerate((330, 470, 610)):
            fill = AMBER + (255,) if (row, col) in {(0, 1), (1, 2)} else GRID + (255,)
            draw.ellipse([x, y, x + 40, y + 40], fill=fill)

    # Галочка в круге.
    draw.ellipse([584, 584, 856, 856], fill=CREAM + (255,))
    draw.ellipse([600, 600, 840, 840], fill=AMBER + (255,))
    draw.line(
        [(665, 720), (705, 762), (782, 675)],
        fill=(255, 255, 255, 255),
        width=30,
        joint="curve",
    )

    base.convert("RGB").save(OUT, "PNG")
    print(f"Готово: {OUT}")


if __name__ == "__main__":
    main()
