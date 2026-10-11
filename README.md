# ShopBazar — Bilingual Bangladeshi E-Commerce

A full-featured e-commerce storefront for a Bangladeshi retail business. Physical
products only, **no delivery** (customers collect from a showroom), **manual
payment** verification (bank transfer / bKash / Nagad / Rocket), and a
**bilingual** (Bangla + English) UI.

Built with **Django 5.2**, HTMX, Alpine.js, Bootstrap 5, Django Channels,
Celery and Redis. Dependencies are managed with **[uv](https://docs.astral.sh/uv/)**.

> The original build specification lives in [`ecommerce-agent-prompt-v2.md`](ecommerce-agent-prompt-v2.md)
> and the design/consistency review in [`spec-review.md`](spec-review.md).

---

## Tech stack

| Area | Choice |
|---|---|
| Backend | Django 5.2 (Python 3.12) |
| Frontend | Django Templates, HTMX, Alpine.js, Bootstrap 5 |
| Auth | django-allauth (email/password + Google/Facebook OAuth2) |
| Realtime | Django Channels 4 + Daphne (live visitor count) |
| Async | Celery + django-celery-beat |
| Cache/session store | Redis (django-redis) |
| DB | SQLite locally, PostgreSQL in production |
| Images | Pillow + django-imagekit |
| Admin | django-unfold (+ django-admin-sortable2, django-solo) |
| Rich text | django-ckeditor, sanitised with **nh3** |
| Static | WhiteNoise |

---

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** (manages Python + dependencies + lockfile)
- Optional: Docker (for Redis + PostgreSQL) or a local Redis server

## Setup

```bash
# 1. Install Python + create the environment and install dependencies
uv sync

# 2. Configure the environment
cp .env.example .env        # Windows: copy .env.example .env

# 3. Create the database schema
uv run python manage.py migrate

# 4. Load demo data (5 categories, 20 products, flash sale, coupon, banners)
uv run python manage.py seed_demo_data

# 5. Run the dev server (served by Daphne for ASGI/WebSocket support)
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/ — admin at `/admin/`
(`admin@example.com` / `admin123`, created by the seed command).

By default local dev uses **SQLite + LocMem cache + in-memory channel layer** and
runs Celery tasks inline, so **no external services are required** to try it.

### Enabling Redis (real caching, channels and Celery)

```bash
docker compose up -d redis          # or: redis-server
# then in .env:
#   USE_REDIS=True
#   REDIS_URL=redis://localhost:6379/0
```

Start the worker and beat scheduler (separate terminals):

```bash
uv run celery -A config worker -l info
uv run celery -A config beat   -l info
```

### PostgreSQL

```bash
docker compose up -d db
# .env: DATABASE_URL=postgres://postgres:postgres@localhost:5432/shopbazar
uv run python manage.py migrate
```

## Tests

```bash
uv run pytest
```

## Useful commands

```bash
uv run python manage.py check
uv run python manage.py makemigrations
uv run python manage.py seed_demo_data        # demo catalogue (DEBUG only)
uv run python manage.py fetch_demo_images     # pull real product/banner photos
uv run python manage.py fetch_demo_images --force   # re-download all images
uv run python scripts/smoke.py       # requests every page, prints status codes
uv run python scripts/flow_test.py   # end-to-end cart -> checkout -> payment -> coupon
```

### Demo images

Each demo product has a **pinned, hand-picked Wikimedia Commons photo** (URLs
resolved in `apps/pages/demo_images.py`), so images always match the product
titles. If a pinned URL fails, the command falls back to a relevance-scored
Commons/Openverse search and finally to a generated placeholder when offline.

- `uv run python manage.py fetch_demo_images` — fill in missing images
- `uv run python manage.py fetch_demo_images --force --debug` — re-download and
  log the chosen source
- `uv run python scripts/contact_sheet.py` — build `media/_contact_sheet.jpg`
  to eyeball all product photos at once

All images are normalised to 800×800 JPEG with Pillow, so an internet connection
is only needed while fetching.

---

## What's implemented

**Accounts** — custom email-first user (`AbstractBaseUser` + `PermissionsMixin`),
profiles, multiple addresses, single-step registration, social onboarding
modal, Google/Facebook OAuth (shown only when a `SocialApp` is configured).

**Catalogue** — categories (self-referential), brands, tags, products with
dual-language names, SKU, **product-level stock** (`stock_quantity` +
`track_inventory`), variants, image gallery, reviews (moderated), full HTMX
filter sidebar (category, price, availability, capacity, type, brand, stock),
sorting, and CSV import/export in the admin.

**Promotions** — flash sales with countdown, hot deals, coupons
(percentage/fixed, caps, min order, per-user limits, atomic redemptions),
auto-issued next-purchase coupons, and a single `Banner` model for the homepage
carousel. A Celery beat task deactivates expired flash sales every 5 minutes.

**Cart** — session cart for guests, merged into the DB cart on login
(max-quantity collision policy), HTMX add / update / remove, slide-in drawer,
coupon application (rate-limit ready).

**Orders** — guest + authenticated checkout, **no delivery address** (pickup
notice + store selection), manual payment with reference number, an admin action
to mark paid (which emails the customer and issues the next-purchase coupon),
order history, ownership checks, and public token-based tracking for guests.

**Analytics** — one `SiteVisit` row per session, a total visitor counter, and a
live visitor count over WebSocket (CORS-free, multi-tab correct via a Redis ref
count) with an HTMX polling fallback.

**Pages** — About / Privacy / Terms / Brands / Stores / Contact, a
`SiteSettings` singleton (platform fee, contact, social), and store locations.

### Money rules (single source of truth)

- All amounts round **HALF_UP to 2 dp** (`apps/common/money.py`).
- Price resolution: variant override → flash sale → hot sale → `discount_price`
  → `base_price`. **Discounts never stack.**
- Platform fee = `round((subtotal − discount) × pct / 100)`, where `pct` is
  `SiteSettings.platform_fee_percentage` (a snapshot is stored on each order).
- `total = (subtotal − discount) + platform_fee`.

---

## Design system

Colours live exclusively in `static/css/theme.css` (CSS custom properties), with
`components.css` and `overrides.css` building on them. Light + dark themes are
supported with no JavaScript required for first paint, and the palette is
contrast-checked for WCAG AA. Fonts are **Hind Siliguri** + **Inter**.

---

## Project layout

```
config/               settings/{base,local,production}, asgi, wsgi, celery, urls
apps/
  common/             money, sanitize (nh3), mixins, middleware, templatetags
  accounts/           CustomUser, profile, addresses, onboarding, OAuth adapter
  catalogue/          categories, brands, products, images, variants, reviews, filters
  promotions/         flash/hot sales, coupons, redemptions, banners, services
  cart/               session + DB cart, merge-on-login, HTMX endpoints
  orders/             checkout, orders, order items, payment instructions, tasks
  analytics/          SiteVisit, live-visitor consumer/routing, middleware, tasks
  pages/              SiteSettings, static pages, stores, homepage, seed command
templates/            base + per-app templates + partials
static/               css/{theme,components,overrides}, js/{theme,app}
tests/                pytest suite
scripts/              smoke.py, flow_test.py
pyproject.toml        dependencies (uv)
uv.lock               exact resolved versions
Dockerfile, docker-compose.yml
```

---

## Notes & caveats

- **CKEditor 4 is end-of-life.** Every rich-text field is sanitised with **nh3**
  on save and the toolbar is restricted, and the package's own warning is
  silenced in settings. Consider `django-ckeditor-5` or a newer editor before
  production.
- **Social login** buttons (Google / Facebook / Apple) are shown as placeholders on
  the login and register pages. They become real as soon as you add a `SocialApp`
  in the admin (Apple needs the allauth Apple provider added first). Facebook's
  `email` permission typically needs app review before launch.
- **Guest next-purchase coupons** are keyed on the order number and limited to a
  single use; if that guessability matters, switch to a longer random code.
- **Privacy:** IP address and user-agent are stored per session (`SiteVisit`);
  a daily task purges rows older than one year — update the Privacy Policy to
  match.
- The seed superuser (`admin123`) is only created when `DEBUG=True`
  (`seed_demo_data` refuses to run otherwise).
