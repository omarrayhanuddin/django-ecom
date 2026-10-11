"""Query candidate image titles for ad-hoc keywords: python img_query.py "phrase" ..."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.pages.demo_images import candidates  # noqa: E402


def main(keywords):
    for keyword in keywords:
        cands = candidates(keyword, seed="probe", size=(800, 800))
        top = [t for t, _u in cands[:5] if t != "picsum"]
        sys.stdout.write((keyword + " -> " + " | ".join(top)).encode("ascii", "replace").decode() + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main(sys.argv[1:])
