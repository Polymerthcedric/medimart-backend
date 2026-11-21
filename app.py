import os
import hmac
import uuid
from functools import wraps

from flask import *
from flask_cors import CORS
import pymysql
import pymysql.cursors
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Demo project. Runtime database and payment credentials must be supplied
# through environment variables; never commit them to source files.

app = Flask(__name__)

# Only explicitly allowed origins may call the API from a browser. The default
# is local development only; deployment must opt in via ALLOWED_ORIGINS.
DEFAULT_ALLOWED_ORIGINS = 'http://localhost,http://127.0.0.1'
allowed_origins = [
    origin.strip()
    for origin in os.environ.get('ALLOWED_ORIGINS', DEFAULT_ALLOWED_ORIGINS).split(',')
    if origin.strip()
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

app_root = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app_root, 'static', 'images')
# Cap request bodies so an anonymous caller cannot exhaust memory or disk.
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MiB
# create the upload directory on startup so /api/add_product does not fail
# with FileNotFoundError when the repo is cloned fresh (static/ is not tracked).
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_UPLOAD_FILENAME_LENGTH = 255
ADMIN_TOKEN_HEADER = 'X-Admin-Token'


def database_connection():
    names = ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME')
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing database configuration: {', '.join(missing)}")
    return pymysql.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.environ['DB_NAME'],
        port=int(os.environ.get('DB_PORT', '3306')),
    )


def _admin_auth_error():
    """Return an error response when an admin request must be rejected."""
    configured_token = os.environ.get('ADMIN_API_TOKEN')
    if not configured_token:
        return jsonify({"error": "Admin endpoints are disabled (ADMIN_API_TOKEN not configured)"}), 503
    presented_token = request.headers.get(ADMIN_TOKEN_HEADER, '')
    # Compare bytes with a constant-time helper; avoid type errors on non-ASCII.
    if not hmac.compare_digest(
        presented_token.encode('utf-8'), configured_token.encode('utf-8')
    ):
        return jsonify({"error": "Unauthorized"}), 401
    return None


def admin_required(view):
    """Optional, token-based gate for the two catalog-changing routes."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        error = _admin_auth_error()
        if error is not None:
            return error
        return view(*args, **kwargs)
    return wrapped


def _store_upload(photo):
    """Save one validated image; return (filename, error_response)."""
    original_name = secure_filename(photo.filename or '')
    if not original_name or len(original_name) > MAX_UPLOAD_FILENAME_LENGTH:
        return None, (jsonify({"error": "Invalid or missing product_photo"}), 400)

    extension = os.path.splitext(original_name)[1].lower().lstrip('.')
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return None, (jsonify({"error": "Unsupported image file type"}), 400)

    # uuid4 + exclusive creation: names are unpredictable and never overwrite
    # an existing file, even if two uploads race.
    for _ in range(5):
        filename = f"{uuid.uuid4().hex}.{extension}"
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            with open(photo_path, 'xb') as destination:
                photo.save(destination)
            return filename, None
        except FileExistsError:
            continue
    return None, (jsonify({"error": "Could not store product_photo"}), 500)


@app.route('/api/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password_hash = generate_password_hash(request.form['password'], method="pbkdf2:sha256")
    phone = request.form['phone']

    connection = database_connection()
    try:
        cursor = connection.cursor()
        sql = 'insert into users(username,email,password,phone) values (%s,%s,%s,%s)'
        data = (username, email, password_hash, phone)
        cursor.execute(sql, data)
        connection.commit()
    finally:
        connection.close()
    return jsonify({"success": "Thank you for signing up"})


@app.route('/api/signin', methods=['POST'])
def signin():
    email = request.form['email']
    password = request.form['password']

    connection = database_connection()
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('select * from users where email = %s', (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"message": "Login failed"})

        stored_password = user.get('password', '')
        valid = False
        try:
            valid = check_password_hash(stored_password, password)
        except (ValueError, TypeError):
            pass

        # Upgrade old plaintext records after a successful login, then never
        # return password material to the client.
        if not valid and stored_password and hmac.compare_digest(
            stored_password.encode('utf-8'), password.encode('utf-8')
        ):
            valid = True
            cursor.execute(
                'update users set password = %s where email = %s',
                (generate_password_hash(password, method="pbkdf2:sha256"), email),
            )
            connection.commit()

        if not valid:
            return jsonify({"message": "Login failed"})

        safe_user = {
            key: value
            for key, value in user.items()
            if key not in ('password', 'password_hash')
        }
        return jsonify({"message": "Login successful", "user": safe_user})
    finally:
        connection.close()


@app.route('/api/add_product', methods=['POST'])
@admin_required
def add_product():
    try:
        product_name = request.form['product_name']
        product_description = request.form['product_description']
        product_cost = request.form['product_cost']
        photo = request.files.get('product_photo')
        if photo is None:
            return jsonify({"error": "Invalid or missing product_photo"}), 400
        filename, error = _store_upload(photo)
        if error is not None:
            return error

        connection = database_connection()
        try:
            cursor = connection.cursor()
            sql = '''
                INSERT INTO product_details (product_name, product_description, product_cost, product_photo)
                VALUES (%s, %s, %s, %s)
            '''
            data = (product_name, product_description, product_cost, filename)
            cursor.execute(sql, data)
            connection.commit()
        finally:
            connection.close()
        return jsonify({"success": "Product details added successfully"})

    except HTTPException:
        # Let Flask handle 413 (MAX_CONTENT_LENGTH) and other HTTP errors.
        raise
    except Exception:
        app.logger.warning("add_product failed")
        return jsonify({"error": "Failed to add product"}), 500


# --- DELETE PRODUCT ---
@app.route('/api/delete_product', methods=['POST'])
@admin_required
def delete_product():
    try:
        product_id = request.form['product_id']

        connection = database_connection()
        try:
            cursor = connection.cursor(pymysql.cursors.DictCursor)

            # Fetch the product photo so we can delete the file too
            cursor.execute('select product_photo from product_details where product_id = %s', (product_id,))
            product = cursor.fetchone()

            sql = 'delete from product_details where product_id = %s'
            cursor.execute(sql, (product_id,))
            connection.commit()

            # Only ever remove a plain filename inside the upload directory.
            if product and product.get('product_photo'):
                stored_name = secure_filename(product['product_photo'])
                if stored_name:
                    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
                    if os.path.isfile(photo_path):
                        os.remove(photo_path)
        finally:
            connection.close()

        return jsonify({"success": "Product deleted successfully"})

    except HTTPException:
        raise
    except Exception:
        app.logger.warning("delete_product failed")
        return jsonify({"error": "Failed to delete product"}), 500


@app.route('/api/get_product_details', methods=['GET'])
def get_product_details():
    connection = database_connection()
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        sql = "select * from product_details"
        cursor.execute(sql)
        product_details = cursor.fetchall()
    finally:
        connection.close()
    return jsonify(product_details)


# Chatbot
from nltk.chat.util import Chat, reflections

pairs = [
    (r"hi|hello|hey", ["Hi! I can answer a few demo questions about the store. What would you like to know?"]),
    (r"how are you", ["I'm a scripted helper for this storefront demo. I can point you to the product list or payment example."]),
    (r"(.*)your name(.*)", ["I'm the Medimart store helper. I use scripted responses, not AI."]),
    (r"(.*)medicine(.*)available", ["Check the product list for the items shown in this demo. It may not reflect real stock."]),
    (r"(.*)buy medicine(.*)", ["This demo shows a checkout flow. It is not a live pharmacy and does not accept real orders."]),
    (r"(.*)availability of (.*)", ["I can't confirm real stock. Check the product list in this demo."]),
    (r"(.*)price of (.*)", ["The product list shows sample prices for this demo. Please confirm prices with a real supplier."]),
    (r"(.*)store hours", ["This demo does not have verified store hours."]),
    (r"(.*)location", ["This demo does not have a verified store location."]),
    (r"(.*)home delivery", ["Delivery options are not configured in this demo."]),
    (r"(.*)delivery charges", ["Delivery charges are not configured in this demo."]),
    (r"(.*)track order", ["Order tracking is not available in this demo."]),
    (r"(.*)cancel order", ["Order cancellation is not available in this demo."]),
    (r"(.*)upload prescription", ["Prescription upload is not available in this demo."]),
    (r"(.*)payment methods", ["The checkout example uses Safaricom's M-Pesa sandbox. It does not take real payments."]),
    (r"(.*)contact", ["Contact details shown in this demo are illustrative only; there is no support team behind it."]),
    (r"(.*)", ["I don't have an answer for that. Try asking about the product list or demo checkout."])
]

chatbot = Chat(pairs, reflections)


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message')
        if not user_input:
            return jsonify({'response': 'No message received'}), 400
        response = chatbot.respond(user_input)
        if not response:
            response = "I'm not sure how to respond to that."
        return jsonify({'response': response})
    except HTTPException:
        raise
    except Exception:
        app.logger.warning("chat request failed")
        return jsonify({'response': 'Server error occurred.'}), 500


# M-Pesa Payment
import requests
import datetime
import base64
from requests.auth import HTTPBasicAuth


@app.route('/api/mpesa_payment', methods=['POST'])
def mpesa_payment():
    try:
        amount = request.form['amount']
        phone = request.form['phone']

        # Clean phone number: remove any non-digit characters
        phone_clean = ''.join(filter(str.isdigit, phone))

        # Convert to SafariCom format: 254XXXXXXXXX
        # Phone numbers are digit-filtered above, so '+254' can never appear
        # here. Normalise local 07... numbers and already-prefixed 254... ones.
        if phone_clean.startswith('0'):
            phone_clean = '254' + phone_clean[1:]
        elif not phone_clean.startswith('254'):
            phone_clean = '254' + phone_clean

        # Ensure we have exactly 12 digits (254 + 9 digits)
        if len(phone_clean) != 12:
            return jsonify({"message": "Invalid phone number. Please enter a valid Safaricom number."}), 400

        consumer_key = os.environ.get('MPESA_CONSUMER_KEY')
        consumer_secret = os.environ.get('MPESA_CONSUMER_SECRET')
        passkey = os.environ.get('MPESA_PASSKEY')
        business_short_code = os.environ.get('MPESA_SHORT_CODE', '174379')
        callback_url = os.environ.get('MPESA_CALLBACK_URL')
        if not all((consumer_key, consumer_secret, passkey, callback_url)):
            return jsonify({"message": "M-Pesa sandbox is not configured."}), 503

        sandbox_api_base = 'https://sandbox.safaricom.co.ke'
        api_base = os.environ.get('MPESA_API_BASE', sandbox_api_base).rstrip('/')
        if api_base != sandbox_api_base:
            return jsonify({"message": "This prototype supports the Safaricom sandbox only."}), 503

        api_url = f"{api_base}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=15,
        )
        app.logger.info("M-Pesa OAuth completed (status=%s)", response.status_code)
        data = response.json()
        access_token = "Bearer" + ' ' + data['access_token']

        timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        data_str = business_short_code + passkey + timestamp
        encoded = base64.b64encode(data_str.encode())
        password = encoded.decode()

        payload = {
            "BusinessShortCode": business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(amount),
            "PartyA": phone_clean,
            "PartyB": business_short_code,
            "PhoneNumber": phone_clean,
            "CallBackURL": callback_url,
            "AccountReference": "Medimart",
            "TransactionDesc": "Payment for Medical Products"
        }

        headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }

        url = f"{api_base}/mpesa/stkpush/v1/processrequest"
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        # Never log provider bodies: they can contain tokens and phone numbers.
        app.logger.info("M-Pesa STK push completed (status=%s)", response.status_code)

        result = response.json()

        if response.status_code == 200 and result.get("ResponseCode") == "0":
            return jsonify({
                "message": "M-Pesa prompt sent to your phone. Enter your PIN to complete payment.",
                "CheckoutRequestID": result.get("CheckoutRequestID", "")
            })
        else:
            error_msg = result.get("errorMessage", result.get("responseDescription", "M-Pesa service unavailable"))
            return jsonify({"message": f"Payment failed: {error_msg}"}), 500

    except HTTPException:
        raise
    except Exception:
        app.logger.warning("M-Pesa payment request failed")
        return jsonify({"message": "Payment service error. Please try again later."}), 500


def _valid_callback_payload(payload):
    """Check the STK Push callback shape without trusting any of its values."""
    if not isinstance(payload, dict):
        return False
    body = payload.get('Body')
    if not isinstance(body, dict):
        return False
    callback = body.get('stkCallback')
    if not isinstance(callback, dict):
        return False

    result_code = callback.get('ResultCode')
    if isinstance(result_code, bool):
        return False
    if isinstance(result_code, str):
        if not result_code.strip().lstrip('-').isdigit():
            return False
    elif not isinstance(result_code, int):
        return False

    for field in ('MerchantRequestID', 'CheckoutRequestID', 'ResultDesc'):
        value = callback.get(field)
        if not isinstance(value, str) or not value:
            return False
    return True


@app.route('/api/mpesa_callback', methods=['POST'])
def mpesa_callback():
    """Receive an M-Pesa sandbox result bearing our own shared secret."""
    configured_secret = os.environ.get('CALLBACK_SECRET')
    if not configured_secret:
        return jsonify({"ResultCode": 1, "ResultDesc": "Callback verification is not configured"}), 503

    presented_secret = request.args.get('secret', '')
    if not hmac.compare_digest(
        presented_secret.encode('utf-8'), configured_secret.encode('utf-8')
    ):
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid callback secret"}), 403

    payload = request.get_json(silent=True)
    if not _valid_callback_payload(payload):
        return jsonify({"ResultCode": 1, "ResultDesc": "Invalid callback payload"}), 400

    app.logger.info(
        "M-Pesa callback accepted (result=%s)", payload['Body']['stkCallback']['ResultCode']
    )
    return jsonify({"ResultCode": 0, "ResultDesc": "Success"})
