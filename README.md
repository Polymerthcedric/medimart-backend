# Medimart Backend

Flask REST API for Medimart — a medical supplies e-commerce platform.

## Features

- User authentication (signup/signin)
- Product CRUD with image upload
- AI chatbot (NLTK rule-based)
- M-Pesa STK Push integration (sandbox)

## Tech Stack

- Python / Flask
- PyMySQL (MySQL on PythonAnywhere)
- NLTK (chatbot)
- Safaricom M-Pesa API (sandbox)
- Gunicorn (WSGI)

## Deploy

Deployed on PythonAnywhere. Push to `main` triggers auto-reload via PythonAnywhere's git sync.

## Routes

| Method | Route                  | Description              |
|--------|------------------------|--------------------------|
| POST   | `/api/signup`          | Create account           |
| POST   | `/api/signin`          | Login                    |
| POST   | `/api/add_product`     | Add product (multipart)  |
| GET    | `/api/get_product_details` | List all products    |
| POST   | `/api/chat`            | Chatbot (JSON body)      |
| POST   | `/api/mpesa_payment`   | Trigger STK Push         |
