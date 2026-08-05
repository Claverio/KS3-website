from django.core.management.base import BaseCommand

from _payment.services import reconcile_pending_fees


class Command(BaseCommand):
    help = "Pull actual Xendit transaction fees and reconcile them against charged snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        run = reconcile_pending_fees(limit=max(1, min(options["limit"], 500)))
        style = self.style.WARNING if run.error_count else self.style.SUCCESS
        self.stdout.write(
            style(
                f"Fee reconciliation #{run.pk}: processed={run.processed_count}, "
                f"matched={run.matched_count}, variance={run.variance_count}, "
                f"errors={run.error_count}."
            )
        )
