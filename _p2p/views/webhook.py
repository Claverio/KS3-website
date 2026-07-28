import hashlib
import hmac
import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from _p2p.models import P2PPurchase
from _p2p.services.payment_transition import PaymentTransitionError, apply_xendit_payment_update
from _setting.models import XenditSetting


@csrf_exempt
@require_POST
def xendit_payment_session_webhook(request):
    setting = XenditSetting.load()
    received_token = request.headers.get("x-callback-token", "")
    if not setting.webhook_verification_token or not hmac.compare_digest(
        received_token, setting.webhook_verification_token
    ):
        return JsonResponse({"detail": "Invalid webhook token."}, status=403)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Invalid JSON."}, status=400)
    event = payload.get("event")
    if event not in {"payment_session.completed", "payment_session.expired"}:
        return JsonResponse({"detail": "Unsupported event."}, status=400)
    data = payload.get("data") or {}
    reference_id = data.get("reference_id")
    try:
        purchase = P2PPurchase.objects.get(reference_id=reference_id)
    except P2PPurchase.DoesNotExist:
        return JsonResponse({"detail": "Purchase not found."}, status=404)
    webhook_id = request.headers.get("webhook-id") or hashlib.sha256(request.body).hexdigest()
    if purchase.xendit_webhook_id == webhook_id:
        return JsonResponse({"status": "duplicate"})
    try:
        apply_xendit_payment_update(
            purchase, payload, webhook_id=webhook_id, webhook_payload=payload
        )
    except PaymentTransitionError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse({"status": "accepted"})
