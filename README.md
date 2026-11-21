# Medimart API prototype

A small Flask API for the Medimart storefront demo. It provides product and account routes, a scripted chat helper, and an M-Pesa **sandbox** flow.

This is a learning project. It is **not** a production commerce service or a medical service:

- Passwords are stored as hashes in a development database; there is no JWT and no session layer.
- The chat helper matches keywords with NLTK and returns fixed answers. It is not an AI model.
- Payment requests only accept the Safaricom **sandbox** host. No real money moves.
- The M-Pesa callback checks a shared secret in the URL and validates the JSON shape, but it does not save a transaction or confirm an order.
- CORS allows only the configured origins (localhost by default).
- The product add/delete routes are disabled unless an admin token is configured.

## Run locally

Install the dependencies and create your environment file:

```sh
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, then load it into your shell and start the app:

```sh
set -a
. ./.env
set +a
python app.py
```

`app.py` creates `static/images/` on startup so photo uploads work from a fresh clone.

Never put database or payment credentials in source files. See **Security limits of this prototype** below about credentials in older commits.

## Environment variables

All values come from `.env` (loaded into the process environment). See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `DB_HOST` | Database host (required) |
| `DB_PORT` | Database port, defaults to `3306` |
| `DB_USER` | Database user (required) |
| `DB_PASSWORD` | Database password (required) |
| `DB_NAME` | Database name (required) |
| `ADMIN_API_TOKEN` | Shared token for add/delete product; if unset, those routes return 503 |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed by CORS; defaults to `http://localhost,http://127.0.0.1` |
| `CALLBACK_SECRET` | Shared secret required in the M-Pesa callback URL; if unset, the callback returns 503 |
| `MPESA_API_BASE` | Safaricom API base URL; the app rejects hosts other than the sandbox |
| `MPESA_CONSUMER_KEY` | Sandbox app consumer key |
| `MPESA_CONSUMER_SECRET` | Sandbox app consumer secret |
| `MPESA_PASSKEY` | Sandbox passkey |
| `MPESA_SHORT_CODE` | Sandbox paybill/short code |
| `MPESA_CALLBACK_URL` | Public URL that receives the sandbox callback; include `?secret=...` matching `CALLBACK_SECRET` |

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/signup` | Create a demo account with a hashed password |
| POST | `/api/signin` | Check credentials against the stored hash |
| POST | `/api/add_product` | Add a listing with a photo (requires `X-Admin-Token`) |
| POST | `/api/delete_product` | Remove a listing (requires `X-Admin-Token`) |
| GET | `/api/get_product_details` | List product details |
| POST | `/api/chat` | Return a scripted answer for a message |
| POST | `/api/mpesa_payment` | Start a sandbox STK Push |
| POST | `/api/mpesa_callback?secret=...` | Receive the sandbox result; verifies our URL secret and payload shape |

The storefront calls the hosted demo API by default. See the [frontend prototype](https://github.com/Polymerthcedric/Medimart) to run both together.

### Callback verification is a demo check

`CALLBACK_SECRET` is a **demo verification measure only**: the app requires the `secret` query parameter in the callback URL and compares it in constant time, then checks that the JSON has the expected STK Push shape. This is **not** Safaricom's own callback signature standard and does not prove a payment happened. Use Safaricom's documented verification/signature mechanism and server-side reconciliation before handling real money.

## Security limits of this prototype

This repository is a public, educational demo and is **not production ready**.

- **Old commits contain credentials.** The git history includes committed database and M-Pesa credentials. History was deliberately **not** rewritten. Anyone with access to the repository can read those values.
- The owner must **rotate the database and M-Pesa credentials in the provider dashboards** (and update `.env`), not just edit current files. Revoking the exposed keys is the only way to make them useless.
- `ADMIN_API_TOKEN`, `CALLBACK_SECRET`, and `ALLOWED_ORIGINS` are minimal guardrails for a demo, not a real identity, authorization, or payment-verification system. Do not reuse production secrets here.
- The callback secret is carried in the URL, so it can be exposed in access logs or referrer headers, and there is no replay protection. Real integrations must use Safaricom's signature process and reconciliation.
- Uploads are limited to a small image allowlist, a 2 MiB request cap, and unique filenames, but there is no virus scanning, image decoding, or content inspection.
- There is no rate limiting, audit trail, CSRF protection, or transaction persistence. Do not expose this service to untrusted traffic.

## Tests

Offline tests use Flask's test client, stubbing database calls and the environment; they need no database or network:

```sh
python -m pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
