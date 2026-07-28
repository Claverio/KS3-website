from django.urls import path
from . import views

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("llms.txt", views.llms_txt, name="llms_txt"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap_xml"),
    path("", views.landing_view, name="landing"),
]
