"""Seed demo data for local development.

REFUSES to run unless DEBUG is True, so the demo superuser (admin123) can never
be created on production.
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts.models import CustomUser
from apps.catalogue.models import Brand, Category, Product, ProductImage, Tag
from apps.orders.models import PaymentInstruction
from apps.pages.models import SiteSettings, StaticPage, StoreLocation, SupportInfo
from apps.promotions.models import Banner, Coupon, FlashSale, FlashSaleProduct, HotSale

PALETTE = [(14, 115, 115), (217, 119, 6), (11, 59, 59), (74, 126, 126), (185, 28, 28)]

CATEGORIES = [
    ("ইলেকট্রনিক্স", "Electronics", "fa-solid fa-mobile-screen", True),
    ("মুদি", "Grocery", "fa-solid fa-basket-shopping", True),
    ("পোশাক", "Clothing", "fa-solid fa-shirt", False),
    ("ঘরের জিনিস", "Home Goods", "fa-solid fa-couch", False),
    ("সৌন্দর্য", "Beauty", "fa-solid fa-spray-can-sparkles", False),
]

PRODUCTS = [
    ("স্মার্টফোন X200", "Smartphone X200", 0, "18500", "piece", "electronics", True, True, True, True),
    ("ইয়ারবাডস প্রো", "Earbuds Pro", 0, "3200", "piece", "electronics", True, True, False, True),
    ("পাওয়ার ব্যাংক ২০০০০mAh", "Power Bank 20000mAh", 0, "2400", "piece", "electronics", False, False, True, False),
    ("ব্লুটুথ স্পিকার", "Bluetooth Speaker", 0, "2750", "piece", "electronics", True, False, False, True),
    ("স্মার্ট ওয়াচ", "Smart Watch", 0, "4100", "piece", "electronics", False, True, True, False),
    ("মিনিকেট চাল", "Miniket Rice 5kg", 1, "420", "5kg", "grocery", True, False, True, False),
    ("সয়াবিন তেল", "Soybean Oil 2L", 1, "320", "2L", "grocery", False, False, True, False),
    ("চিনি", "Sugar 1kg", 1, "145", "1kg", "grocery", False, False, False, False),
    ("মশলার প্যাক", "Spice Combo Pack", 1, "560", "500g", "grocery", True, True, False, True),
    ("বাদাম", "Mixed Nuts 500g", 1, "780", "500g", "grocery", False, False, False, True),
    ("পুরুষদের পাঞ্জাবি", "Men's Panjabi", 2, "1450", "piece", "clothing", True, True, False, False),
    ("মহিলাদের শাড়ি", "Women's Saree", 2, "2800", "piece", "clothing", True, False, True, True),
    ("টি-শার্ট", "Cotton T-Shirt", 2, "650", "piece", "clothing", False, True, True, False),
    ("জিন্স প্যান্ট", "Denim Jeans", 2, "1850", "piece", "clothing", False, False, False, False),
    ("সোফা কভার", "Sofa Cover", 3, "1200", "piece", "home", False, False, True, False),
    ("নন-স্টিক প্যান", "Non-stick Pan", 3, "950", "piece", "home", True, False, False, True),
    ("বেডশিট সেট", "Bed Sheet Set", 3, "1650", "piece", "home", True, True, False, False),
    ("ফেসওয়াশ", "Face Wash 100ml", 4, "280", "100ml", "beauty", False, False, True, False),
    ("হেয়ার অয়েল", "Hair Oil 250ml", 4, "340", "250ml", "beauty", True, False, False, True),
    ("বডি লোশন", "Body Lotion 500ml", 4, "520", "500ml", "beauty", False, True, True, True),
]


def make_image(text, color, size=(600, 600)):
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, size[0] - 10, size[1] - 10], outline=(255, 255, 255), width=4)
    draw.text((30, size[1] // 2 - 10), text[:28], fill=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class Command(BaseCommand):
    help = "Seed demo data (DEBUG only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo_data refuses to run when DEBUG is False.")

        self.stdout.write("Seeding demo data...")

        # Users
        if not CustomUser.objects.filter(email="admin@example.com").exists():
            CustomUser.objects.create_superuser(
                email="admin@example.com",
                password="admin123",
                full_name="Demo Admin",
                phone_number="01700000000",
                onboarding_complete=True,
            )
            self.stdout.write("  - superuser admin@example.com / admin123")

        # Site settings
        settings_obj = SiteSettings.load()
        settings_obj.platform_fee_percentage = Decimal("2.5")
        settings_obj.head_office_address = "১২৩ উত্তর এভিনিউ, ধানমন্ডি, ঢাকা"
        settings_obj.head_office_email = "hello@shopbazar.test"
        settings_obj.head_office_phone = "09611000000"
        settings_obj.announcement_bn = "🚚 ডেলিভারি নেই — শোরুম থেকে সংগ্রহ করুন। ফ্ল্যাশ সেলে ৪০% পর্যন্ত ছাড়!"
        settings_obj.announcement_en = "No delivery — collect from showroom. Up to 40% off in flash sale!"
        settings_obj.save()

        support = SupportInfo.load()
        support.phone_number = "09611000000"
        support.support_hours_bn = "শনি–বৃহ: সকাল ১০টা – রাত ৮টা"
        support.support_hours_en = "Sat–Thu: 10am – 8pm"
        support.email = "support@shopbazar.test"
        support.save()

        # Store locations
        if not StoreLocation.objects.exists():
            StoreLocation.objects.create(
                name="প্রধান শোরুম (ধানমন্ডি)", address_bn="১২৩ উত্তর এভিনিউ, ধানমন্ডি, ঢাকা",
                map_embed_url="", phone="09611000000", is_head_office=True, order=0,
            )
            StoreLocation.objects.create(
                name="চট্টগ্রাম শাখা", address_bn="৪৫ আগ্রাবাদ, চট্টগ্রাম",
                phone="09611000001", is_head_office=False, order=1,
            )
            self.stdout.write("  - 2 store locations")

        # Categories
        categories = []
        for order, (bn, en, icon, featured) in enumerate(CATEGORIES):
            cat, _ = Category.objects.get_or_create(
                name_en=en,
                defaults={"name_bn": bn, "icon": icon, "is_featured": featured, "order": order},
            )
            categories.append(cat)
        self.stdout.write(f"  - {len(categories)} categories")

        # Brands / tags
        brand, _ = Brand.objects.get_or_create(name="ShopBazar Select")
        tag, _ = Tag.objects.get_or_create(name="নতুন")

        # Products
        created_products = []
        for i, row in enumerate(PRODUCTS):
            (bn, en, cat_i, price, capacity, ptype, featured, trending, best, top) = row
            sku = f"SBZ-{1000 + i}"
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "name_bn": bn, "name_en": en, "category": categories[cat_i],
                    "brand": brand, "base_price": Decimal(price),
                    "capacity": capacity, "product_type": ptype,
                    "is_featured": featured, "is_trending": trending,
                    "is_best_seller": best, "is_top_rated": top,
                    "stock_quantity": 50, "track_inventory": True,
                    "short_description_bn": f"{bn} — সেরা মানের পণ্য।",
                    "short_description_en": f"{en} — premium quality product.",
                    "full_description": f"<p>{bn} সম্পর্কে বিস্তারিত তথ্য এখানে।</p>",
                },
            )
            product.tags.add(tag)
            if created and not product.images.exists():
                data = None
                try:
                    from apps.pages.demo_images import (
                        DEMO_PRODUCT_IMAGE_URLS,
                        fetch_image,
                        keyword_for,
                    )

                    data = fetch_image(
                        keyword_for(product),
                        seed=sku,
                        size=(800, 800),
                        url=DEMO_PRODUCT_IMAGE_URLS.get(sku),
                    )
                except Exception:
                    data = None
                if not data:
                    data = make_image(en, PALETTE[i % len(PALETTE)])
                pimg = ProductImage(product=product, alt_text=en, is_primary=True, order=0)
                pimg.image.save(f"{sku}.jpg", ContentFile(data), save=True)
            created_products.append(product)
        self.stdout.write(f"  - {len(created_products)} products")

        # Flash sale
        if not FlashSale.objects.filter(name="বিশেষ ফ্ল্যাশ সেল").exists():
            sale = FlashSale.objects.create(
                name="বিশেষ ফ্ল্যাশ সেল",
                start_time=timezone.now(),
                end_time=timezone.now() + timedelta(days=2),
                is_active=True,
            )
            for product, pct in zip(created_products[:5], ["40", "35", "30", "25", "20"]):
                sale_price = (product.base_price * (Decimal("100") - Decimal(pct)) / 100).quantize(Decimal("0.01"))
                FlashSaleProduct.objects.create(
                    flash_sale=sale, product=product,
                    discount_percentage=Decimal(pct), sale_price=sale_price,
                )
            self.stdout.write("  - flash sale with 5 products")

        # Hot sales
        for product, pct in zip(created_products[5:8], ["15", "20", "25"]):
            HotSale.objects.get_or_create(
                product=product,
                defaults={"discount_percentage": Decimal(pct), "label": "Hot Deal", "is_active": True},
            )
        self.stdout.write("  - 3 hot sale products")

        # Coupon
        Coupon.objects.get_or_create(
            code="WELCOME10",
            defaults={
                "discount_type": Coupon.DiscountType.PERCENTAGE,
                "discount_value": Decimal("10"),
                "minimum_order_value": Decimal("500"),
                "max_uses": 1000,
                "per_user_limit": 1,
                "is_active": True,
            },
        )
        self.stdout.write("  - coupon WELCOME10")

        # Banners
        if not Banner.objects.exists():
            for idx, (title, color) in enumerate(
                [("বিশাল ছাড়!", PALETTE[1]), ("নতুন কালেকশন", PALETTE[0])]
            ):
                data = None
                try:
                    from apps.pages.demo_images import (
                        DEMO_BANNER_IMAGE_URLS,
                        DEMO_BANNER_KEYWORDS,
                        fetch_image,
                    )

                    keyword = DEMO_BANNER_KEYWORDS[idx % len(DEMO_BANNER_KEYWORDS)]
                    banner_url = (
                        DEMO_BANNER_IMAGE_URLS[idx] if idx < len(DEMO_BANNER_IMAGE_URLS) else None
                    )
                    data = fetch_image(keyword, seed=f"banner-{idx}", size=(1600, 600), url=banner_url)
                except Exception:
                    data = None
                if not data:
                    data = make_image(title, color, (1600, 600))
                b = Banner(
                    title_bn=title, title_en=title, subtitle_bn="শোরুম থেকে সংগ্রহ করুন",
                    position=Banner.Position.HERO, order=idx, is_active=True,
                )
                b.image.save(f"hero-{idx}.jpg", ContentFile(data), save=True)
            self.stdout.write("  - 2 hero banners")

        # Payment instructions
        for name, number, acc in [
            ("বিকাশ", "01700000000", "ShopBazar"),
            ("নগদ", "01800000000", "ShopBazar"),
            ("ব্যাংক ট্রান্সফার", "1234567890", "ShopBazar Ltd"),
        ]:
            PaymentInstruction.objects.get_or_create(
                method_name=name,
                defaults={"account_number": number, "account_name": acc,
                          "instructions_bn": f"{name} নম্বরে পেমেন্ট করে TrxID দিন।",
                          "is_active": True},
            )

        # Static pages
        StaticPage.objects.get_or_create(
            slug="about",
            defaults={"title_bn": "আমাদের সম্পর্কে", "title_en": "About Us",
                      "content": "<p>ShopBazar একটি বাংলাদেশি রিটেইল প্ল্যাটফর্ম।</p>", "is_published": True},
        )
        StaticPage.objects.get_or_create(
            slug="privacy",
            defaults={"title_bn": "প্রাইভেসি পলিসি", "title_en": "Privacy Policy",
                      "content": "<p>আমরা আপনার তথ্য সুরক্ষিত রাখি। IP ও ইউজার-এজেন্ট ১২ মাস সংরক্ষিত হয়।</p>",
                      "is_published": True},
        )
        StaticPage.objects.get_or_create(
            slug="terms",
            defaults={"title_bn": "শর্তাবলী", "title_en": "Terms and Conditions",
                      "content": "<p>সেবা ব্যবহারের শর্তাবলী।</p>", "is_published": True},
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
