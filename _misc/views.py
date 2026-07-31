from django.shortcuts import render
from .models import PublicDocument, ImageGallery

def public_doc_list(request):
    docs = PublicDocument.objects.filter(is_published=True).select_related('document').order_by('sort_order', '-upload_date')
    context = {
        'docs': docs,
        'page_title': 'Dokumen Publik',
        'page_description': 'Akses dan unduh berkas-berkas serta laporan resmi dari Koperasi KS3.',
    }
    return render(request, '_misc/public_doc_list.html', context)

def image_gallery_list(request):
    galleries = ImageGallery.objects.filter(is_published=True).select_related('image').order_by('sort_order', '-created_at')
    context = {
        'galleries': galleries,
        'page_title': 'Galeri',
        'page_description': 'Galeri foto dan dokumentasi kegiatan Koperasi KS3.',
    }
    return render(request, '_misc/gallery_list.html', context)
