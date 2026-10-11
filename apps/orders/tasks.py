from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


@shared_task
def send_order_confirmation_email(order_id):
    from .models import Order

    order = Order.objects.filter(pk=order_id).first()
    if not order or not order.contact_email:
        return "no-recipient"
    body = render_to_string("orders/email_confirmation.txt", {"order": order})
    send_mail(
        subject=f"অর্ডার নিশ্চিতকরণ — {order.order_number}",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.contact_email],
        fail_silently=True,
    )
    return order.order_number


@shared_task
def on_order_paid(order_id):
    """Runs when admin verifies payment: email + next-purchase coupon."""
    from apps.promotions.services import issue_next_purchase_coupon

    from .models import Order

    order = Order.objects.filter(pk=order_id).first()
    if not order:
        return "missing"

    coupon = issue_next_purchase_coupon(order)

    if order.contact_email:
        body = render_to_string(
            "orders/email_paid.txt", {"order": order, "coupon": coupon}
        )
        send_mail(
            subject=f"পেমেন্ট যাচাই সম্পন্ন — {order.order_number}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.contact_email],
            fail_silently=True,
        )
    return coupon.code if coupon else "no-coupon"
