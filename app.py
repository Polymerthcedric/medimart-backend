from flask import *
app = Flask(__name__)
from flask_cors import CORS

# NOTE: This is a demo/educational project. All credentials below are
# sandbox/placeholder values and are NOT intended for production use.
# In production, use environment variables (os.environ.get()) for secrets.

CORS(app)

import pymysql
import pymysql.cursors
import os

app_root = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app_root, 'static', 'images')


@app.route('/api/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    phone = request.form['phone']

    # DEMO credentials — sandbox/placeholder values, not for production
    connection = pymysql.connect(
        host='polymerthcedric.mysql.pythonanywhere-services.com',
        user='polymerthcedric',
        password='modcom1234',
        database='polymerthcedric$default'
    )
    try:
        cursor = connection.cursor()
        sql = 'insert into users(username,email,password,phone) values (%s,%s,%s,%s)'
        data = (username, email, password, phone)
        cursor.execute(sql, data)
        connection.commit()
    finally:
        connection.close()
    return jsonify({"success": "Thank you for signing up"})


@app.route('/api/signin', methods=['POST'])
def signin():
    email = request.form['email']
    password = request.form['password']

    # DEMO credentials — sandbox/placeholder values, not for production
    connection = pymysql.connect(
        host='polymerthcedric.mysql.pythonanywhere-services.com',
        user='polymerthcedric',
        password='modcom1234',
        database='polymerthcedric$default'
    )
    try:
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        sql = 'select * from users where email = %s and password = %s'
        data = (email, password)
        cursor.execute(sql, data)
        count = cursor.rowcount
        if count == 0:
            return jsonify({"message": "Login failed"})
        else:
            user = cursor.fetchone()
            return jsonify({"message": "Login successful", "user": user})
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

        # DEMO credentials — sandbox/placeholder values, not for production
        connection = pymysql.connect(
            host='polymerthcedric.mysql.pythonanywhere-services.com',
            user='polymerthcedric',
            password='modcom1234',
            database='polymerthcedric$default'
        )
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

        # DEMO credentials — sandbox/placeholder values, not for production
        connection = pymysql.connect(
            host='polymerthcedric.mysql.pythonanywhere-services.com',
            user='polymerthcedric',
            password='modcom1234',
            database='polymerthcedric$default'
        )
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
    # DEMO credentials — sandbox/placeholder values, not for production
    connection = pymysql.connect(
        host='polymerthcedric.mysql.pythonanywhere-services.com',
        user='polymerthcedric',
        password='modcom1234',
        database='polymerthcedric$default'
    )
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
    (r"hi|hello|hey", ["Hello! Welcome to Medimart. How can I help you today?"]),
    (r"how are you", ["I'm great and ready to assist you with your health needs!"]),
    (r"(.*)your name(.*)", ["I'm Medimart Assistant — here to help you shop smarter and stay healthy."]),
    (r"(.*)medicine(.*)available", ["We have a wide range of medicines in stock. You can search by category or name."]),
    (r"(.*)buy medicine(.*)", ["Yes, you can purchase medicines online or at our physical location."]),
    (r"(.*)availability of (.*)", [r"Yes, we do stock \2. You can search for it on our homepage."]),
    (r"(.*)price of (.*)", [r"The price of \2 may vary depending on the brand. Please search it in our store."]),
    (r"(.*)store hours", ["We are open from 9 AM to 9 PM, Monday to Saturday. Closed on Sundays."]),
    (r"(.*)location", ["Medimart is located at 123 Main Street, near City Hospital."]),
    (r"(.*)home delivery", ["Yes! We offer home delivery within the city limits."]),
    (r"(.*)delivery charges", ["Delivery is free for orders above KES 500. Otherwise, a flat KES 50 fee applies."]),
    (r"(.*)track order", ["Please provide your order ID to track your delivery."]),
    (r"(.*)cancel order", ["You can cancel your order by contacting our support line."]),
    (r"(.*)upload prescription", ["You can upload your prescription on our website or send it via WhatsApp."]),
    (r"(.*)payment methods", ["We accept M-Pesa, cash, and credit cards."]),
    (r"(.*)contact", ["Call us at +254116497339 or chat with us via WhatsApp."]),
    (r"(.*)", ["I'm not sure about that. Could you ask something related to our store, products, or services?"])
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

        # DEMO credentials — Safaricom sandbox values, not for production
        consumer_key = "LF3erGEWGB70cuC7tL3yT0wna2NvmTcJkECyoT0LzVZemGqP"
        consumer_secret = "5pgWE0kLX3tbJmeOePh7Ay09dIi7fzOG47RotXOhWabzgCB2UhBgaihY1ZG7wLt2"

        api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        data = response.json()
        access_token = "Bearer" + ' ' + data['access_token']

        timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
        passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
        business_short_code = "174379"
        data_str = business_short_code + passkey + timestamp
        encoded = base64.b64encode(data_str.encode())
        password = encoded.decode()

        payload = {
            "BusinessShortCode": "174379",
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": str(amount),
            "PartyA": phone_clean,
            "PartyB": "174379",
            "PhoneNumber": phone_clean,
            "CallBackURL": "https://polymerthcedric.pythonanywhere.com/api/mpesa_callback",
            "AccountReference": "Medimart",
            "TransactionDesc": "Payment for Medical Products"
        }

        headers = {
            "Authorization": access_token,
            "Content-Type": "application/json"
        }

        url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        response = requests.post(url, json=payload, headers=headers)
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
