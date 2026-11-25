"""Genereerib PNG-ikoonid (192 ja 512 px). Vajab: pip install pillow"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "app" / "icons"


def draw(size: int) -> Image.Image:
    s = size / 512
    im = Image.new("RGBA", (size, size), "#0b5e8a")   # täisruut — sobib ka "maskable" ikooniks
    d = ImageDraw.Draw(im)
    R = lambda *xy: [round(v * s) for v in xy]
    d.rounded_rectangle(R(104, 128, 408, 400), radius=round(36 * s), fill="#ffffff")
    d.rounded_rectangle(R(104, 128, 408, 200), radius=round(36 * s), fill="#f2b632")
    d.rectangle(R(104, 164, 408, 200), fill="#f2b632")
    d.rounded_rectangle(R(168, 96, 196, 168), radius=round(14 * s), fill="#ffffff")
    d.rounded_rectangle(R(316, 96, 344, 168), radius=round(14 * s), fill="#ffffff")
    # lained
    for i in range(4):
        x0 = 136 + i * 60
        d.pieslice(R(x0, 290, x0 + 60, 336), 180, 360, fill="#4fb0e3")
    d.rectangle(R(136, 312, 376, 368), fill="#4fb0e3")
    d.ellipse(R(230, 236, 282, 288), fill="#f2b632")
    return im


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for n in (192, 512):
        draw(n).save(OUT / f"icon-{n}.png")
        print("ok", n)
