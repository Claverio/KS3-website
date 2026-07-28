"""Restricted StreamField blocks for repeatable homepage content."""

from wagtail import blocks


HOME_ICON_CHOICES = (
    ("bi-building-check", "Building check"),
    ("bi-wallet2", "Wallet"),
    ("bi-shop", "Shop"),
    ("bi-phone", "Phone"),
    ("bi-graph-up-arrow", "Growth chart"),
    ("bi-shield-check", "Shield check"),
    ("bi-check-circle-fill", "Check circle"),
)


class TextItemBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=160)

    class Meta:
        icon = "list-ul"
        label = "Text item"


class MarqueeItemBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=120)
    tone = blocks.ChoiceBlock(
        choices=(("dark", "Dark / bold"), ("muted", "Muted")), default="dark"
    )

    class Meta:
        icon = "horizontalrule"
        label = "Marquee item"


class IconTextItemBlock(blocks.StructBlock):
    icon = blocks.ChoiceBlock(choices=HOME_ICON_CHOICES)
    title = blocks.CharBlock(max_length=120)
    description = blocks.TextBlock(max_length=300)

    class Meta:
        icon = "pick"
        label = "Icon and text"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(max_length=240)
    answer = blocks.RichTextBlock(features=["bold", "italic", "link", "ol", "ul"])

    class Meta:
        icon = "help"
        label = "FAQ item"


def text_item_blocks():
    return [("item", TextItemBlock())]


def marquee_item_blocks():
    return [("item", MarqueeItemBlock())]


def icon_text_item_blocks():
    return [("item", IconTextItemBlock())]


def faq_item_blocks():
    return [("item", FAQItemBlock())]
