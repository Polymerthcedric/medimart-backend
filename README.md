# Medimart Backend

Flask REST API for [Medimart](https://github.com/Polymerthcedric/Medimart) — a medical supplies e-commerce platform with M-Pesa payments and AI chatbot.

**Live API:** https://polymerthcedric.pythonanywhere.com/api  
**Frontend Repo:** [Polymerthcedric/Medimart](https://github.com/Polymerthcedric/Medimart)

---

## Features

- **User Authentication** — Sign up and sign in endpoints with session persistence on the frontend
- **Product Management** — Add products with name, description, price, and image upload; delete products with cascade cleanup of the image file
- **M-Pesa STK Push** — Initiate Safaricom M-Pesa payments via sandbox API; auto-formats phone numbers to 254XXXXXXXXX; uses actual product amount (not hardcoded); includes callback endpoint
- **AI Chatbot** — NLTK rule-based chatbot for customer support queries
- **MySQL Database** — Hosted on PythonAnywhere with `users` and `product_details` tables

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Framework** | Python / Flask |
| **Database** | PyMySQL → MySQL (PythonAnywhere) |
| **Chatbot** | NLTK `nltk.chat.util` |
| **Payments** | Safaricom M-Pesa Sandbox API |
| **WSGI** | Gunicorn (PythonAnywhere) |

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/signup` | Create account (form: `username`, `email`, `password`, `phone`) |
| POST | `/api/signin` | Login (form: `email`, `password`) → returns user object |
| POST | `/api/add_product` | Add product (multipart: `product_name`, `product_description`, `product_cost`, `product_photo`) |
| GET | `/api/get_product_details` | List all products → JSON array |
| POST | `/api/delete_product` | Delete product by ID (form: `product_id`) |
| POST | `/api/mpesa_payment` | Initiate STK push (form: `amount`, `phone`) |
| POST | `/api/mpesa_callback` | M-Pesa transaction result callback |
| POST | `/api/chat` | Chatbot message (JSON: `{"message": "..."}`) |

## Database

### `users` table

| Column | Type |
|--------|------|
| `id` | INT AUTO_INCREMENT PK |
| `username` | VARCHAR |
| `email` | VARCHAR |
| `password` | VARCHAR |
| `phone` | VARCHAR |

### `product_details` table

| Column | Type |
|--------|------|
| `product_id` | INT AUTO_INCREMENT PK |
| `product_name` | VARCHAR |
| `product_description` | TEXT |
| `product_cost` | DECIMAL |
| `product_photo` | VARCHAR (filename) |

## Deployment (PythonAnywhere)

1. Push changes to the `main` branch of this repo
2. Log into [pythonanywhere.com](https://www.pythonanywhere.com)
3. Open a Bash console and run:
   ```bash
   cd ~/medimart-backend && git pull
   ```
4. Go to the **Web** tab and click **Reload**

> Static images are served from `/static/images/` — ensure this directory exists in the web app root.

## M-Pesa Sandbox Configuration

The app uses Safaricom sandbox credentials (hardcoded — move to environment variables for production):

| Credential | Value |
|------------|-------|
| Consumer Key | Sandbox key |
| Consumer Secret | Sandbox secret |
| Passkey | Standard sandbox passkey |
| Shortcode | `174379` (sandbox PayBill) |
| Callback URL | `https://polymerthcedric.pythonanywhere.com/api/mpesa_callback` |

**Phone number input:** Accepts `07XXXXXXXX`, `2547XXXXXXXX`, or `7XXXXXXXX` — automatically normalized to `254XXXXXXXXX`.

---

*Built by [Fidel Cedric Odoyo](https://polymerthcedric.github.io/portfolio)*
