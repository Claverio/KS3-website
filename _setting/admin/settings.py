from django.urls import reverse
from wagtail.admin.viewsets.base import ViewSet
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from backend.helper.singleton import SingletonSnippetViewSet
from _setting.models import ContactSetting, EmailSetting, XenditSetting


class HomePageSettingViewSet(ViewSet):
    name = "homepage-settings"
    menu_label = "Homepage"
    menu_icon = "home"

    @property
    def menu_url(self):
        return reverse(
            "wagtailsettings:edit", args=["_setting", "homepagesetting"]
        )


class ContactSettingViewSet(SingletonSnippetViewSet):
    model = ContactSetting
    menu_label = "Kontak & Kantor"
    icon = "site"


class EmailSettingViewSet(SingletonSnippetViewSet):
    model = EmailSetting
    menu_label = "Email Notifikasi"
    icon = "envelope"


class XenditSettingViewSet(SingletonSnippetViewSet):
    model = XenditSetting
    menu_label = "Xendit"
    icon = "credit-card"


class GeneralSettingsGroup(SnippetViewSetGroup):
    menu_label = "General Settings"
    menu_icon = "gear"
    menu_name = "general-settings"
    menu_order = 800
    items = (
        HomePageSettingViewSet,
        ContactSettingViewSet,
        EmailSettingViewSet,
        XenditSettingViewSet,
    )


register_snippet(GeneralSettingsGroup)
