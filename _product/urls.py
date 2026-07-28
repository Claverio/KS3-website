from django.urls import path
from django.views.generic import RedirectView

from _product import views


urlpatterns = [
    path("product", RedirectView.as_view(pattern_name="product", permanent=True), name="product_legacy"),
    path("product/", views.product_list, name="product"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
]
