"""Interactive real-provider P2P purchase and payment verification harness."""

import time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from _p2p.forms import P2PPurchaseForm
from _p2p.models import P2P, P2PPurchase
from _p2p.services import create_p2p_purchase, synchronize_xendit_purchase
from _p2p.services.purchase_workflow import PurchaseWorkflowError
from _payment.services import FeeConfigurationError, active_channels, resolve_fee
from _setting.models import XenditSetting
from backend.services.xendit import XenditError


class Command(BaseCommand):
    help = "Create a real P2P purchase and verify Xendit via polling or webhook-only observation."

    def add_arguments(self, parser):
        parser.add_argument("--xendit-mode", choices=("ask", "poll", "webhook"), default="ask")
        parser.add_argument("--payment-wait", type=int, default=300)
        parser.add_argument("--interval", type=int, default=5)
        parser.add_argument("--project-id", type=int)
        parser.add_argument("--purchase-reference")

    def _ask(self, prompt, *, optional=False):
        value = input(prompt).strip()
        if not value and not optional:
            raise CommandError("Input is required; no purchase was created.")
        return value

    def _select_project(self, project_id=None):
        projects = list(
            P2P.objects.select_related("category").filter(
                status=P2P.Status.OPEN, is_published=True, category__is_active=True
            )
        )
        projects = [project for project in projects if project.can_purchase]
        if not projects:
            raise CommandError("No purchasable P2P projects exist.")
        self.stdout.write("\nAvailable P2P projects:")
        for project in projects:
            self.stdout.write(
                f"  [{project.pk}] {project.title} | Rp{project.slot_price:,.0f}/slot | "
                f"available {project.available_slots}/{project.total_slots} | "
                f"{project.interest_rate}% p.a. | {project.tenor_months} months"
            )
        selected_id = project_id or self._ask("Choose project ID: ")
        try:
            selected_id = int(selected_id)
            return next(project for project in projects if project.pk == selected_id)
        except (ValueError, StopIteration) as exc:
            raise CommandError("Project ID is invalid or not purchasable.") from exc

    def _collect_form(self, project):
        channel = active_channels("p2p").first()
        if not channel:
            raise CommandError("No Virtual Account channel is enabled for P2P.")
        self.stdout.write(f"Using payment channel: {channel.display_name}")
        data = {
            "slot_quantity": self._ask("Number of slots: "),
            "full_name": self._ask("Full name (as on KTP): "),
            "phone": self._ask("Phone / WhatsApp: "),
            "email": self._ask("Email: "),
            "nik": self._ask("NIK (optional): ", optional=True),
            "note": self._ask("Admin note (optional): ", optional=True),
            "xendit_channel": channel.code,
        }
        form = P2PPurchaseForm(data=data, project=project)
        if not form.is_valid():
            errors = "; ".join(
                f"{field}: {', '.join(messages)}" for field, messages in form.errors.items()
            )
            raise CommandError(f"Purchase data is invalid: {errors}")
        return form.cleaned_data

    def _choose_mode(self, mode):
        if mode != "ask":
            return mode
        answer = self._ask("Payment detection: [1] poll Xendit, [2] webhook only: ")
        if answer == "1":
            return "poll"
        if answer == "2":
            return "webhook"
        raise CommandError("Choose payment detection mode 1 or 2.")

    def _wait(self, purchase, *, seconds, interval, mode):
        method = "polling Xendit" if mode == "poll" else "waiting for the Xendit webhook"
        self.stdout.write(f"\nWaiting up to {seconds}s; {method}. Keep this command open.")
        deadline = time.monotonic() + seconds
        previous = None
        while time.monotonic() < deadline:
            if mode == "poll" and not purchase.is_final:
                try:
                    purchase = synchronize_xendit_purchase(purchase)
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"  Xendit poll failed; retrying: {exc}"))
            purchase.refresh_from_db()
            state = (purchase.status, purchase.xendit_session_status)
            if state != previous:
                self.stdout.write(
                    f"  {timezone.localtime():%H:%M:%S} local={state[0]} provider={state[1] or '-'}"
                )
                previous = state
            if purchase.is_final:
                if purchase.status == P2PPurchase.Status.PAID:
                    self.stdout.write(self.style.SUCCESS("Payment completed safely."))
                    return
                raise CommandError(f"Payment ended with status {purchase.status}.")
            time.sleep(interval)
        raise CommandError(
            "Payment wait timed out. Use --purchase-reference to resume without creating another session."
        )

    def handle(self, *args, **options):
        if options["payment_wait"] < 1 or options["interval"] < 1:
            raise CommandError("Payment wait and interval must be positive.")
        setting = XenditSetting.load()
        if (
            not setting.is_active
            or not setting.api_key
        ):
            raise CommandError("Active Xendit settings and API key are required.")
        mode = self._choose_mode(options["xendit_mode"])
        if mode == "webhook" and not setting.webhook_verification_token:
            raise CommandError("Webhook mode requires the Xendit webhook verification token.")
        reference = options.get("purchase_reference")
        if reference:
            try:
                purchase = P2PPurchase.objects.select_related("project").get(
                    reference_id=reference
                )
            except P2PPurchase.DoesNotExist as exc:
                raise CommandError("Purchase reference was not found.") from exc
            self.stdout.write(f"Resuming {purchase.reference_id} ({purchase.project.title}).")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "This creates a REAL purchase and REAL Xendit Payment Session. It never fakes payment state."
                )
            )
            project = self._select_project(options.get("project_id"))
            cleaned = self._collect_form(project)
            quantity = cleaned["slot_quantity"]
            try:
                fee = resolve_fee(
                    channel_code=cleaned["xendit_channel"],
                    route="p2p",
                    principal_amount=project.slot_price * quantity,
                )
            except FeeConfigurationError as exc:
                raise CommandError(str(exc)) from exc
            total = (project.slot_price * quantity) + fee.total_fee
            self.stdout.write(
                f"\nReady: project={project.title}, slots={quantity}, total=Rp{total:,.0f}, "
                f"buyer={cleaned['full_name']} <{cleaned['email']}>"
            )
            if self._ask("Type CREATE to create the real purchase: ") != "CREATE":
                self.stdout.write("Canceled. No purchase was created.")
                return
            try:
                purchase = create_p2p_purchase(
                    project=project, **cleaned
                )
            except (PurchaseWorkflowError, XenditError) as exc:
                raise CommandError(f"Purchase creation failed cleanly: {exc}") from exc
            self.stdout.write(self.style.SUCCESS(f"Purchase created: {purchase.reference_id}"))
            self.stdout.write(f"Booking number: {purchase.booking_number}")
            self.stdout.write(f"Payment URL: {purchase.payment_link_url}")
        self._wait(
            purchase,
            seconds=options["payment_wait"],
            interval=options["interval"],
            mode=mode,
        )
