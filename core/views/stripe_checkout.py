import stripe 
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from decouple import config

from core.models import UserProfile

stripe.api_key = config("STRIPE_SECRET_KEY")

@login_required
def upgrade_to_pro(request):
    session = stripe.checkout.Session.create(
        payment_method_types = ['card'],
        line_items= [{
            'price_data' : {
                "currency" : "usd",
                "unit_amount" : 5000,
                "product_data" : {
                    "name" : "Pro Plan Subscription",
                },
            },
            "quantity" : 1,
        }],
        mode = "payment",
        success_url = request.build_absolute_uri("/api/v1/payment-success/"),
        cancel_url=request.build_absolute_uri("/api/v1/dashboard/"),
        client_reference_id = request.user.id
    )

    return redirect(session.url, code = 303)


@login_required
def payment_success(request):
    profile = request.user.userprofile
    profile.tier = "pro"
    profile.save()
    return render(request, "Payment_success.html")