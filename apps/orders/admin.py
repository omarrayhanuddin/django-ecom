from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Order, OrderItem, PaymentInstruction, PaymentReference


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "variant", "product_name", "unit_price", "quantity", "line_total")
    can_delete = False


class PaymentReferenceInline(TabularInline):
    model = PaymentReference
    extra = 0
    readonly_fields = ("method", "reference", "submitted_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        "order_number", "customer", "status_badge", "payment_badge",
        "payment_method", "total_display", "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("order_number", "guest_email", "guest_phone", "user__email", "payment_reference")
    readonly_fields = (
        "order_number", "public_token", "subtotal", "discount_amount",
        "platform_fee_percentage", "platform_fee_amount", "total_amount",
        "paid_at", "verified_by", "verified_at", "created_at", "updated_at",
    )
    inlines = [OrderItemInline, PaymentReferenceInline]
    date_hierarchy = "created_at"
    actions = ["mark_paid", "mark_confirmed", "mark_ready", "mark_completed"]

    @admin.display(description="গ্রাহক")
    def customer(self, obj):
        return obj.user.email if obj.user else (obj.guest_email or obj.customer_name)

    @admin.display(description="অবস্থা")
    def status_badge(self, obj):
        colors = {
            "PENDING": "#D97706", "CONFIRMED": "#0E7373", "PROCESSING": "#2563EB",
            "READY": "#059669", "CANCELLED": "#DC2626", "COMPLETED": "#059669",
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            colors.get(obj.status, "#666"), obj.get_status_display(),
        )

    @admin.display(description="পেমেন্ট")
    def payment_badge(self, obj):
        colors = {
            "UNPAID": "#DC2626", "AWAITING_VERIFICATION": "#D97706",
            "PAID": "#059669", "REFUNDED": "#4A7E7E",
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            colors.get(obj.payment_status, "#666"), obj.get_payment_status_display(),
        )

    @admin.display(description="মোট", ordering="total_amount")
    def total_display(self, obj):
        return f"৳{obj.total_amount:,.2f}"

    @admin.action(description="পেমেন্ট যাচাই করুন (PAID + ইমেইল + কুপন)")
    def mark_paid(self, request, queryset):
        count = 0
        for order in queryset:
            if order.payment_status != Order.PaymentStatus.PAID:
                order.mark_paid(verified_by=request.user)
                count += 1
        self.message_user(request, f"{count}টি অর্ডার পরিশোধিত হিসেবে চিহ্নিত হয়েছে।")

    @admin.action(description="নিশ্চিত করুন (CONFIRMED)")
    def mark_confirmed(self, request, queryset):
        for order in queryset:
            order.transition(Order.Status.CONFIRMED)

    @admin.action(description="সংগ্রহের জন্য প্রস্তুত (READY)")
    def mark_ready(self, request, queryset):
        for order in queryset:
            order.transition(Order.Status.READY)

    @admin.action(description="সম্পন্ন করুন (COMPLETED + স্টক হ্রাস)")
    def mark_completed(self, request, queryset):
        for order in queryset:
            order.transition(Order.Status.COMPLETED)


@admin.register(PaymentInstruction)
class PaymentInstructionAdmin(ModelAdmin):
    list_display = ("method_name", "account_number", "account_name", "is_active")
    list_editable = ("is_active",)
