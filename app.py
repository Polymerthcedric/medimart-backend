from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
import pymysql.cursors
import os
import requests
import datetime
import base64
from requests.auth import HTTPBasicAuth
from nltk.chat.util import Chat, reflections

app = Flask(__name__)
CORS(app)

app_root = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(app_root, 'static', 'images')

DB_CONFIG = {
    'host': 'polymerthcedric.mysql.pythonanywhere-services.com',
    'user': 'polymerthcedric',
    'password': 'modcom1234',
    'database': 'polymerthcedric$default',
}

MPESA_CONFIG = {
    'consumer_key': 'LF3erGEWGB70cuC7tL3yT0wna2NvmTcJkECyoT0LzVZemGqP',
    'consumer_secret': '5pgWE0kLX3tbJmeOePh7Ay09dIi7fzOG47RotXOhWabzgCB2UhBgaihY1ZG7wLt2',
    'passkey': 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919',
    'short_code': '174379',
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


# ─── Auth Routes ────────────────────────────────────────────────

@app.route('/api/signup', methods=['POST'])
def signup():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    phone = request.form['phone']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (username, email, password, phone) VALUES (%s, %s, %s, %s)',
        (username, email, password, phone),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': 'Thank you for signing up'})


@app.route('/api/signin', methods=['POST'])
def signin():
    email = request.form['email']
    password = request.form['password']

    conn = get_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))

    if cursor.rowcount == 0:
        return jsonify({'message': 'Login failed'})
    user = cursor.fetchone()
    conn.close()
    return jsonify({'message': 'Login successful', 'user': user})


# ─── Product Routes ─────────────────────────────────────────────

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

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO product_details (product_name, product_description, product_cost, product_photo) VALUES (%s, %s, %s, %s)',
            (product_name, product_description, product_cost, filename),
        )
        conn.commit()
        conn.close()
        return jsonify({'success': 'Product added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get_product_details', methods=['GET'])
def get_product_details():
    conn = get_db()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT * FROM product_details')
    products = cursor.fetchall()
    conn.close()
    return jsonify(products)


# ─── Chatbot ────────────────────────────────────────────────────

pairs = [
    (r'hi|hello|hey', ['Hello! Welcome to Medimart. How can I help you today?']),
    (r'how are you', ["I'm great and ready to assist you with your health needs!"]),
    (r'(.*)your name(.*)', ['I\u2019m Medimart Assistant \u2014 here to help you shop smarter and stay healthy.']),
    (r'(.*)medicine(.*)available', ['We have a wide range of medicines in stock. You can search by category or name.']),
    (r'(.*)buy medicine(.*)', ['Yes, you can purchase medicines online or at our physical location.']),
    (r'(.*)availability of (.*)', [r'Yes, we do stock \2. You can search for it on our homepage.']),
    (r'(.*)price of (.*)', [r'The price of \2 may vary depending on the brand. Please search it in our store.']),
    (r'(.*)store hours', ['We are open from 9 AM to 9 PM, Monday to Saturday. Closed on Sundays.']),
    (r'(.*)location', ['Medimart is located at 123 Main Street, near City Hospital.']),
    (r'(.*)home delivery', ['Yes! We offer home delivery within the city limits.']),
    (r'(.*)delivery charges', ['Delivery is free for orders above \u20b9500. Otherwise, a flat \u20b950 fee applies.']),
    (r'(.*)track order', ['Please provide your order ID to track your delivery.']),
    (r'(.*)cancel order', ['You can cancel your order by contacting our support line.']),
    (r'(.*)upload prescription', ['You can upload your prescription on our website or send it via WhatsApp.']),
    (r'(.*)accept digital prescription', ['Yes, we accept both digital and paper prescriptions.']),
    (r'(.*)consult doctor', ['We can connect you to a doctor online for medical advice.']),
    (r'(.*)test(.*)', ['We partner with labs for common health tests. Booking is available.']),
    (r'(.*)covid(.*)', ['We have COVID essentials like masks, sanitizers, and thermometers available.']),
    (r'(.*)mask(.*)', ['Yes, we stock surgical masks, N95 masks, and reusable cloth masks.']),
    (r'(.*)sanitizer(.*)', ['We carry hand sanitizers in various sizes and brands.']),
    (r'(.*)fever(.*)', ['We offer Paracetamol, Crocin, and other fever-relief medications.']),
    (r'(.*)pain relief(.*)', ['We have tablets, ointments, and sprays for pain relief.']),
    (r'(.*)allergy(.*)', ['We stock antihistamines and allergy relief medications.']),
    (r'(.*)diabetes(.*)', ['We have diabetes medicines, sugar testing strips, and glucometers.']),
    (r'(.*)blood pressure(.*)', ['We stock BP monitors and medicines like Amlodipine, Telmisartan, etc.']),
    (r'(.*)baby product(.*)', ['We offer diapers, baby lotion, baby formula, wipes, and more.']),
    (r'(.*)vitamin(.*)', ['We stock Vitamin C, D, B12, multivitamins, and immunity boosters.']),
    (r'(.*)skin care(.*)', ['We have face washes, moisturizers, sunscreens, and medicated creams.']),
    (r'(.*)hair(.*)', ['We carry hair oils, anti-dandruff shampoos, and hair fall control products.']),
    (r'(.*)women health(.*)', ['We have sanitary products, PCOS supplements, and prenatal vitamins.']),
    (r'(.*)men health(.*)', ["We offer men's grooming, supplements, and fitness products."]),
    (r'(.*)return medicine(.*)', ['Returns are accepted within 7 days if unopened and with the bill.']),
    (r'(.*)expired(.*)', ['Please avoid using expired medicine. We can help dispose of it safely.']),
    (r'(.*)payment methods', ['You can pay via cash, UPI, cards, and mobile wallets.']),
    (r'(.*)discount(.*)', ['We offer up to 15% discount on select medicines.']),
    (r'(.*)generic medicine(.*)', ['Yes, we provide approved and affordable generic alternatives.']),
    (r'(.*)best seller(.*)', ['Top sellers include Paracetamol, Dettol, Dabur Chyawanprash, and glucometers.']),
    (r'(.*)contact', ['Call us at +254 100363487 or chat with us via WhatsApp.']),
    (r'(.*)customer care(.*)', ["You can reach our customer care through the 'Contact Us' page or call us directly."]),
    (r'(.*)', ["I'm not sure about that. Could you ask something related to our store, products, or services?"]),
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
        return jsonify({'response': response or "I'm not sure how to respond to that."})
    except Exception as e:
        return jsonify({'response': 'Server error occurred.'}), 500


# ─── M-Pesa Payment ─────────────────────────────────────────────

@app.route('/api/mpesa_payment', methods=['POST'])
def mpesa_payment():
    amount = request.form['amount']
    phone = request.form['phone']

    api_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    resp = requests.get(api_url, auth=HTTPBasicAuth(MPESA_CONFIG['consumer_key'], MPESA_CONFIG['consumer_secret']))
    access_token = 'Bearer ' + resp.json()['access_token']

    timestamp = datetime.datetime.today().strftime('%Y%m%d%H%M%S')
    data_str = MPESA_CONFIG['short_code'] + MPESA_CONFIG['passkey'] + timestamp
    password = base64.b64encode(data_str.encode()).decode()

    payload = {
        'BusinessShortCode': MPESA_CONFIG['short_code'],
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': '1',
        'PartyA': phone,
        'PartyB': MPESA_CONFIG['short_code'],
        'PhoneNumber': phone,
        'CallBackURL': 'https://coding.co.ke/api/confirm.php',
        'AccountReference': 'Medimart',
        'TransactionDesc': 'Payments for Products',
    }

    headers = {'Authorization': access_token, 'Content-Type': 'application/json'}
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    requests.post(url, json=payload, headers=headers)

    return jsonify({'message': 'An MPESA Prompt has been sent to your phone. Please check and complete payment.'})
