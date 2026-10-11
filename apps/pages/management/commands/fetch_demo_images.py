"""Download real demo images for products and banners.

Usage:
    python manage.py fetch_demo_images            # fill in missing images
    python manage.py fetch_demo_images --force    # re-download everything
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.catalogue.models import Product, ProductImage
from apps.promotions.models import Banner

from ...demo_images import (
    DEMO_BANNER_IMAGE_URLS,
    DEMO_BANNER_KEYWORDS,
    DEMO_PRODUCT_IMAGE_URLS,
    fetch_image,
    keyword_for,
)


def _replace_image(instance, field_name, data, filename):
    field = getattr(instance, field_name)
    try:
        field.delete(save=False)
    except Exception:
        pass
    field.save(filename, ContentFile(data), save=True)


class Command(BaseCommand):
    help = "Fetch real product/banner images from the internet (Openverse/Wikimedia)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="re-download existing images")
        parser.add_argument("--debug", action="store_true", help="print the chosen image title")

    def handle(self, *args, **options):
        force = options["force"]
        debug = options["debug"]
        ok = fail = 0

        # ── Products ──
        for product in Product.objects.order_by("sku"):
            if product.images.exists() and not force:
                continue
            keyword = keyword_for(product)
            data = fetch_image(
                keyword,
                seed=product.sku,
                size=(800, 800),
                url=DEMO_PRODUCT_IMAGE_URLS.get(product.sku),
                debug=debug,
            )
            if not data:
                self.stderr.write(f"  ! no image for {product.sku} ({keyword})")
                fail += 1
                continue
            for old in list(product.images.all()):
                try:
                    old.image.delete(save=False)
                except Exception:
                    pass
                old.delete()
            image = ProductImage(product=product, alt_text=product.name_en or product.name_bn, is_primary=True, order=0)
            _replace_image(image, "image", data, f"{product.sku}.jpg")
            self.stdout.write(f"  + {product.sku:<9} {keyword}")
            ok += 1

        # ── Banners ──
        banners = list(Banner.objects.order_by("order", "id"))
        for idx, banner in enumerate(banners):
            if banner.image and not force:
                continue
            keyword = DEMO_BANNER_KEYWORDS[idx % len(DEMO_BANNER_KEYWORDS)]
            banner_url = DEMO_BANNER_IMAGE_URLS[idx] if idx < len(DEMO_BANNER_IMAGE_URLS) else None
            data = fetch_image(
                keyword, seed=f"banner-{idx}", size=(1600, 600), url=banner_url, debug=debug
            )
            if not data:
                self.stderr.write(f"  ! no banner image for #{idx}")
                fail += 1
                continue
            _replace_image(banner, "image", data, f"hero-{idx}.jpg")
            self.stdout.write(f"  + banner-{idx} {keyword}")
            ok += 1

        self.stdout.write(self.style.SUCCESS(f"Done. {ok} images fetched, {fail} failed."))
