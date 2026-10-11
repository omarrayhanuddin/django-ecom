"""Resolve pinned Commons titles to direct thumbnail URLs (retrying on throttle)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.pages.demo_images import (  # noqa: E402
    DEMO_BANNER_IMAGES,
    DEMO_PRODUCT_IMAGES,
    _wikimedia_title_url,
)


def resolve(title, attempts=8):
    for i in range(attempts):
        url = _wikimedia_title_url(title, 1400)
        if url:
            return url
        time.sleep(1.0 + i)
    return None


def main():
    targets = list(DEMO_PRODUCT_IMAGES.items())
    results = {}
    # pass 1
    for sku, title in targets:
        results[sku] = resolve(title)
        time.sleep(0.5)
    # pass 2 for anything that throttled out
    for sku, title in targets:
        if not results.get(sku):
            time.sleep(2.0)
            results[sku] = resolve(title)
    for sku, title in targets:
        url = results.get(sku)
        line = f'    "{sku}": "{url}",' if url else f'    # MISS {sku}  {title}'
        sys.stdout.write(line.encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()

    banner_results = {}
    for i, title in enumerate(DEMO_BANNER_IMAGES):
        banner_results[i] = resolve(title)
        time.sleep(0.5)
    sys.stdout.write("\n# BANNERS\n")
    for i, title in enumerate(DEMO_BANNER_IMAGES):
        url = banner_results.get(i)
        line = f'    "{i}": "{url}",' if url else f'    # MISS banner-{i}  {title}'
        sys.stdout.write(line.encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
