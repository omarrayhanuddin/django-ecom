"""HTML sanitisation for all rich-text fields, using nh3 (ammonia).

Applied on save so the database never stores unsafe markup.
"""
import nh3

SAFE_TAGS = {
    "p", "br", "span", "strong", "b", "em", "i", "u", "s",
    "ul", "ol", "li", "blockquote",
    "a", "h2", "h3", "h4", "h5",
    "table", "thead", "tbody", "tr", "th", "td",
    "img", "hr", "div",
}

SAFE_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "*": {"class"},
}


def clean_html(raw: str) -> str:
    """Return an XSS-safe HTML fragment. Empty input -> empty string."""
    if not raw:
        return ""
    return nh3.clean(
        raw,
        tags=SAFE_TAGS,
        attributes=SAFE_ATTRIBUTES,
        link_rel="noopener noreferrer",
        url_schemes={"http", "https", "mailto", "tel"},
    )
