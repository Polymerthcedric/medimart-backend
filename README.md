# Medimart API prototype

A small Flask API for the Medimart storefront demo. It provides product and account routes, a scripted chat helper, and an M-Pesa **sandbox** flow.

This is a learning project. It is **not** a production commerce service or a medical service:

- Passwords are stored as hashes in a development database; there is no JWT and no session layer.
- The chat helper matches keywords with NLTK and returns fixed answers. It is not an AI model.
- Payment requests only accept the Safaricom **sandbox** host. No real money moves.
- The M-Pesa callback currently prints the payload and returns success. It does **not** verify the callback signature, save a transaction, or confirm an order.
- CORS allows every origin, which is fine for a local demo but not for a deployed service.

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

Never put database or payment credentials in source files. Credentials that were committed in older versions of this repository should be treated as exposed and rotated before the service is used again.

## Environment variables

All values come from `.env` (loaded into the process environment). See `.env.example`.

| Variable | Purpose |
| --- | --- |
| `DB_HOST` | Database host (required) |
| `DB_PORT` | Database port, defaults to `3306` |
| `DB_USER` | Database user (required) |
| `DB_PASSWORD` | Database password (required) |
| `DB_NAME` | Database name (required) |
| `MPESA_API_BASE` | Safaricom API base URL; the app rejects hosts other than the sandbox |
| `MPESA_CONSUMER_KEY` | Sandbox app consumer key |
| `MPESA_CONSUMER_SECRET` | Sandbox app consumer secret |
| `MPESA_PASSKEY` | Sandbox passkey |
| `MPESA_SHORT_CODE` | Sandbox paybill/short code |
| `MPESA_CALLBACK_URL` | Public URL that receives the sandbox callback |

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| POST | `/api/signup` | Create a demo account with a hashed password |
| POST | `/api/signin` | Check credentials against the stored hash |
| POST | `/api/add_product` | Add a listing with a photo |
| POST | `/api/delete_product` | Remove a listing |
| GET | `/api/get_product_details` | List product details |
| POST | `/api/chat` | Return a scripted answer for a message |
| POST | `/api/mpesa_payment` | Start a sandbox STK Push |
| POST | `/api/mpesa_callback` | Receive the sandbox result (prints it, returns success) |

The storefront calls the hosted demo API by default. See the [frontend prototype](https://github.com/Polymerthcedric/Medimart) to run both together.

## License

MIT — see [LICENSE](LICENSE).
