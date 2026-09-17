from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

for size in (180, 192, 512):
    image = Image.new("RGB", (size, size), "#EEF1F6")
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.12)
    radius = int(size * 0.24)
    draw.rounded_rectangle((margin, margin, size - margin, size - margin), radius=radius, fill="#111D3C")
    accent = int(size * 0.075)
    draw.rounded_rectangle((size - margin - accent * 2, margin, size - margin, size - margin), radius=accent, fill="#C7F24A")
    font_size = int(size * 0.43)
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "S", font=font)
    x = (size - (bbox[2] - bbox[0])) / 2 - int(size * 0.025)
    y = (size - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((x, y), "S", font=font, fill="#FFFFFF")
    image.save(OUT / f"icon-{size}.png", optimize=True)
