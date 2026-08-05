from django.urls import path

from .views import fee_quote


urlpatterns = [
    path("api/payment/xendit/fee-quote/", fee_quote, name="xendit_fee_quote"),
]
