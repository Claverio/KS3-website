from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from _p2p.models import P2P, P2PCategory, P2PPurchase


def make_project(**overrides):
    category, _ = P2PCategory.objects.get_or_create(name="Testing", slug="testing")
    values = {
        "category": category,
        "title": "Test Project",
        "slug": f"test-project-{P2P.objects.count()}",
        "summary": "Test funding project.",
        "status": P2P.Status.OPEN,
        "target_amount": Decimal("1000000"),
        "slot_price": Decimal("100000"),
        "service_fee": Decimal("2750"),
        "total_slots": 10,
        "interest_rate": Decimal("12"),
        "tenor_months": 12,
        "funding_deadline": timezone.now() + timedelta(days=10),
        "project_start_date": timezone.localdate() + timedelta(days=20),
        "project_end_date": timezone.localdate() + timedelta(days=385),
        "is_published": True,
    }
    values.update(overrides)
    return P2P.objects.create(**values)


def make_purchase(project=None, **overrides):
    project = project or make_project()
    values = {
        "reference_id": f"REF-{P2PPurchase.objects.count()}",
        "booking_number": f"BOOK-{P2PPurchase.objects.count()}",
        "project": project,
        "full_name": "Budi Santoso",
        "phone": "081234567890",
        "email": "budi@example.com",
        "nik": "1234567890123456",
        "slot_quantity": 1,
        "unit_price": project.slot_price,
        "subtotal": project.slot_price,
        "service_fee": project.service_fee,
        "total_amount": project.slot_price + project.service_fee,
        "status": P2PPurchase.Status.WAITING_PAYMENT,
        "xendit_session_id": f"ps-{P2PPurchase.objects.count():025d}",
        "xendit_session_status": "ACTIVE",
    }
    values.update(overrides)
    return P2PPurchase.objects.create(**values)
