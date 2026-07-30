"""Seed simulator profiles for the current KS3 product catalogue."""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from _product.management.simulation_seed import SEED_VERSION, seed_product_simulations


class Command(BaseCommand):
    help = "Seed idempotent financial simulator profiles for current KS3 products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Fail when one of the known product slugs does not exist.",
        )

    def handle(self, *args, **options):
        try:
            simulations, missing = seed_product_simulations(strict=options["strict"])
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

        for simulation in simulations:
            state = "aktif" if simulation.is_enabled else "nonaktif sesuai karakter produk"
            self.stdout.write(f"  {simulation.product.title}: {state} · {simulation.get_strategy_display()}")
        if missing:
            self.stdout.write(self.style.WARNING(f"  dilewati karena belum ada: {', '.join(missing)}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Simulator seed {SEED_VERSION} ready: {len(simulations)} profile(s)."
            )
        )
