from django.urls import path
from django.views.generic import RedirectView

from _product import views


urlpatterns = [
    path("nabung/", views.saving_create, name="saving_create"),
    path("nabung/<uuid:public_id>/waiting/", views.saving_waiting, name="saving_waiting"),
    path("nabung/<uuid:public_id>/complete/", views.saving_complete, name="saving_complete"),
    path("api/product/savings/<uuid:public_id>/status/", views.saving_status, name="saving_status"),
    path("api/product/savings/<uuid:public_id>/return/", views.saving_xendit_return, name="saving_xendit_return"),
    path("product", RedirectView.as_view(pattern_name="product", permanent=True), name="product_legacy"),
    path("product/", views.product_list, name="product"),
    path("product/<slug:slug>/simulation/", views.product_simulation, name="product_simulation"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("api/product/webhooks/xendit/payment-session/", views.saving_xendit_webhook, name="saving_xendit_webhook"),
]
