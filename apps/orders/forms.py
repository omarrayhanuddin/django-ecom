from django import forms

from apps.catalogue.models import Product
from apps.common.validators import validate_bd_phone
from apps.pages.models import StoreLocation

from .models import Order


class CheckoutForm(forms.Form):
    """Guest + authenticated checkout. No delivery address (pickup only)."""

    customer_name = forms.CharField(max_length=255, label="নাম")
    email = forms.EmailField(label="ইমেইল")
    phone = forms.CharField(max_length=11, label="মোবাইল নম্বর", validators=[validate_bd_phone])
    pickup_store = forms.ModelChoiceField(
        queryset=StoreLocation.objects.all(), label="সংগ্রহের শোরুম", empty_label=None
    )
    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices, label="পেমেন্ট মাধ্যম"
    )
    payment_reference = forms.CharField(
        max_length=120,
        required=False,
        label="পেমেন্ট রেফারেন্স",
        help_text="বিকাশ/নগদ TrxID অথবা ব্যাংক রেফারেন্স নম্বর",
    )
    note = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}), label="মন্তব্য"
    )
    agree = forms.BooleanField(
        label="শর্তাবলী ও শোরুম থেকে সংগ্রহ নীতিতে সম্মত আছি", required=True
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["customer_name"].initial = user.full_name
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone_number
