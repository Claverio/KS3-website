from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSetGroup

from backend.helper.singleton import SingletonSnippetViewSet
from _setting.models import ContactSetting, EmailSetting, XenditSetting


class ContactSettingViewSet(SingletonSnippetViewSet):
    model = ContactSetting
    menu_label = "Contact"
    icon = "site"


class EmailSettingViewSet(SingletonSnippetViewSet):
    model = EmailSetting
    menu_label = "Email"
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
    items = (ContactSettingViewSet, EmailSettingViewSet, XenditSettingViewSet)


register_snippet(GeneralSettingsGroup)
