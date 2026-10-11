"""Shared validators."""
import re

from django.core.exceptions import ValidationError

BD_PHONE_RE = re.compile(r"^01[3-9]\d{8}$")


def validate_bd_phone(value: str) -> None:
    """Validate a Bangladeshi mobile number: 01[3-9]XXXXXXXX (11 digits)."""
    if not value:
        return
    if not BD_PHONE_RE.match(value):
        raise ValidationError(
            "সঠিক মোবাইল নম্বর দিন (যেমন 01712345678)।",
            code="invalid_bd_phone",
        )
