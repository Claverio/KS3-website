from decimal import Decimal

from _product.models import Product, ProductCategory, ProductSimulation, SavingTransaction


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


def make_simulation(product=None, **overrides):
    product = product or make_product()
    values = {
        "product": product,
        "is_enabled": True,
        "product_kind": ProductSimulation.ProductKind.SAVINGS,
        "strategy": ProductSimulation.Strategy.SAVINGS_SIMPLE,
        "amount_min": Decimal("1000000"),
        "amount_max": Decimal("100000000"),
        "amount_default": Decimal("12000000"),
        "amount_step": Decimal("100000"),
        "tenor_mode": ProductSimulation.TenorMode.RANGE,
        "tenor_min_months": 1,
        "tenor_max_months": 120,
        "tenor_default_months": 12,
        "tenor_step_months": 1,
        "rate_mode": ProductSimulation.RateMode.FIXED,
        "base_annual_rate": Decimal("12"),
        "rate_application": ProductSimulation.RateApplication.LOCKED,
        "breakdown_mode": ProductSimulation.BreakdownMode.AUTO_COMPACT,
        "show_chart": True,
        "show_table": True,
    }
    values.update(overrides)
    return ProductSimulation.objects.create(**values)


def make_saving_transaction(product=None, **overrides):
    product = product or make_product()
    values = {
        "reference_id": f"KS3-SAV-TEST-{SavingTransaction.objects.count():04d}",
        "transaction_code": f"KS3-STR-TEST-{SavingTransaction.objects.count():04d}",
        "product": product,
        "full_name": "Budi Santoso",
        "phone": "081234567890",
        "email": "budi@example.com",
        "nik": "1234567890123456",
        "is_new_member": False,
        "nomor_anggota": "AGT-001",
        "amount": Decimal("500000"),
        "service_fee": Decimal("0"),
        "total_amount": Decimal("500000"),
        "currency": "IDR",
        "status": SavingTransaction.Status.WAITING_PAYMENT,
        "xendit_session_id": f"ps-sav-{SavingTransaction.objects.count():025d}",
        "xendit_session_status": "ACTIVE",
    }
    values.update(overrides)
    return SavingTransaction.objects.create(**values)
