"""Safe, theme-native StreamField blocks shared by editable page content."""

from wagtail import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.embeds.blocks import EmbedBlock
from wagtail.images.blocks import ImageChooserBlock


RICH_TEXT_FEATURES = ["bold", "italic", "underline", "link", "ol", "ul"]


class HeadingBlock(blocks.StructBlock):
    level = blocks.ChoiceBlock(
        choices=(("h2", "H2"), ("h3", "H3"), ("h4", "H4")), default="h3"
    )
    title = blocks.CharBlock(max_length=160)

    class Meta:
        icon = "title"
        label = "Heading"
        template = "cms/blocks/streamfield/heading.html"


class ParagraphBlock(blocks.StructBlock):
    content = blocks.RichTextBlock(features=RICH_TEXT_FEATURES)

    class Meta:
        icon = "pilcrow"
        label = "Rich paragraph"
        template = "cms/blocks/streamfield/paragraph.html"


class TwoColumnTextBlock(blocks.StructBlock):
    left = blocks.RichTextBlock(features=RICH_TEXT_FEATURES)
    right = blocks.RichTextBlock(features=RICH_TEXT_FEATURES)

    class Meta:
        icon = "columns"
        label = "Two-column text"
        template = "cms/blocks/streamfield/two_column_text.html"


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    alt_text = blocks.CharBlock(required=False, max_length=160)
    caption = blocks.CharBlock(required=False, max_length=255)

    class Meta:
        icon = "image"
        label = "Image"
        template = "cms/blocks/streamfield/image.html"


class TwoColumnImageBlock(blocks.StructBlock):
    left_image = ImageChooserBlock(label="Left image")
    left_alt_text = blocks.CharBlock(required=False, max_length=160)
    right_image = ImageChooserBlock(label="Right image")
    right_alt_text = blocks.CharBlock(required=False, max_length=160)

    class Meta:
        icon = "image"
        label = "Two-column images"
        template = "cms/blocks/streamfield/two_column_image.html"


class ImageTextBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    image_position = blocks.ChoiceBlock(
        choices=(("left", "Image left"), ("right", "Image right")), default="left"
    )
    title = blocks.CharBlock(required=False, max_length=160)
    content = blocks.RichTextBlock(features=RICH_TEXT_FEATURES)

    class Meta:
        icon = "image"
        label = "Image and text"
        template = "cms/blocks/streamfield/image_text.html"


class ListBlock(blocks.StructBlock):
    style = blocks.ChoiceBlock(
        choices=(("unordered", "Bullet list"), ("ordered", "Numbered list")),
        default="unordered",
    )
    items = blocks.ListBlock(blocks.CharBlock(max_length=255), min_num=1)

    class Meta:
        icon = "list-ul"
        label = "List"
        template = "cms/blocks/streamfield/list.html"


class ManualTableBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160)
    columns = blocks.ListBlock(blocks.CharBlock(max_length=80), min_num=1)
    rows = blocks.ListBlock(
        blocks.StructBlock(
            [("cells", blocks.ListBlock(blocks.CharBlock(max_length=255), min_num=1))]
        ),
        min_num=1,
    )
    footer_note = blocks.CharBlock(required=False, max_length=255)

    class Meta:
        icon = "table"
        label = "Table"
        template = "cms/blocks/streamfield/manual_table.html"


class BlockquoteBlock(blocks.StructBlock):
    quote = blocks.RichTextBlock(features=["bold", "italic", "link"])
    author = blocks.CharBlock(required=False, max_length=100)

    class Meta:
        icon = "openquote"
        label = "Quote"
        template = "cms/blocks/streamfield/blockquote.html"


class CalloutBlock(blocks.StructBlock):
    tone = blocks.ChoiceBlock(
        choices=(("info", "Information"), ("warning", "Warning"), ("success", "Success")),
        default="info",
    )
    title = blocks.CharBlock(required=False, max_length=160)
    content = blocks.RichTextBlock(features=RICH_TEXT_FEATURES)

    class Meta:
        icon = "info-circle"
        label = "Callout / notice"
        template = "cms/blocks/streamfield/callout.html"


class AccordionBlock(blocks.StructBlock):
    items = blocks.ListBlock(
        blocks.StructBlock(
            [
                ("title", blocks.CharBlock(max_length=200)),
                ("content", blocks.RichTextBlock(features=RICH_TEXT_FEATURES)),
            ]
        ),
        min_num=1,
    )

    class Meta:
        icon = "list-ul"
        label = "Accordion"
        template = "cms/blocks/streamfield/accordion.html"


class DocumentBlock(blocks.StructBlock):
    document = DocumentChooserBlock()
    label = blocks.CharBlock(max_length=100, default="Download document")

    class Meta:
        icon = "doc-full"
        label = "Document download"
        template = "cms/blocks/streamfield/document.html"


class VideoBlock(blocks.StructBlock):
    embed = EmbedBlock(help_text="YouTube, Vimeo, or another supported URL")
    caption = blocks.CharBlock(required=False, max_length=255)

    class Meta:
        icon = "media"
        label = "Video / embed"
        template = "cms/blocks/streamfield/video.html"


class SeparatorBlock(blocks.StaticBlock):
    class Meta:
        icon = "horizontalrule"
        label = "Separator"
        template = "cms/blocks/streamfield/separator.html"


class SpacingBlock(blocks.StructBlock):
    size = blocks.ChoiceBlock(
        choices=(("20", "Small"), ("40", "Medium"), ("60", "Large")), default="40"
    )

    class Meta:
        icon = "arrows-up-down"
        label = "Spacing"
        template = "cms/blocks/streamfield/spacing.html"


def page_content_blocks():
    return [
        ("heading", HeadingBlock()),
        ("paragraph", ParagraphBlock()),
        ("two_column_text", TwoColumnTextBlock()),
        ("image", ImageBlock()),
        ("two_column_image", TwoColumnImageBlock()),
        ("image_text", ImageTextBlock()),
        ("list", ListBlock()),
        ("manual_table", ManualTableBlock()),
        ("blockquote", BlockquoteBlock()),
        ("callout", CalloutBlock()),
        ("accordion", AccordionBlock()),
        ("document", DocumentBlock()),
        ("video", VideoBlock()),
        ("separator", SeparatorBlock()),
        ("spacing", SpacingBlock()),
    ]


# Backward-compatible import name used by older apps.
misc_page_body_blocks = page_content_blocks
