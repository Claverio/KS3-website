from django.db.models import Sum
from django.db.models.functions import Coalesce

from _p2p.models import P2PPurchase


def reserved_slot_count(project):
    return int(
        project.purchases.filter(status__in=P2PPurchase.reserving_statuses()).aggregate(
            total=Coalesce(Sum("slot_quantity"), 0)
        )["total"]
    )


def available_slot_count(project):
    return max(project.total_slots - reserved_slot_count(project), 0)
