"""Fetch real, relevant, licence-friendly demo images from the internet.

Selection order and strategy:
  1. Wikimedia Commons — filenames are literal ("Bag of rice", "Frying pan"),
     so results match the product well. Candidates are scored by how many query
     words appear in the file title, and obvious non-photos are rejected.
  2. Openverse (CC/Flickr) — fallback, also scored by title.
  3. Lorem Picsum — last-resort random photo so something always loads.

Every result is normalised with Pillow so stored files have a consistent size
and format.
"""
import io
import re
import time

import requests
from PIL import Image, ImageOps

USER_AGENT = {"User-Agent": "shopbazar-demo/1.0 (demo seed)"}
TIMEOUT = 30

# Filenames that are almost never a usable product photo.
BLACKLIST = re.compile(
    r"(map|logo|diagram|chart|icon|coat of arms|flag|poster|drawing|cartoon|"
    r"sketch|seal|monument|sign|screenshot|graph|stamp|coin|banknote|plaque|"
    r"schematic|illustration|clipart|text|document|book|cover|page|advertis|"
    r"leaflet|newspaper|blueprint|panorama|panoramic|satellite|"
    r"street view|factory|pasta|museum|century|antique|processing|vat|"
    r"flattened|broken|blood|fossil|compost|"
    r"\.tiff?$|\.webp$)",
    re.IGNORECASE,
)

# search keyword per SKU (kept specific so results match the product name)
DEMO_PRODUCT_KEYWORDS = {
    "SBZ-1000": "smartphone",
    "SBZ-1001": "earbuds",
    "SBZ-1002": "power bank",
    "SBZ-1003": "bluetooth speaker",
    "SBZ-1004": "smartwatch",
    "SBZ-1005": "rice bag",
    "SBZ-1006": "cooking oil",
    "SBZ-1007": "sugar cubes",
    "SBZ-1008": "spices",
    "SBZ-1009": "mixed nuts",
    "SBZ-1010": "kurta",
    "SBZ-1011": "indian woman sari",
    "SBZ-1012": "t-shirt",
    "SBZ-1013": "jeans",
    "SBZ-1014": "sofa couch",
    "SBZ-1015": "frying pan",
    "SBZ-1016": "bed sheet",
    "SBZ-1017": "face wash product",
    "SBZ-1018": "coconut oil",
    "SBZ-1019": "moisturizer",
}

DEMO_BANNER_KEYWORDS = ["supermarket shopping", "clothing store"]

# Pinned Wikimedia Commons file titles — verified to resolve, chosen to clearly
# match each product. Used first; search is only a fallback.
DEMO_PRODUCT_IMAGES = {
    "SBZ-1000": "File:5 different Smartphones.jpg",
    "SBZ-1001": "File:Bose QuietComfort Ultra Earbuds - 2.jpg",
    "SBZ-1002": "File:Portable power bank.jpg",
    "SBZ-1003": "File:Bluetooth speaker JBL Xtreme from side showing one of the bass speakers.jpg",
    "SBZ-1004": "File:Android Wear Smartwatch- LG G Watch (15048721571).jpg",
    "SBZ-1005": "File:Bag of rice 20221028 150305.jpg",
    "SBZ-1006": "File:Cooking oils on a shelf 02.jpg",
    "SBZ-1007": "File:Individually wrapped sugar cubes.jpg",
    "SBZ-1008": "File:020231119 Spices in Poland.jpg",
    "SBZ-1009": "File:20130126 Mixed nuts.jpg",
    "SBZ-1010": "File:Blue khadi kurta.jpg",
    "SBZ-1011": "File:Indian Woman in Saree.jpg",
    "SBZ-1012": "File:A boy wearing T-shirt and short jeans.jpg",
    "SBZ-1013": "File:Blonde woman wearing jeans - 2007.JPG",
    "SBZ-1014": "File:Sofa, Couch, Studio, Rostov-on-Don, Russia.jpg",
    "SBZ-1015": "File:Egg roll frying pan from Korea.jpg",
    "SBZ-1016": "File:Bed sheet.JPG",
    "SBZ-1017": "File:Fit Me Face Wash review.jpg",
    "SBZ-1018": "File:Coconut Oil amp 30050.jpg",
    "SBZ-1019": "File:Calamine Lotion B P.jpg",
}

DEMO_BANNER_IMAGES = [
    "File:Interior of Maxima supermarket in Molas Shopping Centre, Kaunas, May 2026 1.jpg",
    "File:Clothing store Modas Trevo in Barcelos.jpg",
]

# Resolved direct thumbnail URLs (stable, no API call needed at seed time).
DEMO_PRODUCT_IMAGE_URLS = {
    "SBZ-1000": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c6/5_different_Smartphones.jpg/1920px-5_different_Smartphones.jpg",
    "SBZ-1001": "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/10/Bose_QuietComfort_Ultra_Earbuds_-_2.jpg/1920px-Bose_QuietComfort_Ultra_Earbuds_-_2.jpg",
    "SBZ-1002": "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/75/Portable_power_bank.jpg/1920px-Portable_power_bank.jpg",
    "SBZ-1003": "https://thumb.wikimedia.org/wikipedia/commons/thumb/b/b0/Bluetooth_speaker_JBL_Xtreme_from_side_showing_one_of_the_bass_speakers.jpg/1920px-Bluetooth_speaker_JBL_Xtreme_from_side_showing_one_of_the_bass_speakers.jpg",
    "SBZ-1004": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3a/Android_Wear_Smartwatch-_LG_G_Watch_%2815048721571%29.jpg/1920px-Android_Wear_Smartwatch-_LG_G_Watch_%2815048721571%29.jpg",
    "SBZ-1005": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/2a/Bag_of_rice_20221028_150305.jpg/1920px-Bag_of_rice_20221028_150305.jpg",
    "SBZ-1006": "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f0/Cooking_oils_on_a_shelf_02.jpg/1920px-Cooking_oils_on_a_shelf_02.jpg",
    "SBZ-1007": "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/10/Individually_wrapped_sugar_cubes.jpg/1920px-Individually_wrapped_sugar_cubes.jpg",
    "SBZ-1008": "https://thumb.wikimedia.org/wikipedia/commons/thumb/f/f8/020231119_Spices_in_Poland.jpg/1920px-020231119_Spices_in_Poland.jpg",
    "SBZ-1009": "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e1/20130126_Mixed_nuts.jpg/1920px-20130126_Mixed_nuts.jpg",
    "SBZ-1010": "https://upload.wikimedia.org/wikipedia/commons/c/c5/Blue_khadi_kurta.jpg",
    "SBZ-1011": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/31/Indian_Woman_in_Saree.jpg/1920px-Indian_Woman_in_Saree.jpg",
    "SBZ-1012": "https://upload.wikimedia.org/wikipedia/commons/6/60/A_boy_wearing_T-shirt_and_short_jeans.jpg",
    "SBZ-1013": "https://upload.wikimedia.org/wikipedia/commons/d/d9/Blonde_woman_wearing_jeans_-_2007.JPG",
    "SBZ-1014": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/23/Sofa%2C_Couch%2C_Studio%2C_Rostov-on-Don%2C_Russia.jpg/1920px-Sofa%2C_Couch%2C_Studio%2C_Rostov-on-Don%2C_Russia.jpg",
    "SBZ-1015": "https://upload.wikimedia.org/wikipedia/commons/0/05/Egg_roll_frying_pan_from_Korea.jpg",
    "SBZ-1016": "https://upload.wikimedia.org/wikipedia/commons/6/68/Bed_sheet.JPG",
    "SBZ-1017": "https://upload.wikimedia.org/wikipedia/commons/2/28/Fit_Me_Face_Wash_review.jpg",
    "SBZ-1018": "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/00/Coconut_Oil_amp_30050.jpg/1920px-Coconut_Oil_amp_30050.jpg",
    "SBZ-1019": "https://upload.wikimedia.org/wikipedia/commons/0/02/Calamine_Lotion_B_P.jpg",
}

DEMO_BANNER_IMAGE_URLS = [
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/79/Interior_of_Maxima_supermarket_in_Molas_Shopping_Centre%2C_Kaunas%2C_May_2026_1.jpg/1920px-Interior_of_Maxima_supermarket_in_Molas_Shopping_Centre%2C_Kaunas%2C_May_2026_1.jpg",
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/ef/Clothing_store_Modas_Trevo_in_Barcelos.jpg/1920px-Clothing_store_Modas_Trevo_in_Barcelos.jpg",
]


def _wikimedia_title_url(title, width=1400):
    """Resolve a Commons file title to a scaled thumbnail URL, or None."""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": width,
            },
            headers=USER_AGENT,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return None
    for page in resp.json().get("query", {}).get("pages", {}).values():
        if "missing" in page:
            continue
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if url:
            return url
    return None


def _score(title, keyword):
    words = [w for w in re.split(r"\W+", keyword.lower()) if len(w) > 2]
    if not words:
        return 0
    low = title.lower()
    return sum(1 for w in words if w in low)


def _wikimedia_candidates(keyword):
    """Return [(score, title, url), ...] from Wikimedia Commons."""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {keyword}",
                "gsrnamespace": 6,
                "gsrlimit": 25,
                "prop": "imageinfo",
                "iiprop": "url|mime|size",
                "iiurlwidth": 1400,
            },
            headers=USER_AGENT,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return []

    out = []
    for page in resp.json().get("query", {}).get("pages", {}).values():
        title = page.get("title", "")
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        url = info.get("thumburl") or info.get("url")
        width = info.get("width", 0)
        if not url or not mime.startswith("image/"):
            continue
        if BLACKLIST.search(title) or (width and width < 350):
            continue
        out.append((_score(title, keyword), title, url))
    return out


def _openverse_candidates(keyword):
    try:
        resp = requests.get(
            "https://api.openverse.org/v1/images/",
            params={
                "q": keyword,
                "page_size": 12,
                "license_type": "commercial",
                "mature": "false",
            },
            headers=USER_AGENT,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
    except Exception:
        return []
    out = []
    for item in resp.json().get("results", []):
        title = item.get("title") or ""
        url = item.get("url")
        if not url or BLACKLIST.search(title):
            continue
        out.append((_score(title, keyword), title, url))
    return out


def _picsum(seed, size):
    return f"https://picsum.photos/seed/{seed}/{size[0]}/{size[1]}"


def candidates(keyword, seed, size):
    """Ordered [(title, url), ...]: relevant Wikimedia hits, then Openverse, then Picsum."""
    found = _wikimedia_candidates(keyword) + _openverse_candidates(keyword)
    # Prefer anything that actually mentions the query; keep the rest as backfill.
    relevant = [c for c in found if c[0] > 0]
    backfill = [c for c in found if c[0] == 0]
    ordered = sorted(relevant, key=lambda c: -c[0]) + backfill
    result = [(title, url) for _score_, title, url in ordered]
    result.append(("picsum", _picsum(seed, size)))
    return result


def _download(url, size):
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=USER_AGENT, timeout=TIMEOUT)
        except Exception:
            resp = None
        if resp is not None and resp.status_code == 200:
            if not resp.headers.get("content-type", "").startswith("image"):
                return None
            image = Image.open(io.BytesIO(resp.content)).convert("RGB")
            image = ImageOps.fit(image, size, Image.LANCZOS)
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=85)
            return buffer.getvalue()
        time.sleep(1.0 + attempt)  # back off on throttle/transient error
    return None


def fetch_image(keyword, seed, size=(800, 800), url=None, title=None, debug=False):
    """Return normalised JPEG bytes for a product, or ``None`` on failure.

    Resolution order: pinned direct URL -> pinned Commons title -> scored search
    -> random Picsum photo.
    """
    if url:
        data = _download(url, size)
        if data:
            if debug:
                print(f"[image] {keyword!r} -> pinned url")
            return data

    if title:
        resolved = _wikimedia_title_url(title)
        if resolved:
            data = _download(resolved, size)
            if data:
                if debug:
                    print(f"[image] {keyword!r} -> {title!r} (pinned)")
                return data

    for cand_title, cand_url in candidates(keyword, seed, size):
        data = _download(cand_url, size)
        if data:
            if debug:
                print(f"[image] {keyword!r} -> {cand_title!r}")
            return data
    return None


def keyword_for(product):
    return DEMO_PRODUCT_KEYWORDS.get(product.sku) or (product.name_en or product.name_bn or "product")
