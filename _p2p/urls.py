from django.urls import path

from . import views


urlpatterns = [
    path("peer-to-peer/", views.p2p_list, name="p2p_list"),
    path("peer-to-peer/<slug:slug>/", views.p2p_detail, name="p2p_details"),
    path("peer-to-peer/<slug:slug>/purchase/", views.p2p_purchase, name="p2p_purchase"),
    path("peer-to-peer/purchase/<uuid:public_id>/waiting/", views.p2p_waiting, name="p2p_purchase_waiting"),
    path("peer-to-peer/purchase/<uuid:public_id>/complete/", views.p2p_complete, name="p2p_booking_complete"),
    path("api/p2p/xendit/return/<uuid:public_id>/", views.p2p_xendit_return, name="p2p_xendit_return"),
    path("api/p2p/purchases/<uuid:public_id>/status/", views.purchase_status, name="p2p_purchase_status"),
    path("api/p2p/webhooks/xendit/payment-session/", views.xendit_payment_session_webhook, name="xendit_payment_session_webhook"),
]
