from django.urls import path
from . import views

urlpatterns = [
    path("dokumen-publik/", views.public_doc_list, name="public_docs"),
    path("galeri/", views.image_gallery_list, name="image_gallery"),
]
