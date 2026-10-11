# Spec Review — `ecommerce-agent-prompt.md`

**Reviewed:** 2026-10-10
**Verdict:** Ambitious and mostly coherent, but **not buildable as written**. There are ~6 blocking contradictions, several outright-wrong config snippets (verified against current releases), a stack of undeclared dependencies, and money-handling rules that are ambiguous enough to produce incorrect invoices. Fix the blocking items before any code is written, otherwise the agent will guess and you'll pay for rework.

Severity: 🔴 blocking · 🟠 high · 🟡 medium

---

## 1. Blocking contradictions (resolve before coding)

### 1.1 🟠→🔴 `apps/dealership/DealershipSlide` duplicates `apps/promotions/Banner`
`Banner.position` includes `DEALERSHIP`, and a whole separate app `dealership` models the *same* homepage carousel. Two models, two admin registrations, one UI element. **Pick one.** Recommendation: delete `apps/dealership` and use `Banner` with `position` (or delete `Banner` and keep `DealershipSlide`). The name "Dealership" is also misleading for a retail store — it reads like a car dealership; consider `showcase`/`hero`.

### 1.2 🔴 Platform fee has two sources of truth
`SiteSettings.platform_fee_percentage` (Settings section, business rule #2) **and** `PLATFORM_FEE_PERCENTAGE` in `.env` (env example) both define it. Which wins? Decide: I recommend **DB `SiteSettings` is authoritative**, `.env` value used only to seed the singleton on first boot. Document it.

### 1.3 🔴 Platform fee math is undefined
"`fee = subtotal * (platform_fee_percentage / 100)`" — but is `subtotal` **before or after** coupon discount? Is the fee added on top of the discounted total or the gross? This changes every invoice. Needs an explicit formula, e.g.:
```
net_subtotal = subtotal
discount     = coupon discount
taxable      = net_subtotal - discount
platform_fee = round(taxable * pct / 100, 2)
total        = taxable + platform_fee
```
Also: **rounding rules and currency precision** for BDT are unspecified (2 dp? banker's rounding? `ROUND_HALF_UP`?). Money bugs come from exactly this. Add a `round_money()` helper and use it everywhere.

### 1.4 🔴 Order-detail enumeration / guest order lookups
- `order_number = ORD-YYYYMMDD-XXXX` is **sequential and guessable**.
- `/orders/<order_number>/` is auth-required, yet **guest checkout is allowed** — so guests cannot view/track their own order at all, and the confirmation page is a dead-end after the session ends.
- The spec does mention an "order ownership check", but for guests there is no owner.

Need: a non-guessable `public_token` (uuid) on `Order` for guest lookups, plus email-a-link flow. Never expose guests' orders by sequential number.

### 1.5 🔴 Next-purchase coupon is issued too early
Business rule #4 says a coupon is issued "after every completed/confirmed order". But payment is **manual and unverified** — status just placed is `PENDING`/`AWAITING_VERIFICATION`. As written, a user can place orders, accept the free coupon, and never pay. Tie coupon issuance to **payment verified / order completed** (admin action), not to order placement.

### 1.6 🔴 Bilingual strategy is undecided
Rule #8 says "simple `name_bn`/`name_en` dual-field pattern **or** `django-parler`". These are completely different data models (and `django-parler` isn't in requirements). Choose one now — it touches every model, admin, form, and template. For 2 languages and a non-technical owner, **dual fields (`name_bn`, `name_en` + a `display_name` property)** is simpler and cheaper than parler. Also decide the fallback when a field is blank.

### 1.7 🟠 Which price wins? (price-resolution order undefined)
A product can have `base_price`, `discount_price`, a `FlashSaleProduct.discount_percentage`/`sale_price`, a `HotSale.discount_percentage`, and variant `price_override`. The spec never defines stacking precedence. Need one documented resolver, e.g.:
`variant override → active flash sale → hot sale → discount_price → base_price`, and whether discounts can stack (default: no).

---

## 2. Wrong / outdated technical configuration (verified)

### 2.1 🔴 `django-allauth` settings are deprecated
`ACCOUNT_EMAIL_REQUIRED`, `ACCOUNT_USERNAME_REQUIRED`, and `ACCOUNT_AUTHENTICATION_METHOD` were **deprecated in allauth 65.5 (Mar 2025)** and now emit warnings; `AUTHENTICATION_METHOD` was removed in favor of `LOGIN_METHODS`. For allauth on Django 5.x use:
```python
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]  # no username
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
```
Pin `django-allauth>=65.5` and drop the three legacy settings.

### 2.2 🔴 Channels 4 needs `daphne` — it's missing
The spec sets `ASGI_APPLICATION` and runs `python manage.py runserver`, but **Channels 4 removed the Channels `runserver`**. You must install `daphne` (or `channels[daphne]`) and put **`"daphne"` at the top of `INSTALLED_APPS`, before `django.contrib.staticfiles`**. `daphne` is absent from `requirements/base.txt` and from the shown `INSTALLED_APPS`. Also missing: `config/routing.py`, `apps/*/routing.py`, the `consumers.py` location, and the full `ProtocolTypeRouter` sketch that explicitly registers `"http": get_asgi_application()` (Channels 4 no longer auto-routes HTTP).

### 2.3 🔴 `bleach` is deprecated and EOL
Bleach was deprecated in Jan 2023 and its **final release (6.4.0, Jun 2026) received no further security fixes**. Use **`nh3`** (Rust/ammonia) for `RichTextField` sanitization, e.g. `nh3.clean(html, tags=..., attributes=..., url_schemes={"http","https"})`. Note: `nh3` cannot filter individual CSS properties, so disallow `style` outright.

### 2.4 🟠 `sorl-thumbnail` needs an explicitly configured KV store
sorl-thumbnail requires a key/value store. Its own Redis backend is deprecated in favor of the Django cache. On Django 4+/5, configure a cache and point `THUMBNAIL_CACHE` at it (or accept the default cached-db store with memcached). None of these settings appear in the spec's settings block. (Also consider `django-imagekit` instead, as the spec offers it as an alternative — it avoids this.)

### 2.5 🟠 Bootstrap variable override won't do what the spec claims
`overrides.css` sets `--bs-primary`, `--bs-primary-rgb`, etc., and says "Bootstrap components inherit the palette automatically". **False for the important cases.** Bootstrap's `.btn-primary` is compiled from Sass into `--bs-btn-bg`, not `--bs-primary`, so overriding `--bs-primary` does **not** turn Bootstrap buttons teal — they'd stay default blue (`#0d6efd`), violating the spec's own rule #1.
Additionally:
- `--bs-primary-rgb: 14, 115, 115;` is **hardcoded and only set in `:root`** → in dark mode (primary becomes `#13B8B8`) any rgb-derived Bootstrap styles (focus rings, etc.) stay wrong. Add the dark-mode override too.
- The custom `.btn-primary` in `components.css` collides by **class name** with Bootstrap's `.btn-primary`. Load order saves you here (components after Bootstrap), but it's fragile. Prefer a namespaced class (`.btn-brand`) or explicitly neutralize Bootstrap's button classes.

### 2.6 🟡 `psycopg2-binary` in the shipped requirements
Fine for local dev, discouraged for production (bundled libpq can mask issues). Split: `psycopg2-binary` in `local.txt`, `psycopg[c]`/`psycopg2` in `production.txt`.

---

## 3. Missing dependencies (referenced in the spec, absent from requirements)

| Referenced where | Missing package |
|---|---|
| `RichTextField` (Product, StaticPage) | `django-ckeditor` / `django-tinymce` — **not declared** |
| CSV bulk product import | `django-import-export` (or a hand-written action) |
| Rate-limit coupon endpoint | `django-ratelimit` |
| HTML sanitization | `nh3` (replace `bleach`) |
| Channels runserver | `daphne` |
| `Config`/`csv` seed | stdlib — fine |
| Optional: Bilingual | `django-parler` (if that route is chosen) |
| Optional: brute-force/login hardening | `django-axes` |

Also `django-htmx` is listed but never used in any described pattern — either use it (for `HX-Request` detection / `hx-*` helpers) or drop it.

---

## 4. Data-model gaps

**accounts**
- 🟠 `CustomUser` lists `is_active, is_staff` but not `is_superuser`; and with `AbstractBaseUser` you must also mix in `PermissionsMixin` or Django admin/groups break. Needs a `CustomUserManager` with `create_user`/`create_superuser` (not mentioned).
- 🟡 Onboarding gated on "`phone_number` is blank" is a proxy. Add an explicit `onboarding_complete` boolean — otherwise a user who legitimately has no phone but dismisses the modal gets nagged forever.
- 🟡 No `created_at/updated_at`; no phone normalization/validation for BD `01XXXXXXXXX`.

**catalogue**
- 🔴 Admin says "search by name/**SKU**" but `Product` has **no SKU** (only `ProductVariant.sku`). Contradiction.
- 🟠 **No product-level stock.** Only `ProductVariant.stock_quantity` exists; most products won't have variants. `availability` is a status enum, not inventory. "In Stock" filtering and "quantity range" filter have nothing to filter on. Add `stock_quantity`/`track_inventory` at product level (or make a default variant mandatory).
- 🟠 `capacity` is a free-text `CharField` but the filter sidebar filters **by capacity**. Free text → "500ml", "500 ml", "0.5L" all differ. Needs a controlled choices set or a `Capacity` FK.
- 🟠 `product_type` "CharField **or** FK" — undecided; affects filtering.
- 🟡 `ProductReview`: no unique constraint `(user, product)` and no per-review moderation default. Add `UniqueConstraint` + default `is_approved=False`.
- 🟡 No stock decrement / oversell protection on add-to-cart or checkout.
- 🟡 `slug` strategy (auto-generate? uniqueness? language-specific?) unspecified.

**promotions**
- 🟠 `FlashSaleProduct.sale_price` "computed **or** stored" — decide. If computed, it drifts when `base_price` changes; if stored, it's a snapshot. Matters for legality of the advertised price.
- 🔴 Coupon abuse holes: `used_count` + `max_uses` with no `CouponRedemption` (per-user usage) model and no atomic `select_for_update` → a single-use coupon can be used many times / in a race. Add `CouponRedemption(user, coupon, order)` with a unique constraint, and enforce per-user vs global limits distinctly.
- 🟡 No max-discount cap on `PERCENTAGE` coupons.
- 🟡 `is_next_purchase` semantics unclear (a flag on the coupon; is it "auto-issued"?).

**cart**
- 🟠 No `unique_together (cart, product, variant)` → duplicate lines.
- 🟠 `unit_price` snapshot at add-time but coupons/flash sales move between add and checkout; need **re-validation at checkout** and a rule for which price is charged.
- 🟡 Cart-merge on login with two existing carts: quantity collision policy undefined.

**orders**
- 🟠 `Order` lacks audit fields for manual payment: `paid_at`, `verified_by`, `verified_at`, `payment_reference` **uniqueness** (TrxID reuse = fraud).
- 🟠 No enforced status-transition rules; any status can jump to any other.
- 🟡 **No pickup store selection** even though the whole premise is "collect from showroom". Which branch? Add `pickup_store` FK to `StoreLocation` (or at least capture at checkout).
- 🟡 `order_number` generation has a concurrency collision risk (add a DB unique + retry/sequence).

**analytics**
- 🟠 Live-visitor remove-on-disconnect is wrong for multi-tab users (each socket decrement). Need a per-session ref count or a `session_id` set rather than counting channels.
- 🟡 IP + user-agent logged for "unique session" — privacy policy must disclose; retention period unspecified.
- 🟡 The "periodic cleanup of stale entries" has no home (which Celery task? beat schedule?).

**pages**
- 🟡 `SiteSettings` singleton via `django-solo` **or** custom save logic — pick one (also interacts with `django-unfold`).

---

## 5. Business-logic & security gaps

- 🔴 **HTMX + CSRF is not handled.** `hx-post`/`hx-delete`/`hx-patch` need `X-CSRFToken` (e.g. a `hx-headers` attribute on `<body>` or `htmx.config`). The spec shows none, so every cart/coupon POST will 403.
- 🔴 **Django doesn't parse form data for PUT/PATCH/DELETE.** The spec's `hx-patch="/cart/item/{id}/"` and `hx-delete` won't populate `request.POST`. You need a middleware to shim `request.POST`/`request.FILES`, or use POST + `X-HTTP-Method-Override`.
- 🟠 **Multi-target cart updates.** `hx-post="/cart/add/" hx-target="#cart-count"` updates *only* the badge — the drawer, summary, and line items go stale. Use `HX-Trigger` events or out-of-band swaps.
- 🟠 **Guest→account cart/order merge by email is unsafe.** Matching/merging on a self-declared email lets one user absorb another's guest order history. Require email verification before merge.
- 🟠 **Platform fee legality/UX.** A mandatory fee on top of the advertised price may draw consumer-protection complaints (and the spec's own "WCAG-accessible, trustworthy" positioning argues against surprise fees). Show it in every price breakdown from the product page onward, and confirm with the owner.
- 🟠 Search suggest returns **JSON** but the HTMX pattern expects an **HTML partial**. Contradiction — either return HTML or do JSON with a JS handler (which the spec forbids elsewhere).
- 🟡 `/search/` and `/search/suggest/` have **no owning app** in the structure. Homepage "ALL PRODUCTS" paginated + HTMX `hx-push-url` + filters + infinite sections needs a concrete pagination-vs-filter design.
- 🟡 No image-upload validation (content type/size), no `SECURE_*`/HSTS/cookie-flag list (only SSL redirect), no open-redirect check on `next`, no admin brute-force protection.
- 🟡 `seed_demo_data` creates `admin@example.com / admin123` — **must be guarded to `DEBUG` only**, never runnable in production.
- 🟡 No tests / no test runner (`pytest-django`) and no `.gitignore`, `Dockerfile`, or `.dockerignore`.

---

## 6. Design-system problems

### 6.1 🔴 Accent color fails the spec's own WCAG AA claim
The spec calls the palette "WCAG AA accessible". It isn't for the accent:
- **White on `--color-accent #D97706` = ~3.2:1** → fails AA for normal text (needs 4.5:1). Used in `.badge-hot`, `.flash-sale-bar`, `.footer-support-phone` at small sizes.
- **Dark mode `--color-sale #EF4444` with white text = ~3.8:1** → also fails AA normal for the small `% OFF` badge.
- **`--color-footer-heading: rgba(255,255,255,0.40)` on `#0B3B3B` = ~3.3:1** → fails for the ~11px uppercase headings.

Fixes: darken accent text or use dark ink on amber (`--color-accent-text: #3B1D00`-ish), or bump sale/dark values; raise footer-heading opacity to ~0.65+. Decide and re-check contrast for both themes.

### 6.2 🟠 `--bs-primary-rgb` hardcoding vs rule #4
Rule #4 says "never hardcode `#0E7373`", yet `overrides.css` hardcodes `--bs-primary-rgb: 14, 115, 115`. And it's only defined for light mode (see 2.5). Either generate the rgb from the token or define it per theme.

### 6.3 🟡 Theme toggle has no initial icon state
`updateToggleIcon` flips `.icon-sun`/`.icon-moon` **after** DOM load; there's no CSS default, so both emoji render on first paint. Add `.icon-sun/.icon-moon` defaults keyed off `[data-theme]`.

### 6.4 🟡 `lang` handling
`<html lang="bn">` but content is bilingual; set `lang` on Bangla vs English fragments for correct hyphenation/screen-reader pronunciation.

### 6.5 🟡 On-page complexity
The homepage stacks ~9 wide sections **plus** a full paginated/filtered catalogue. That's a heavy first load and a lot of HTMX state on one route. Consider splitting "all products" to `/products/` (which already exists) and keeping only a truncated grid on the homepage.

---

## 7. Settings that are missing entirely
The "Key Django Settings" section omits settings the agent will otherwise guess:
`TIME_ZONE="Asia/Dhaka"`, `LANGUAGE_CODE`, `USE_TZ`, `USE_I18N`, `DEFAULT_AUTO_FIELD`, `EMAIL_BACKEND` (console in dev), `CSRF_TRUSTED_ORIGINS`, Django 5 `STORAGES` with WhiteNoise, `THUMBNAIL_*`, `CELERY_*` + `config/celery.py` + `config/__init__.py` import, the Celery beat schedule (flash-sale expiry, stale-visitor cleanup), and the Redis env var (settings hardcode `redis://127.0.0.1:6379` while `.env` defines `REDIS_URL` — pick one).

---

## 8. Recommended decisions (answer these before building)

1. Bilingual: dual fields vs parler? (recommend dual fields)
2. Dealership/Banner: which single model survives? (recommend delete `dealership`)
3. Platform fee source of truth + exact formula + rounding? (recommend SiteSettings authoritative, fee on `subtotal − discount`)
4. Next-purchase coupon issued on: payment-verified/completed (recommend) vs order-placed?
5. Admin theme: `django-unfold` **or** `jazzmin` (pick one — recommendation: unfold)
6. Rich text: ckeditor vs tinymce? Sanitizer: `nh3`.
7. Thumbnails: sorl-thumbnail vs imagekit? (imagekit avoids KV-store setup)
8. Product stock: product-level field added? Price precedence order?
9. Guest order tracking: public token + email link?
10. Accent/dark-sale/sale color values that actually pass AA?

---

## 9. Phase-it, don't big-bang it

The deliverables list is a single 12-item monolith. Suggested order so something is demoable early:
1. **Foundation:** project skeleton, settings split, custom user + allauth (new settings), theme/design tokens, base template, navbar/footer.
2. **Catalogue:** models → admin → list/detail → HTMX filters. (Needs stock + price-precedence decisions.)
3. **Cart + coupons:** session merge, HTMX cart, coupon model with redemptions.
4. **Checkout + orders:** fee math, pickup store, payment instructions, manual verification, next-purchase coupon on completion.
5. **Promotions + homepage sections + dealership/banner.**
6. **Analytics (Channels + Redis) + Celery tasks + pages.**
7. **Seed data, README, tests, deploy config.**

---

## 10. Corrected allauth + Channels snippets (drop-in)

```python
# allauth (Django 5 / allauth >= 65.5)
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {"SCOPE": ["profile", "email"], "AUTH_PARAMS": {"access_type": "online"}},
    "facebook": {"METHOD": "oauth2", "SCOPE": ["email", "public_profile"]},
}

# Channels 4 — daphne FIRST
INSTALLED_APPS = [
    "daphne",                 # must precede django.contrib.staticfiles
    "django.contrib.admin",
    # ...
    "channels",
]
ASGI_APPLICATION = "config.asgi.application"
```

```python
# config/asgi.py (Channels 4 — HTTP must be registered explicitly)
import os
from django.core.asgi import get_asgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.analytics.routing  # ws/visitors/

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(URLRouter(apps.analytics.routing.websocket_urlpatterns)),
})
```

Sanitizer:
```python
import nh3
SAFE_TAGS = {"p","br","strong","em","ul","ol","li","a","h3","h4","blockquote","img"}
html = nh3.clean(raw_html, tags=SAFE_TAGS, link_rel=None, url_schemes={"http","https"})
```

---

## 11. Smaller notes
- `config/` is described as a "settings **package**" but `wsgi.py`/`asgi.py` sit beside the package in the tree — minor structural fuzziness.
- Missing files the agent will need: `config/celery.py`, `config/routing.py`, `apps/analytics/{routing,consumers,middleware}.py`, `apps/*/tasks.py`, `.gitignore`, `Dockerfile`, `pytest.ini`.
- The tree in §"Project Structure" omits `templates/home/`, `templates/accounts/`, etc. (referenced later).
- "Announcement bar (optional)" — say yes/no; it affects the base template.
- Facebook OAuth's `email` permission often requires app review; call this out as a launch dependency for BD users.
- `django-unfold` + `django-admin-sortable2` + `django-solo` compatibility should be verified together before committing.
```
