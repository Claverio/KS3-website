# P2P phase 1 operations

## Runtime

Use the shared uv environment:

```bash
/Users/stevenchristian/.venvs/dw/bin/python manage.py check
/Users/stevenchristian/.venvs/dw/bin/python manage.py migrate
```

Configure **General Settings → Email** and **General Settings → Xendit** in Wagtail.
For local webhook testing, set the Xendit public base URL to:

```text
https://semisoft-evergreen-hastily.ngrok-free.dev
```

Configure the Xendit Payment Session webhook as:

```text
https://semisoft-evergreen-hastily.ngrok-free.dev/api/p2p/webhooks/xendit/payment-session/
```

Keep the browser return base URL separate during local testing:

```text
http://127.0.0.1:8000
```

Xendit sends server callbacks to ngrok, but opens success/cancel return URLs
in the customer's browser, so localhost works when checkout is performed on
the same development machine.

The verification token configured in Xendit must exactly match the token in
the Xendit singleton. API keys and webhook tokens must never be copied into
fixtures, migrations, logs, or source control.

## Payment state

```text
creating → waiting_payment → paid
                           ├→ expired
                           ├→ canceled
                           └→ failed
```

The browser polls the local status endpoint only. While a purchase is pending,
that backend endpoint reconciles with Xendit at most once every 10 seconds.
Xendit polling and Xendit webhooks both call the same idempotent payment
transition service.

## Interactive acceptance test

Polling Xendit directly:

```bash
/Users/stevenchristian/.venvs/dw/bin/python manage.py simulate_p2p_purchase \
  --xendit-mode poll --payment-wait 300 --interval 5
```

Webhook-only observation through ngrok:

```bash
/Users/stevenchristian/.venvs/dw/bin/python manage.py simulate_p2p_purchase \
  --xendit-mode webhook --payment-wait 300 --interval 5
```

Resume an existing purchase without creating another Payment Session:

```bash
/Users/stevenchristian/.venvs/dw/bin/python manage.py simulate_p2p_purchase \
  --purchase-reference KS3-P2P-REFERENCE --xendit-mode webhook
```

The command exits non-zero for invalid configuration, invalid form data,
provider mismatch, a terminal non-paid status, or timeout.

## Automated verification

```bash
/Users/stevenchristian/.venvs/dw/bin/python manage.py makemigrations --check --dry-run
/Users/stevenchristian/.venvs/dw/bin/python manage.py test _p2p --settings=backend.settings.test
```

## Troubleshooting

- `403 Invalid webhook token`: compare the Xendit dashboard callback token to General Settings.
- CLI webhook timeout: confirm ngrok is online and the exact callback URL is registered in Xendit.
- CLI poll failures: check Xendit API URL/key and the stored Payment Session ID.
- Order remains `waiting_payment`: resume the watcher; do not create a duplicate order.
- Paid email is skipped: complete the SMTP user and App Password fields.
