# Medimart API prototype

A Flask API for the Medimart storefront. It includes product and account routes, a scripted chat helper, and an M-Pesa sandbox flow. This is a learning project, not a production commerce or medical service.

## Run locally

Install the dependencies with `pip install -r requirements.txt`, copy `.env.example` to `.env`, and add your development database and M-Pesa sandbox values. Load them in a Bash shell before starting the app:

Do not put database or payment credentials in source files. Credentials that were previously committed should be rotated before this service is used again.

```sh
cp .env.example .env
# Edit .env, then load its values in this shell.
set -a
. ./.env
set +a
python app.py
```
