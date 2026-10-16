from flask import *
app = Flask(__name__)
from flask_cors import CORS

CORS(app)

import pymysql
import pymysql.cursors
import os
import hmac
from werkzeug.security import check_password_hash, generate_password_hash

app_root = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app_root, 'static', 'images')


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
        if not valid and stored_password and hmac.compare_digest(stored_password, password):
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
def add_product():
    try:
        product_name = request.form['product_name']
        product_description = request.form['product_description']
        product_cost = request.form['product_cost']
        photo = request.files['product_photo']
        filename = photo.filename
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(photo_path)

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

    except Exception as e:
        print("Error adding product:", str(e))
        return jsonify({"error": "Failed to add product"}), 500


# --- DELETE PRODUCT ---
@app.route('/api/delete_product', methods=['POST'])
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

            # Remove the image file if it exists
            if product and product['product_photo']:
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], product['product_photo'])
                if os.path.exists(photo_path):
                    os.remove(photo_path)
        finally:
            connection.close()

        return jsonify({"success": "Product deleted successfully"})

    except Exception as e:
        print("Error deleting product:", str(e))
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
    (r"(.*)contact", ["This demo does not have a verified support contact."]),
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
    except Exception as e:
        print(f"Error in /chat route: {str(e)}")
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
        if phone_clean.startswith('0'):
            phone_clean = '254' + phone_clean[1:]
        elif phone_clean.startswith('+254'):
            phone_clean = phone_clean[1:]
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

        api_base = os.environ.get('MPESA_API_BASE', 'https://sandbox.safaricom.co.ke').rstrip('/')
        api_url = f"{api_base}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(consumer_key, consumer_secret),
            timeout=15,
        )
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
        print("M-Pesa Response:", response.text)

        result = response.json()

        if response.status_code == 200 and result.get("ResponseCode") == "0":
            return jsonify({
                "message": "M-Pesa prompt sent to your phone. Enter your PIN to complete payment.",
                "CheckoutRequestID": result.get("CheckoutRequestID", "")
            })
        else:
            error_msg = result.get("errorMessage", result.get("responseDescription", "M-Pesa service unavailable"))
            return jsonify({"message": f"Payment failed: {error_msg}"}), 500

    except Exception as e:
        print("M-Pesa Error:", str(e))
        return jsonify({"message": "Payment service error. Please try again later."}), 500


@app.route('/api/mpesa_callback', methods=['POST'])
def mpesa_callback():
    """M-Pesa will POST the transaction result here."""
    data = request.get_json()
    print("M-Pesa Callback:", data)
    return jsonify({"ResultCode": 0, "ResultDesc": "Success"})
