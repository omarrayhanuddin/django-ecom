# E-Commerce Web Application — Build Specification (v2)

> Revised from `ecommerce-agent-prompt.md`. This version resolves the blocking contradictions, corrects outdated configuration against current releases, declares every dependency, and makes the money rules explicit. Sections marked **[CHANGED]** differ from v1; **[NEW]** are additions.

**Target:** Bangladeshi retail storefront. Physical products only. **No delivery** — customers collect from a showroom. Payment is **manual** (bank transfer / bKash / Nagad / Rocket), verified by the owner. Bilingual UI (Bangla + English). Admin must be fully usable without coding knowledge.

---

## 0. Locked Decisions (from review)

| # | Decision | Choice |
|---|---|---|
| 1 | Bilingual storage | **Dual fields** (`name_bn`, `name_en`, etc.) + `display_name` property. No parler. |
| 2 | Homepage carousel models | **Delete `apps/dealership`.** Use `promotions.Banner` only. |
| 3 | Platform fee basis | On **`subtotal − discount`** (post-discount). |
| 4 | Next-purchase coupon timing | Issued **only when payment is verified** (`PAID`/`COMPLETED`). |
| 5 | Admin theme | **`django-unfold`** (not jazzmin). |
| 6 | Thumbnails | **`django-imagekit`** (not sorl-thumbnail). |
| 7 | Product stock | Add **`stock_quantity` + `track_inventory` at product level**; variants may override. |
| 8 | Rich text editor | **`django-ckeditor`**, **sanitized with `nh3`** on save. |

Additional decisions applied (from review §5–§7):
- **allauth** uses current settings (`ACCOUNT_LOGIN_METHODS`, `ACCOUNT_SIGNUP_FIELDS`).
- **Channels 4** with `daphne` in `INSTALLED_APPS`.
- Guest orders get a **non-guessable `public_token`** for tracking.
- **`CouponRedemption`** model for per-user usage + atomic limits.
- **Pickup store** selected at checkout.
- Canonical **price-resolution order** and **money rounding** (see §4).
- Accent/sale/footer colors corrected to pass **WCAG AA** (see §18).

---

## 1. Tech Stack (Corrected) **[CHANGED]**

- **Backend:** Python 3.11+, Django 5.x
- **Frontend:** Django Templates, HTMX, Alpine.js (minimal), Bootstrap 5
- **Database:** PostgreSQL (SQLite for local dev only)
- **Auth:** `django-allauth` (Google + Facebook OAuth2 + email/password)
- **Payments:** Manual confirmation workflow (no gateway)
- **Real-time:** Django Channels 4 + Redis (live visitor count) — **requires `daphne`**
- **Caching:** Redis (`django-redis`)
- **Search:** Django ORM + `django-filter`
- **Images:** `Pillow` + `django-imagekit`
- **Admin:** `django-unfold` (+ `django-admin-sortable2`, `django-solo`)
- **Task queue:** Celery + Redis
- **Rich text:** `django-ckeditor` + `nh3` sanitizer
- **Static/Media:** WhiteNoise + local media (S3-ready stub)
- **Config:** `django-environ`

---

## 2. Project Structure (Corrected) **[CHANGED]**

`apps/dealership/` is removed. Added the missing wiring files.

```
project_root/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── __init__.py          # imports celery_app  [NEW]
│   ├── celery.py            # Celery app + beat schedule  [NEW]
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py              # ProtocolTypeRouter (http + websocket)  [CHANGED]
│   └── routing.py           # (optional) aggregated websocket routes  [NEW]
├── apps/
│   ├── accounts/
│   ├── catalogue/
│   ├── promotions/          # includes Banner (homepage carousel)  [CHANGED]
│   ├── cart/
│   ├── orders/
│   ├── analytics/
│   │   ├── middleware.py    # SiteVisit logging  [NEW]
│   │   ├── consumers.py     # LiveVisitorConsumer  [NEW]
│   │   └── routing.py       # websocket_urlpatterns  [NEW]
│   └── pages/
├── templates/
│   ├── base.html
│   ├── home/index.html
│   ├── partials/            # HTMX + shared partials
│   └── <app>/
├── static/
│   ├── css/  (theme.css, components.css, overrides.css)
│   ├── js/   (theme.js, cart.js)
│   └── images/
├── media/
├── pyproject.toml           # uv project: dependencies + dev group
├── uv.lock                  # exact resolved versions (commit this)
├── tests/                   # pytest suite
├── scripts/                 # smoke.py, flow_test.py
├── manage.py
├── .env.example
├── .gitignore               # [NEW]
├── pytest.ini               # [NEW]
├── docker-compose.yml       # Redis + PostgreSQL
├── Dockerfile               # [NEW]
└── README.md
```

> **Tooling note:** dependencies are managed with **uv** (`uv init` + `uv add`),
> not `requirements/*.txt`. See §12 and §18.

## 3. Core Utilities (Build These First) **[NEW]**

Create `apps/common/` (or a `core` module) with helpers used across apps.

### 3.1 Money
```python
# apps/common/money.py
from decimal import Decimal, ROUND_HALF_UP

def round_money(value) -> Decimal:
    """All BDT amounts are rounded HALF_UP to 2 dp. Use everywhere."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### 3.2 Bilingual display
```python
# apps/common/mixins.py
class BilingualNameMixin(models.Model):
    name_bn = models.CharField(max_length=255, blank=True)
    name_en = models.CharField(max_length=255, blank=True)

    @property
    def display_name(self):
        return self.name_bn or self.name_en or ""

    class Meta:
        abstract = True
```
Every admin-editable bilingual string uses `_bn` / `_en` fields and exposes a `display_*` property. **Fallback:** Bangla first, then English.

### 3.3 Sanitizer
```python
# apps/common/sanitize.py
import nh3

SAFE_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li",
    "a", "h2", "h3", "h4", "blockquote", "img",
}
SAFE_ATTRS = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height"},
}

def clean_html(raw: str) -> str:
    return nh3.clean(raw, tags=SAFE_TAGS, attributes=SAFE_ATTRS,
                     link_rel="noopener noreferrer", url_schemes={"http", "https"})
```
Call `clean_html()` in `Model.save()` for every RichTextField (`full_description`, `StaticPage.content`, etc.). `style` is never allowed.

---

## 4. Money, Pricing & Fee Rules (Single Source of Truth) **[CHANGED]**

### 4.1 Price resolution (first match wins)
```
1. ProductVariant.price_override   (if a variant is selected)
2. Active FlashSaleProduct.sale_price
3. Active HotSale percentage       -> base_price * (1 - pct/100)
4. Product.discount_price          (if set and < base_price)
5. Product.base_price
```
- **Discounts never stack.** Only one applies.
- A product's effective "was" price is always `base_price`.
- `% OFF` shown = `round((base_price - effective) / base_price * 100)`, only if > 0.
- Pricing is computed by a single method `Product.get_effective_price()` and reused by cart, listing, and checkout.

### 4.2 Platform (service) fee
- Source of truth: **`SiteSettings.platform_fee_percentage`** (DB). `.env` value is used only to seed the singleton on first migrate. **[CHANGED]**
- Formula (**post-discount**):
```python
discount      = coupon discount on the eligible items        # see 4.3
taxable       = round_money(subtotal - discount)
platform_fee  = round_money(taxable * Decimal(platform_fee_percentage) / Decimal("100"))
total         = round_money(taxable + platform_fee)
```
- `platform_fee_percentage` is **snapshotted** onto the order at checkout (`Order.platform_fee_percentage`).

### 4.3 Coupon discount
- `PERCENTAGE`: `discount = taxable_eligible * pct/100`, optionally capped by `max_discount_amount`. **[NEW]**
- `FIXED_AMOUNT`: `discount = min(value, subtotal)`.
- Never negative; applied before the platform fee.

### 4.4 Rounding
All money passes through `round_money()` (2 dp, `ROUND_HALF_UP`). `OrderItem.line_total = round_money(unit_price * quantity)`.

---

## 5. App-by-App Specifications

### 5.1 `apps/accounts/` **[CHANGED]**

**Models**
```python
class CustomUser(AbstractBaseUser, PermissionsMixin):      # PermissionsMixin REQUIRED
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=11, blank=True)  # BD: ^01[3-9]\d{8}$
    full_name = models.CharField(max_length=255)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False)   # [NEW] explicit gate

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()   # create_user / create_superuser

class UserProfile(models.Model):    # OneToOne(CustomUser)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

class Address(models.Model):        # FK(CustomUser, related_name="addresses")
    label = models.CharField(choices=LABELS)   # HOME/OFFICE/OTHER
    division, district, upazila, street_address
    is_default = models.BooleanField(default=False)
```
- Email is `USERNAME_FIELD`; **no username field** (`ACCOUNT_USER_MODEL_USERNAME_FIELD = None`).
- Onboarding gate is `onboarding_complete` (NOT "phone blank").
- On first social login with `onboarding_complete == False` → redirect to onboarding modal (HTMX) collecting phone + a default address.

**Features**
- Registration form: full name, email, phone, one address — single step.
- `Address.is_default`: only one per user (enforce in `save()`).
- Profile page: edit profile, manage addresses, order history.

**URLs:** `/accounts/login/`, `/accounts/register/`, `/accounts/onboarding/`, `/accounts/profile/`, `/accounts/addresses/`

---

### 5.2 `apps/catalogue/` **[CHANGED]**

**Models**
```python
class Category(BilingualNameMixin):
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children")
    icon = models.CharField(max_length=64, blank=True)   # Font Awesome class
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

class Brand(models.Model):
    name, slug, logo

class Tag(models.Model):
    name, slug

class Product(BilingualNameMixin):
    slug = models.SlugField(unique=True)
    sku = models.CharField(max_length=64, unique=True)      # [NEW] admin searches by this
    category = models.ForeignKey(Category, on_delete=PROTECT)
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    short_description_bn/_en = models.CharField(max_length=300, blank=True)
    full_description = models.TextField()                    # CKEditor; sanitized via nh3
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(null=True, blank=True, ...)
    availability = models.CharField(choices=[IN_STOCK, PRE_ORDER, UPCOMING])
    capacity = models.CharField(max_length=50, blank=True)   # free text kept for display
    product_type = models.CharField(max_length=50, blank=True)  # [CHANGED] -> see note
    stock_quantity = models.PositiveIntegerField(default=0)  # [NEW]
    track_inventory = models.BooleanField(default=True)      # [NEW]
    is_featured / is_trending / is_best_seller / is_top_rated = BooleanField(default=False)
    created_at, updated_at
    meta_title, meta_description

    def get_effective_price(self): ...   # §4.1
    @property
    def in_stock(self):
        return (not self.track_inventory) or self.stock_quantity > 0

class ProductImage(models.Model):
    product = FK(related_name="images")
    image, alt_text, is_primary, order

class ProductVariant(models.Model):
    product = FK(related_name="variants")
    name, sku = CharField(unique=True)
    price_override = DecimalField(null=True, blank=True)
    stock_quantity = PositiveIntegerField(default=0)   # overrides product when present

class ProductReview(models.Model):
    product, user, rating (1-5), comment, created_at
    is_approved = models.BooleanField(default=False)   # [CHANGED] default False
    class Meta:
        constraints = [UniqueConstraint(fields=["product", "user"], name="uniq_review_per_user")]
```

> **`capacity` / `product_type` decision:** keep both as controlled values. Define module-level `CAPACITY_CHOICES` and `PRODUCT_TYPE_CHOICES` in `constants.py` and validate against them, so the filter sidebar is reliable. Free-text capacity is no longer filterable.

**Features**
- HTMX filter sidebar: category tree, price range, availability, capacity, quantity (stock) range, product type, brand. Sorting: price ↑↓, newest, best-rated, popularity.
- Product detail: image gallery, HTMX add-to-cart, star rating, related products.
- Admin: CSV import (`django-import-export`) **and** an image-upload action with auto-thumbnails.

**URLs:** `/products/`, `/products/<slug>/`, `/categories/<slug>/`

### 5.3 `apps/promotions/` **[CHANGED]**

**Models**
```python
class FlashSale(models.Model):
    name
    start_time, end_time
    is_active = BooleanField(default=True)
    products = M2M(Product, through="FlashSaleProduct")

class FlashSaleProduct(models.Model):
    flash_sale = FK
    product = FK
    discount_percentage = Decimal
    sale_price = Decimal            # STORED snapshot (decided: stored, not computed)
    UniqueConstraint(flash_sale, product)

class HotSale(models.Model):
    product = FK
    discount_percentage = Decimal
    label = CharField            # e.g. "Hot Deal"
    is_active = BooleanField

class Coupon(models.Model):
    code = CharField(unique=True)          # stored UPPERCASE
    discount_type = choices[PERCENTAGE, FIXED_AMOUNT]
    discount_value = Decimal
    max_discount_amount = Decimal(null=True, blank=True)   # [NEW] cap for % coupons
    minimum_order_value = Decimal(default=0)
    max_uses = PositiveIntegerField(null=True)   # global cap; null = unlimited
    used_count = PositiveIntegerField(default=0)
    per_user_limit = PositiveIntegerField(default=1)        # [NEW]
    valid_from, valid_to
    is_active
    is_next_purchase = BooleanField(default=False)
    user = FK(CustomUser, null=True, blank=True)   # null = public

class CouponRedemption(models.Model):        # [NEW] anti-abuse
    coupon = FK(related_name="redemptions")
    user = FK(null=True)
    order = OneToOne(Order)
    redeemed_at
    UniqueConstraint(coupon, user)   # for user-specific / per_user_limit=1

class Banner(models.Model):                  # single homepage carousel model
    title_bn/_en, subtitle_bn/_en (blank)
    image, link_url
    position = choices[TOP_SLIDER, HERO]     # [CHANGED] "DEALERSHIP" removed
    order = PositiveIntegerField(default=0)
    is_active
```
> `dealsership` app is deleted; `Banner.position = HERO` is the main homepage carousel. Rename the old `DEALERSHIP` choice to `HERO` to avoid car-dealership confusion.

**Features**
- Flash sale countdown (Alpine.js ticking from a server-provided `end_time`).
- `% OFF` badge on cards from `FlashSaleProduct.discount_percentage` / HotSale.
- **Next-purchase coupon** generated by a Celery task **triggered when an admin marks payment `PAID`** (or order `COMPLETED`) — code `NEXT-<ORDER_NUMBER>`, 5% off, 30 days, `per_user_limit=1`, tied to that user.

**URLs:** `/promotions/flash-sale/`, `/promotions/hot-deals/`

---

### 5.4 `apps/cart/`

**Models**
```python
class Cart(models.Model):
    user = FK(null=True)               # null for guest
    session_key = CharField(blank=True, db_index=True)
    created_at, updated_at
    # constraint: exactly one of user / session_key set

class CartItem(models.Model):
    cart = FK(related_name="items")
    product = FK
    variant = FK(null=True, blank=True)
    quantity = PositiveIntegerField(default=1)
    unit_price = Decimal                # snapshot at add-time, re-validated at checkout
    UniqueConstraint(cart, product, variant, name="uniq_cart_line")   # [NEW]
```

**Rules**
- Guest cart keyed by `session_key`; merged into the user's cart on login/registration.
- **Merge collision policy** **[NEW]:** if a product/variant exists in both, keep `max(quantity)` (clamped to stock); do not sum duplicates.
- **Price re-validation at checkout:** recompute using `get_effective_price()`; if it changed, keep the lower and notify. Never charge a stale `unit_price`.
- **Stock check** on add and at checkout; block if `track_inventory` and quantity > stock.

**Features (HTMX)**
- Add to cart + live badge; inline +/- quantity; remove item; slide-in drawer (Alpine.js).
- Summary: subtotal, coupon discount, service fee (post-discount; §4.2), total.
- Coupon input with HTMX validation (rate-limited).

---

### 5.5 `apps/orders/` **[CHANGED]**

**Models**
```python
class Order(models.Model):
    order_number = CharField(unique=True)     # ORD-YYYYMMDD-XXXX (generated with DB-unique retry)
    public_token = UUIDField(default=uuid4, unique=True, editable=False)   # [NEW] guest tracking
    user = FK(null=True)
    guest_email = EmailField(blank=True)
    guest_phone = CharField(blank=True)
    pickup_store = FK("pages.StoreLocation", null=True, blank=True)        # [NEW]
    status = choices[PENDING, CONFIRMED, PROCESSING, READY, CANCELLED, COMPLETED]
    payment_status = choices[UNPAID, AWAITING_VERIFICATION, PAID, REFUNDED]
    payment_method = choices[BANK_TRANSFER, BKASH, NAGAD, ROCKET, OTHER]
    payment_reference = CharField(blank=True)   # TrxID / bank ref
    # manual-payment audit trail  [NEW]
    paid_at = DateTimeField(null=True, blank=True)
    verified_by = FK(CustomUser, null=True, related_name="verified_orders")
    verified_at = DateTimeField(null=True, blank=True)
    platform_fee_percentage = Decimal   # snapshot
    platform_fee_amount = Decimal       # computed
    subtotal, discount_amount, total_amount = Decimal
    coupon = FK(Coupon, null=True)
    note = TextField(blank=True)
    created_at, updated_at
    # constraint: payment_reference non-empty must be unique per method
    UniqueConstraint(fields=["payment_method", "payment_reference"], condition=~Q(payment_reference=""))

class OrderItem(models.Model):
    order = FK(related_name="items")
    product = FK(on_delete=PROTECT)
    variant = FK(null=True, on_delete=SET_NULL)
    product_name = CharField   # snapshot
    unit_price = Decimal       # snapshot
    quantity, line_total

class PaymentInstruction(models.Model):
    method_name, account_number, account_name, instructions_bn/_en, is_active
```

**Status transition rules** **[NEW]** (enforce in `Order.transition()`):
```
PENDING    -> CONFIRMED, CANCELLED
CONFIRMED  -> PROCESSING, CANCELLED
PROCESSING -> READY, CANCELLED
READY      -> COMPLETED
COMPLETED  -> (terminal)
```
Payment: `UNPAID -> AWAITING_VERIFICATION -> PAID -> REFUNDED`.

**Checkout flow**
1. Cart review.
2. Customer info (pre-filled if logged in).
3. **No delivery address.** Show notice: *"আপনাকে আমাদের শোরুম থেকে পণ্য সংগ্রহ করতে হবে।"*
4. **Select pickup store** (from `StoreLocation`). **[NEW]**
5. Payment method → show matching `PaymentInstruction`.
6. Customer enters payment reference (bKash TrxID / bank ref).
7. Place order → `PENDING` / `AWAITING_VERIFICATION`.
8. Confirmation page (works for guests via `public_token` link).
9. Admin verifies → `PAID` → triggers `order_paid` task → email + **next-purchase coupon**.

**URLs:** `/cart/`, `/checkout/`, `/orders/`, `/orders/<order_number>/`, `/orders/track/<public_token>/` **[NEW]**

### 5.6 `apps/analytics/` **[CHANGED]**

**Models**
```python
class SiteVisit(models.Model):
    session_key = CharField(unique=True)   # one row per session
    ip_address = GenericIPAddressField(null=True)
    user_agent = TextField(blank=True)
    visited_at = DateTimeField(auto_now_add=True)
    page_url = CharField(blank=True)
```
- Middleware logs one `SiteVisit` per new session (not per page).
- **Privacy:** disclose IP/UA logging in the Privacy Policy; define retention (default: purge rows older than 12 months via Celery).

**Live visitor count (WebSocket)**
- Redis sorted set `live_visitors`: member = `session_key`, score = timestamp.
- **Multi-tab correct** **[NEW]:** maintain a **per-session ref count** in Redis (`live_visitors:refs` hash). Increment on connect, decrement on disconnect; only remove the session from the set when its ref count hits 0.
- Broadcast the count `len(live_visitors)` to group `visitors` on every change.
- Stale cleanup: Celery task every 60s removes members with score older than 5 minutes.

**HTMX fallback:** `#live-count` uses `hx-get="/analytics/live-count/" hx-trigger="every 30s"`.

### 5.7 `apps/pages/`

**Models:** `StaticPage` (title_bn/_en, slug, content, is_published), `StoreLocation` (name, address_bn/_en, map_embed_url, phone, is_head_office, order), `SupportInfo` (singleton-ish), `SiteSettings` (singleton via `django-solo`).

`SiteSettings`: `site_name_bn/_en`, `platform_fee_percentage`, `head_office_address`, `head_office_email`, `head_office_phone`, `facebook_url`, `youtube_url`, `instagram_url`.

Pages: About (`/about/`), Privacy (`/privacy/`), Terms (`/terms/`), Brands (`/brands/`), Stores (`/stores/`), Contact (`/contact/`).

---

## 6. Homepage (`templates/home/index.html`)

Sections **in order**:
1. Nav (logo, search, cart, login)
2. Announcement bar (scrolling; enable per `SiteSettings`/Banner)
3. **HERO carousel** (`Banner.position=HERO`)
4. Featured categories (icon grid, 6–8)
5. Flash sale (countdown + `%` badges)
6. Hot deals
7. Trending products (horizontal scroll)
8. Top-rated products
9. Best sellers
10. Recommended for you (auth-aware)
11. **Featured products grid** with a "View all products" link → `/products/` **[CHANGED]** — the full paginated/filtered catalogue lives on `/products/`, not the homepage (avoids a huge first load).
12. Visitor counter (total + live)
13. Footer

---

## 7. HTMX Interaction Patterns (Corrected) **[CHANGED]**

**Global CSRF + method handling** — add to `<body>` in `base.html`:
```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
```
And install a small middleware so Django parses form data for `PUT`/`PATCH`/`DELETE` (Django only parses `POST`):
```python
# apps/common/middleware.py
class HtmxMethodMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.method in {"PUT", "PATCH", "DELETE"}:
            request.method = "POST"      # keep real method in request.META["HTTP_X_HTTP_METHOD_OVERRIDE"]
        return self.get_response(request)
```

| Interaction | Pattern |
|---|---|
| Add to cart | `hx-post="/cart/add/" hx-target="#cart-drawer" hx-swap="innerHTML"` + `HX-Trigger: cartUpdated` |
| Remove item | `hx-delete="/cart/item/{id}/"` (middleware-parsed) `hx-target="#cart-items" hx-swap="outerHTML"` |
| Update quantity | `hx-patch="/cart/item/{id}/" hx-trigger="change" hx-target="#cart-summary"` |
| Product filter | `hx-get="/products/?{params}" hx-target="#product-grid" hx-push-url="true"` |
| Coupon apply | `hx-post="/cart/apply-coupon/" hx-target="#coupon-result"` (rate-limited) |
| Live count fallback | `hx-get="/analytics/live-count/" hx-trigger="every 30s" hx-target="#live-count"` |
| Search suggest | `hx-get="/search/suggest/?q=" hx-trigger="keyup changed delay:300ms"` → returns **HTML partial** (not JSON) |

**Multi-target updates:** a single add-to-cart response updates the drawer; use `HX-Trigger` events (`cartUpdated`, `couponApplied`) plus `hx-trigger="cartUpdated from:body"` on the badge/summary so they refresh too. Do not target only `#cart-count`.

Handlers that mutate (cart/coupon/checkout) must re-render every affected partial in one response (drawer + badge + summary).

---

## 8. URL Structure (Corrected) **[CHANGED]**

```
/                              home
/products/                     list + filters
/products/<slug>/              detail
/categories/<slug>/            category list
/search/                       results
/search/suggest/               HTMX suggestions (HTML partial)
/cart/                         cart page
/cart/add/                     HTMX add
/cart/item/<id>/               HTMX update/delete
/cart/apply-coupon/            HTMX coupon
/checkout/                     checkout steps
/orders/                       order list (auth)
/orders/<order_number>/        order detail (owner only)
/orders/track/<public_token>/  guest order tracking            [NEW]
/accounts/login/  register/  logout/
/accounts/onboarding/          social onboarding form          [NEW]
/accounts/profile/             auth
/accounts/addresses/           auth
/promotions/flash-sale/  hot-deals/
/about/ /privacy/ /terms/ /brands/ /stores/ /contact/
/analytics/live-count/         HTMX fallback
/ws/visitors/                  WebSocket
/admin/
```
> `/search/` is owned by `apps/catalogue` (no separate search app).

## 9. Django Admin (`django-unfold`) **[CHANGED]**

Register/configure:
- **ProductAdmin:** list_display (thumbnail, name, sku, category, effective price, stock badge), `ProductImageInline`, `ProductVariantInline`; search by name/`sku`; filter category/brand/availability; CSV import/export actions.
- **OrderAdmin:** status/payment colour badges; `OrderItemInline`; action **"Mark as PAID + send confirmation"** (sets `payment_status=PAID`, `paid_at`, `verified_by/at`, fires `order_paid` task); payment_reference shown read-only.
- **FlashSaleAdmin:** inline `FlashSaleProduct` with percentage.
- **CouponAdmin:** shows `used_count` / `redemptions`; "copy code" action; prevent editing `used_count` manually.
- **SiteSettingsAdmin:** singleton (`django-solo`), one row only.
- **BannerAdmin:** drag-to-reorder (`django-admin-sortable2`), preview thumbnail.
- **LiveVisitorDisplay:** read-only custom admin view reading the Redis count.

> Verify `unfold` + `admin-sortable2` + `solo` render together; unfold supports both, but test before committing.

---

## 10. Authentication (`django-allauth`, current settings) **[CHANGED]**

```python
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {"SCOPE": ["profile", "email"], "AUTH_PARAMS": {"access_type": "online"}},
    "facebook": {"METHOD": "oauth2", "SCOPE": ["email", "public_profile"]},
}
```
- Pin `django-allauth>=65.5`.
- **Onboarding:** a middleware (or allauth `ACCOUNT_ADAPTER` + `get_login_redirect_url`) redirects authenticated users with `onboarding_complete == False` to `/accounts/onboarding/`.
- **Note:** Facebook's `email` permission typically requires app review — treat as a launch dependency.

---

## 11. Key Django Settings **[CHANGED]**

```python
# config/settings/base.py
INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "daphne",                          # MUST precede staticfiles (Channels 4)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "channels",
    "django_celery_beat",              # [NEW] DB-driven beat schedule
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "django_filters",
    "imagekit",                        # [CHANGED]
    "ckeditor",                        # [CHANGED]
    "django_htmx",
    "import_export",                   # [NEW]
    "solo",
    "adminsortable2",
    # local apps
    "apps.accounts", "apps.catalogue", "apps.promotions", "apps.cart",
    "apps.orders", "apps.analytics", "apps.pages",
]

AUTH_USER_MODEL = "accounts.CustomUser"
SITE_ID = 1

LANGUAGE_CODE = "bn"                   # [NEW]
TIME_ZONE = "Asia/Dhaka"               # [NEW]
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [environ["REDIS_URL"]]},   # [CHANGED] from env, not hardcoded
    }
}
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": environ["REDIS_URL"],
    }
}

# Celery
CELERY_BROKER_URL = environ["REDIS_URL"]
CELERY_RESULT_BACKEND = environ["REDIS_URL"]
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = "Asia/Dhaka"

# Static/media (Django 5 STORAGES)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"; MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "/static/"; STATIC_ROOT = BASE_DIR / "staticfiles"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"  # local
LOGIN_REDIRECT_URL = LOGOUT_REDIRECT_URL = "/"
RATELIMIT_VIEW = "apps.cart.views.ratelimited"
CKEDITOR_CONFIGS = {"default": {"toolbar": "Custom",
    "toolbar_Custom": [["Bold","Italic","Underline"],["BulletedList","NumberedList"],
                       ["Outdent","Indent"],["Link","Unlink"],["RemoveFormat"]]}}
```

`config/asgi.py` (Channels 4 — HTTP must be registered):
```python
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.analytics import routing as analytics_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(URLRouter(analytics_routing.websocket_urlpatterns)),
})
```

`config/celery.py` + `config/__init__.py`:
```python
# config/celery.py
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# config/__init__.py
from .celery import app as celery_app
__all__ = ("celery_app",)
```

**Celery tasks (define in `apps/*/tasks.py`):**
- `deactivate_expired_flash_sales` — every 5 min; sets `FlashSale.is_active=False` when `end_time` passed.
- `cleanup_stale_live_visitors` — every 60 s.
- `purge_old_site_visits` — daily.
- `send_order_paid_email` + `issue_next_purchase_coupon` — on `order_paid` (fired when admin marks PAID).
- `send_order_confirmation_email` — on placement.

---

## 12. Dependencies (uv) **[CHANGED — v2.1]**

Dependencies are declared in **`pyproject.toml`** and locked in **`uv.lock`**
(managed with `uv add`, no `requirements/*.txt`).

`[project].dependencies`:
```
Django>=5.0,<6.0            daphne>=4.0            django-imagekit
django-environ             channels-redis          django-ckeditor
channels                   django-allauth[socialaccount]>=65.5
django-filter              nh3                    Pillow
celery                     django-celery-beat      redis
django-redis               django-unfold           django-admin-sortable2
django-solo                django-htmx             django-import-export
django-ratelimit           whitenoise             gunicorn
```
`[dependency-groups].dev`:
```
pytest, pytest-django
```
Production adds PostgreSQL support via `uv add "psycopg[c]"` when deploying.

---

## 13. `.env.example` (Corrected) **[CHANGED]**

```
SECRET_KEY=change-me
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local
DATABASE_URL=postgres://user:password@localhost:5432/ecommerce_db
REDIS_URL=redis://localhost:6379/0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@yoursite.com
# Platform fee is owned by SiteSettings in the DB. This seeds the singleton on first migrate only.
PLATFORM_FEE_PERCENTAGE=2.5
```
> Do **not** keep `PLATFORM_FEE_PERCENTAGE` as a runtime setting; `SiteSettings.platform_fee_percentage` wins.

---

## 14. Seed Data — `python manage.py seed_demo_data` **[CHANGED]**

- Guard: **refuse to run when `DEBUG is False`** (protects prod from `admin123`). **[NEW]**
- 5 categories, 2 featured; 20 products across categories (with product-level stock); 1 active flash sale (5 products, 20–40% off); 3 hot-sale products; coupon `WELCOME10` (10% off, min 500 BDT, `per_user_limit=1`); 2 `Banner` HERO slides; default `SiteSettings` (fee 2.5%); 2 `StoreLocation` (one head office); demo superuser `admin@example.com` / `admin123`.

## 15. Business Rules (Consolidated) **[CHANGED]**

1. **No delivery.** Checkout never asks for/stores a delivery address; show the pickup notice and require a **pickup store**.
2. **Platform fee is mandatory** and computed **post-discount** (§4.2), snapshotted on the order.
3. **Payment is manual.** Customer enters a reference; admin verifies. Only one order per `(payment_method, payment_reference)`.
4. **Next-purchase coupon** (`NEXT-<ORDER_NUMBER>`, 5% off, 30 days, `per_user_limit=1`) is issued **when payment is verified**, then shown on the order page and emailed.
5. **Guest checkout allowed**; a `public_token` link lets guests track their order. **Cart/order merging on registration requires email verification** before attaching guest orders.
6. **Flash sale expiry:** Celery beat deactivates expired sales every 5 minutes.
7. **Recommended products:** auth + prior orders → same categories; guest → best sellers.
8. **Bilingual:** every admin-editable text has `_bn`/`_en`; fallback Bangla → English.

---

## 16. Security Checklist **[CHANGED]**

- **HTMX:** global `X-CSRFToken` header + `HtmxMethodMiddleware` (§7).
- Login required: `/orders/`, `/accounts/profile/`, `/accounts/addresses/`.
- **Order ownership:** authenticated users see only their own; guests only via `public_token` (never by sequential `order_number`).
- **Rate-limit** coupon apply + search suggest + onboarding (`django-ratelimit`).
- **Sanitize** all rich text with `nh3.clean()` on save; disallow `style`/`script`; `url_schemes={"http","https"}`.
- **Image uploads:** validate content type + max size; store under generated names.
- **Payment reference uniqueness** to stop TrxID replay.
- Production: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`.
- Consider `django-axes` for admin brute-force protection. Optional admin IP allowlist at nginx.
- Guard `seed_demo_data` against non-DEBUG runs.

---

## 17. Design System (Corrected) **[CHANGED]**

Same token approach as v1, with **contrast fixes** and a corrected Bootstrap bridge.

### 17.1 Contrast fixes (WCAG AA)
v1 failed AA in several places. Corrections:

| Token / use | v1 | Problem | v2 |
|---|---|---|---|
| `--color-accent-text` (text ON amber) | `#FFFFFF` | white on `#D97706` ≈ 3.2:1 (fails) | **`#3A1D00`** (dark ink on amber) |
| `--color-sale` (light mode) | `#DC2626` | white ≈ 4.0:1 (fails) | **`#B91C1C`** (white ≈ 5.9:1) |
| `[data-theme=dark] --color-sale` | `#EF4444` | white ≈ 3.8:1 (fails) | keep `#EF4444` but set **`--color-sale-text: #0F1E1E`** (dark ink) |
| `--color-footer-heading` | `rgba(255,255,255,.40)` | ≈ 3.3:1 (fails) | **`rgba(255,255,255,.70)`** |
| `--color-footer-support-phone` | accent `#D97706` on dark | ≈ 3.8:1 | use palette token **`--color-footer-accent: #F5B94A`** |

Rule: **bright colors in dark mode get dark ink** (`--color-primary-text`, `--color-accent-text`, `--color-sale-text`); light mode keeps white ink on darkened colors.

### 17.2 Light tokens (corrected highlights)
```css
:root {
  --color-primary: #0E7373; --color-primary-hover: #0B5C5C;
  --color-primary-deep: #0B3B3B; --color-primary-light: #E6F4F4;
  --color-primary-text: #FFFFFF;

  --color-accent: #D97706; --color-accent-hover: #B45309;
  --color-accent-light: #FEF3C7; --color-accent-text: #3A1D00;   /* CHANGED */

  --color-sale: #B91C1C; --color-sale-light: #FEE2E2; --color-sale-text: #FFFFFF; /* CHANGED */

  --color-bg: #F0F7F7; --color-surface: #FFFFFF; --color-surface-alt: #F7FBFB;
  --color-border: #D1E8E8; --color-border-strong: #A8D4D4;
  --color-text: #0F2E2E; --color-text-muted: #4A7E7E; --color-text-disabled: #93BBBB;
  --color-nav-bg: #0E7373; --color-footer-bg: #0B3B3B;
  --color-footer-text: rgba(255,255,255,.75);
  --color-footer-heading: rgba(255,255,255,.70);   /* CHANGED */
  --color-footer-accent: #F5B94A;                  /* NEW */

  /* ...feedback, shadows, radii, spacing, transitions as before... */
  --bs-primary-rgb: 14, 115, 115;                  /* light only */
}

[data-theme="dark"] {
  --color-primary: #13B8B8; --color-primary-hover: #0E9A9A;
  --color-primary-light: #162B2B; --color-primary-text: #0F1E1E;
  --color-accent: #F59E0B; --color-accent-text: #0F1E1E;
  --color-sale: #EF4444; --color-sale-text: #0F1E1E;   /* CHANGED */
  --color-bg: #0F1E1E; --color-surface: #162B2B; --color-surface-alt: #1A3030;
  --color-text: #E8F4F4; --color-text-muted: #7AADAD;
  --color-nav-bg: #0A1717; --color-footer-bg: #050E0E;
  --color-footer-heading: rgba(255,255,255,.70);
  /* ... */
  --bs-primary-rgb: 19, 184, 184;                  /* NEW — matches dark primary */
}
```

### 17.3 Bootstrap bridge (corrected) **[CHANGED]**
`overrides.css` maps Bootstrap variables, but **do not rely on `--bs-primary` to restyle `.btn-primary`** — Bootstrap compiles button colors from Sass, not that variable. Therefore:
- Use the **custom `.btn-primary` from `components.css`** for brand buttons, and **neutralise Bootstrap's**. To avoid class collision, define a namespaced variant `.btn-brand` and use it in templates, **or** ensure `components.css` loads after Bootstrap (it does) and explicitly reset Bootstrap's button custom properties:
```css
.btn-primary {
  --bs-btn-bg: var(--color-primary);
  --bs-btn-border-color: var(--color-primary);
  --bs-btn-hover-bg: var(--color-primary-hover);
  --bs-btn-hover-border-color: var(--color-primary-hover);
  --bs-btn-color: var(--color-primary-text);
  background: var(--color-primary); color: var(--color-primary-text);
  border: none; border-radius: var(--radius-md);
}
```
- `--bs-primary-rgb` is defined **per theme** (above) so dark-mode focus rings stay correct.
- Keep the rest of the `--bs-*` mappings (`--bs-body-bg`, `--bs-body-color`, `--bs-border-color`, `--bs-card-bg`, `--bs-link-color`, `--bs-secondary-color`).

### 17.4 Theme toggle **[CHANGED]**
Add initial icon state so both emoji don't flash:
```css
[data-theme="light"] .icon-sun { display: none; }
[data-theme="dark"]  .icon-moon { display: none; }
```

### 17.5 Design rules (kept from v1)
No Bootstrap default blue; no raw greys; no inline `style="color/background"`; flash-sale bar is amber; `% OFF` badges are `--color-sale`; add-to-cart is teal; dark mode works pre-JS; the 3px left border on `.section-title` is the only decoration; fonts are Hind Siliguri + Inter.

---

## 18. Development Setup (uv) **[CHANGED — v2.1]**

```bash
uv sync                          # install Python 3.12 + all deps from uv.lock
cp .env.example .env             # edit DATABASE_URL / REDIS_URL / OAuth keys
uv run python manage.py migrate
uv run python manage.py seed_demo_data     # DEBUG only
uv run python manage.py runserver          # served by daphne (Channels 4)
uv run celery -A config worker -l info
uv run celery -A config beat   -l info     # DB scheduler via django-celery-beat
uv run pytest                              # tests
```

Local dev defaults to SQLite + LocMem cache + in-memory channel layer and runs
Celery tasks eagerly, so **no Redis is required to start**. Set `USE_REDIS=True`
(and run `redis-server` / `docker compose up -d redis`) to exercise caching,
Channels and the worker/beat. See `README.md` for the full workflow.

---

## 19. Deliverables & Build Order **[CHANGED]**

Phase it — do not big-bang.

**Phase 0 — Foundation**
Project skeleton, settings split, custom user + manager + allauth (new settings), design tokens + base template + navbar/footer, common utilities (`money`, `sanitize`, mixins, method middleware).

**Phase 1 — Catalogue**
Models (+`sku`, `stock_quantity`, `track_inventory`, choices) → admin → list/detail → HTMX filters → imagekit thumbnails → CSV import.

**Phase 2 — Cart & Coupons**
Session cart + merge, HTMX cart (with CSRF + multi-target), coupon model + `CouponRedemption`, rate-limited validation.

**Phase 3 — Checkout & Orders**
Fee math utility, pickup store selection, payment instructions, manual verification + audit fields, `public_token` guest tracking, next-purchase coupon on PAID.

**Phase 4 — Promotions & Homepage**
Flash/Hot sales, `Banner` HERO carousel, all homepage sections (grid links to `/products/`).

**Phase 5 — Analytics, Tasks & Pages**
Channels consumer (multi-tab correct) + daphne/asgi, Celery tasks + beat, SiteSettings/pages/stores/contact, visitor widgets.

**Phase 6 — Hardening & Docs**
Security settings, tests, `README.md`, `Dockerfile`, `docker-compose.yml`, `.gitignore`.

---

## 20. Open Items / Assumptions
- Confirm with the owner that a **mandatory service fee** is acceptable under local consumer norms, and that it's shown from the product page onward.
- Confirm **retention period** for `SiteVisit` (default 12 months) for the Privacy Policy.
- Confirm **Facebook app review** timeline (email permission) before relying on FB login at launch.
- Confirm BDT is always **2 dp** (some BD invoices display 0 dp) — spec assumes 2 dp everywhere.





