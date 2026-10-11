"""Build a label-contact-sheet of demo product images for quick visual review."""
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from apps.catalogue.models import Product  # noqa: E402

MEDIA = Path(__file__).resolve().parent.parent / "media"
COLS, CELL, IMG = 5, 300, 260
FONT_PATHS = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    products = [p for p in Product.objects.order_by("sku") if p.primary_image]
    rows = (len(products) + COLS - 1) // COLS
    canvas = Image.new("RGB", (COLS * CELL, rows * CELL), (240, 247, 247))
    draw = ImageDraw.Draw(canvas)
    f = font(20)
    for i, product in enumerate(products):
        r, c = divmod(i, COLS)
        try:
            img = Image.open(product.primary_image.image.path).convert("RGB")
        except Exception:
            continue
        img = img.resize((IMG, IMG))
        x = c * CELL + (CELL - IMG) // 2
        y = r * CELL + 10
        canvas.paste(img, (x, y))
        label = (product.name_en or product.sku)[:26]
        draw.text((c * CELL + 12, y + IMG + 4), f"{product.sku}  {label}", fill=(15, 46, 46), font=f)
    out = MEDIA / "_contact_sheet.jpg"
    canvas.save(out, "JPEG", quality=88)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
