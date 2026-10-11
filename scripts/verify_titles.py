"""Verify pinned Wikimedia file titles resolve to an image URL."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.pages.demo_images import _wikimedia_title_url  # noqa: E402

TITLES = [
    "File:5 different Smartphones.jpg",
    "File:Bose QuietComfort Ultra Earbuds - 2.jpg",
    "File:Portable power bank.jpg",
    "File:Bluetooth speaker JBL Xtreme from side showing one of the bass speakers.jpg",
    "File:Android Wear Smartwatch- LG G Watch (15048721571).jpg",
    "File:Bag of rice 20221028 150305.jpg",
    "File:Cooking oils on a shelf 02.jpg",
    "File:Individually wrapped sugar cubes.jpg",
    "File:020231119 Spices in Poland.jpg",
    "File:20130126 Mixed nuts.jpg",
    "File:Blue khadi kurta.jpg",
    "File:Indian Woman in Saree.jpg",
    "File:A boy wearing T-shirt and short jeans.jpg",
    "File:Blonde woman wearing jeans - 2007.JPG",
    "File:Sofa, Couch, Studio, Rostov-on-Don, Russia.jpg",
    "File:Egg roll frying pan from Korea.jpg",
    "File:Bed sheet.JPG",
    "File:Fit Me Face Wash review.jpg",
    "File:Coconut Oil amp 30050.jpg",
    "File:Calamine Lotion B P.jpg",
    "File:Interior of Maxima supermarket in Molas Shopping Centre, Kaunas, May 2026 1.jpg",
    "File:Clothing store Modas Trevo in Barcelos.jpg",
]


def main():
    for t in TITLES:
        url = _wikimedia_title_url(t, 1400)
        status = "PASS" if url else "MISS"
        sys.stdout.write(f"{status}  {t}\n".encode("ascii", "replace").decode())
        sys.stdout.flush()
        time.sleep(0.4)


if __name__ == "__main__":
    main()
