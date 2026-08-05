import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.services.xendit import XenditAPIError, XenditConfigurationError, XenditService
from _p2p.models import P2PPurchase
from _p2p.services.payment_transition import apply_xendit_payment_update
from _product.models import SavingTransaction
from _product.services.payment_transition import apply_saving_payment_update
from _payment.services import reconcile_pending_fees

logger = logging.getLogger(__name__)

MAX_RECORDS_PER_RUN = 50
EXPIRY_CUTOFF_HOURS = 48


class Command(BaseCommand):
    help = "Sync unpaid P2P purchases and saving transactions with Xendit payment status."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List unpaid records without making any API calls.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=EXPIRY_CUTOFF_HOURS)

        # --- P2P Purchases ---
        p2p_qs = (
            P2PPurchase.objects
            .filter(
                status=P2PPurchase.Status.WAITING_PAYMENT,
                xendit_session_id__isnull=False,
            )
            .exclude(session_expires_at__lt=cutoff)
            .order_by("created_at")
            [:MAX_RECORDS_PER_RUN]
        )
        p2p_total = len(p2p_qs)
        p2p_synced = 0
        p2p_errors = 0

        for purchase in p2p_qs:
            if dry_run:
                self.stdout.write(f"  [DRY-RUN] P2P {purchase.reference_id} ({purchase.xendit_session_id})")
                continue
            try:
                payload = XenditService.get_session_status(purchase.xendit_session_id)
                apply_xendit_payment_update(purchase, payload)
                p2p_synced += 1
                self.stdout.write(f"  [OK] P2P {purchase.reference_id} -> {purchase.status}")
            except (XenditAPIError, XenditConfigurationError) as exc:
                p2p_errors += 1
                logger.warning("Xendit sync failed for P2P %s: %s", purchase.reference_id, exc)
                self.stderr.write(f"  [ERR] P2P {purchase.reference_id}: {exc}")
            except Exception as exc:
                p2p_errors += 1
                logger.exception("Unexpected error syncing P2P %s", purchase.reference_id)
                self.stderr.write(f"  [ERR] P2P {purchase.reference_id}: {exc}")

        # --- Saving Transactions ---
        saving_qs = (
            SavingTransaction.objects
            .filter(
                status=SavingTransaction.Status.WAITING_PAYMENT,
                xendit_session_id__isnull=False,
            )
            .exclude(session_expires_at__lt=cutoff)
            .order_by("created_at")
            [:MAX_RECORDS_PER_RUN]
        )
        saving_total = len(saving_qs)
        saving_synced = 0
        saving_errors = 0

        for saving_txn in saving_qs:
            if dry_run:
                self.stdout.write(f"  [DRY-RUN] SAV {saving_txn.reference_id} ({saving_txn.xendit_session_id})")
                continue
            try:
                payload = XenditService.get_session_status(saving_txn.xendit_session_id)
                apply_saving_payment_update(saving_txn, payload)
                saving_synced += 1
                self.stdout.write(f"  [OK] SAV {saving_txn.reference_id} -> {saving_txn.status}")
            except (XenditAPIError, XenditConfigurationError) as exc:
                saving_errors += 1
                logger.warning("Xendit sync failed for SAV %s: %s", saving_txn.reference_id, exc)
                self.stderr.write(f"  [ERR] SAV {saving_txn.reference_id}: {exc}")
            except Exception as exc:
                saving_errors += 1
                logger.exception("Unexpected error syncing SAV %s", saving_txn.reference_id)
                self.stderr.write(f"  [ERR] SAV {saving_txn.reference_id}: {exc}")

        # --- Summary ---
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"Dry run: {p2p_total} P2P purchases, {saving_total} saving transactions pending."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Synced {p2p_synced}/{p2p_total} P2P purchases "
                f"({p2p_errors} errors), "
                f"{saving_synced}/{saving_total} saving transactions "
                f"({saving_errors} errors)."
            ))
            fee_run = reconcile_pending_fees(limit=MAX_RECORDS_PER_RUN)
            fee_style = self.style.WARNING if fee_run.error_count else self.style.SUCCESS
            self.stdout.write(fee_style(
                f"Fee reconciliation: {fee_run.processed_count} processed, "
                f"{fee_run.matched_count} matched, {fee_run.variance_count} variance, "
                f"{fee_run.error_count} errors."
            ))
