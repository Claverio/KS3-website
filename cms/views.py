from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.template import loader

from _p2p.models import P2P
from _product.models import Product
from _setting.models import HomePageSetting


class LandingView(TemplateView):
    template_name = "cms/pages/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home_settings"] = HomePageSetting.for_request(self.request)
        context["featured_projects"] = P2P.objects.select_related("category").filter(
            is_featured=True,
            is_published=True,
            category__is_active=True,
        )[:3]
        context["featured_products"] = Product.objects.select_related(
            "category", "card_image"
        ).filter(
            is_featured=True,
            is_published=True,
            category__is_active=True,
        )[:5]
        return context


landing_view = LandingView.as_view()
def robots_txt(request):
    template = loader.get_template("cms/robots.txt")
    return HttpResponse(template.render(), content_type="text/plain")


def llms_txt(request):
    template = loader.get_template("cms/llms.txt")
    return HttpResponse(template.render(), content_type="text/plain")


def sitemap_xml(request):
    template = loader.get_template("cms/sitemap.xml")
    return HttpResponse(template.render(), content_type="application/xml")
