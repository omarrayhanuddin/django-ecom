"""Controlled vocabularies used by catalogue models and filters.

Keeping capacity / product_type as choices (not free text) makes the filter
sidebar reliable.
"""

CAPACITY_CHOICES = [
    ("100ml", "100ml"),
    ("250ml", "250ml"),
    ("500ml", "500ml"),
    ("1L", "1 Litre"),
    ("2L", "2 Litre"),
    ("100g", "100g"),
    ("250g", "250g"),
    ("500g", "500g"),
    ("1kg", "1 Kg"),
    ("2kg", "2 Kg"),
    ("5kg", "5 Kg"),
    ("piece", "প্রতি পিস"),
]

PRODUCT_TYPE_CHOICES = [
    ("electronics", "Electronics"),
    ("grocery", "Grocery"),
    ("clothing", "Clothing"),
    ("home", "Home Goods"),
    ("beauty", "Beauty"),
    ("other", "Other"),
]

AVAILABILITY_IN_STOCK = "IN_STOCK"
AVAILABILITY_PRE_ORDER = "PRE_ORDER"
AVAILABILITY_UPCOMING = "UPCOMING"

AVAILABILITY_CHOICES = [
    (AVAILABILITY_IN_STOCK, "স্টকে আছে"),
    (AVAILABILITY_PRE_ORDER, "প্রি-অর্ডার"),
    (AVAILABILITY_UPCOMING, "আসছে"),
]
