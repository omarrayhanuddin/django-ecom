from django import template

register = template.Library()


@register.filter
def bdt(value):
    """Format a number as Bangladeshi Taka, e.g. ৳1,250.00"""
    try:
        return f"৳{float(value):,.2f}"
    except (TypeError, ValueError):
        return "৳0.00"


@register.filter
def stars(rating):
    """Return a 5-char star string, e.g. ★★★☆☆."""
    try:
        rating = int(round(float(rating)))
    except (TypeError, ValueError):
        rating = 0
    rating = max(0, min(5, rating))
    return "★" * rating + "☆" * (5 - rating)


@register.filter
def in_stock_label(product):
    return "স্টকে আছে" if getattr(product, "in_stock", False) else "স্টক নেই"


@register.filter
def add_class(field, css):
    """Add a CSS class to a bound form field widget."""
    try:
        existing = field.field.widget.attrs.get("class", "")
        field.field.widget.attrs["class"] = f"{existing} {css}".strip()
        return field
    except AttributeError:
        return field


@register.filter
def widget_class(field):
    """Return the right Bootstrap class for a bound field's widget."""
    try:
        name = field.field.widget.__class__.__name__
    except AttributeError:
        return "form-control"
    if name in ("CheckboxInput",):
        return "form-check-input"
    if name in ("Select", "SelectMultiple", "SelectDateWidget"):
        return "form-select"
    return "form-control"
