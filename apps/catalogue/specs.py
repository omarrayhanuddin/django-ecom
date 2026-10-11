"""django-imagekit thumbnail specs, registered by name for templates."""
from imagekit import ImageSpec, register
from imagekit.processors import ResizeToFill, ResizeToFit


class ProductCardThumbnail(ImageSpec):
    processors = [ResizeToFill(400, 400)]
    format = "JPEG"
    options = {"quality": 82}


class ProductDetailThumbnail(ImageSpec):
    processors = [ResizeToFit(900, 900)]
    format = "JPEG"
    options = {"quality": 88}


class ProductMiniThumbnail(ImageSpec):
    processors = [ResizeToFill(80, 80)]
    format = "JPEG"
    options = {"quality": 80}


class BannerThumbnail(ImageSpec):
    processors = [ResizeToFill(1600, 600)]
    format = "JPEG"
    options = {"quality": 85}


class SlideThumbnail(ImageSpec):
    processors = [ResizeToFill(200, 100)]
    format = "JPEG"
    options = {"quality": 80}


register.generator("catalogue:product_card", ProductCardThumbnail)
register.generator("catalogue:product_detail", ProductDetailThumbnail)
register.generator("catalogue:product_mini", ProductMiniThumbnail)
register.generator("promotions:banner", BannerThumbnail)
register.generator("promotions:slide", SlideThumbnail)
