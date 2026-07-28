from _product.models import Product, ProductCategory


def make_product(**overrides):
    category, _ = ProductCategory.objects.get_or_create(name="Testing", slug="testing")
    values = {
        "category": category,
        "title": "Test Product",
        "slug": f"test-product-{Product.objects.count()}",
        "summary": "A test product summary.",
        "content": [],
        "is_published": True,
        "is_featured": False,
    }
    values.update(overrides)
    return Product.objects.create(**values)
