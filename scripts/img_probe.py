"""Probe which image titles the demo fetcher would pick, per product keyword."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.pages.demo_images import DEMO_BANNER_KEYWORDS, candidates, DEMO_PRODUCT_KEYWORDS  # noqa: E402


def main():
    def p(s):
        sys.stdout.write(s.encode("ascii", "replace").decode() + "\n")
        sys.stdout.flush()

    for sku, keyword in DEMO_PRODUCT_KEYWORDS.items():
        cands = candidates(keyword, seed=sku, size=(800, 800))
        top = [t for t, _u in cands[:4] if t != "picsum"]
        p(f"{sku}  {keyword:<18} -> " + (" | ".join(top) if top else "(no relevant hit)"))
    p("")
    for i, keyword in enumerate(DEMO_BANNER_KEYWORDS):
        cands = candidates(keyword, seed=f"banner-{i}", size=(1600, 600))
        top = [t for t, _u in cands[:4] if t != "picsum"]
        p(f"banner-{i}  {keyword:<18} -> " + " | ".join(top))


if __name__ == "__main__":
    main()
