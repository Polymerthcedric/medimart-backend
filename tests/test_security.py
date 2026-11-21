"""Offline security checks for the Medimart prototype.

No network calls and no real database: DB access is stubbed and the upload
folder is redirected to a pytest temp directory.
"""

import io

import pytest

import app as app_module


PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
ADMIN_HEADER = 'X-Admin-Token'
VALID_CALLBACK = {
    'Body': {
        'stkCallback': {
            'MerchantRequestID': 'demo-merchant-id',
            'CheckoutRequestID': 'demo-checkout-id',
            'ResultCode': 0,
            'ResultDesc': 'The service request is processed successfully.',
        }
    }
}


class FakeCursor:
    def execute(self, *args, **kwargs):
        return None

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def close(self):
        return None


class FakeConnection:
    def cursor(self, *args, **kwargs):
        return FakeCursor()

    def commit(self):
        return None

    def close(self):
        return None


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setitem(app_module.app.config, 'UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setattr(app_module, 'database_connection', lambda: FakeConnection())
    return app_module.app.test_client()


@pytest.fixture
def admin_token(monkeypatch):
    token = 'test-admin-token'
    monkeypatch.setenv('ADMIN_API_TOKEN', token)
    return token


def product_data(filename='photo.png', content=PNG_BYTES):
    return {
        'product_name': 'Demo item',
        'product_description': 'Demo description',
        'product_cost': '10',
        'product_photo': (io.BytesIO(content), filename),
    }


def admin_headers(token):
    return {ADMIN_HEADER: token}


# --- Admin gate ---------------------------------------------------------


@pytest.mark.parametrize('path', ['/api/add_product', '/api/delete_product'])
def test_admin_endpoints_return_503_when_token_unset(client, monkeypatch, path):
    monkeypatch.delenv('ADMIN_API_TOKEN', raising=False)
    response = client.post(path, data=product_data())
    assert response.status_code == 503
    assert b'disabled' in response.data.lower()


@pytest.mark.parametrize('path', ['/api/add_product', '/api/delete_product'])
def test_admin_endpoints_return_401_for_wrong_token(client, admin_token, path):
    response = client.post(
        path, data=product_data(), headers=admin_headers('wrong-token')
    )
    assert response.status_code == 401


def test_admin_endpoints_return_200_for_correct_token(client, admin_token, tmp_path):
    added = client.post(
        '/api/add_product',
        data=product_data(),
        headers=admin_headers(admin_token),
    )
    assert added.status_code == 200

    saved = list(tmp_path.iterdir())
    assert len(saved) == 1
    assert saved[0].suffix == '.png'
    assert saved[0].name != 'photo.png'

    deleted = client.post(
        '/api/delete_product',
        data={'product_id': '1'},
        headers=admin_headers(admin_token),
    )
    assert deleted.status_code == 200


# --- M-Pesa callback ----------------------------------------------------


def test_callback_returns_503_when_secret_unset(client, monkeypatch):
    monkeypatch.delenv('CALLBACK_SECRET', raising=False)
    response = client.post(
        '/api/mpesa_callback?secret=anything', json=VALID_CALLBACK
    )
    assert response.status_code == 503


def test_callback_returns_403_for_wrong_secret(client, monkeypatch):
    monkeypatch.setenv('CALLBACK_SECRET', 'demo-callback-secret')
    response = client.post(
        '/api/mpesa_callback?secret=wrong', json=VALID_CALLBACK
    )
    assert response.status_code == 403


def test_callback_returns_200_for_valid_shaped_callback(client, monkeypatch):
    monkeypatch.setenv('CALLBACK_SECRET', 'demo-callback-secret')
    response = client.post(
        '/api/mpesa_callback?secret=demo-callback-secret', json=VALID_CALLBACK
    )
    assert response.status_code == 200
    assert response.get_json()['ResultCode'] == 0


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'Body': None},
        {'Body': {'stkCallback': {'ResultCode': 0}}},
        {'Body': {'stkCallback': dict(VALID_CALLBACK['Body']['stkCallback'], ResultDesc=None)}},
        'not-a-dict',
    ],
)
def test_callback_returns_400_for_invalid_shape(client, monkeypatch, payload):
    monkeypatch.setenv('CALLBACK_SECRET', 'demo-callback-secret')
    response = client.post(
        '/api/mpesa_callback?secret=demo-callback-secret', json=payload
    )
    assert response.status_code == 400
    assert response.get_json()['ResultCode'] != 0


# --- Uploads ------------------------------------------------------------


def test_upload_rejects_executable_extension(client, admin_token, tmp_path):
    response = client.post(
        '/api/add_product',
        data=product_data(filename='malware.exe'),
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_empty_filename(client, admin_token, tmp_path):
    response = client.post(
        '/api/add_product',
        data=product_data(filename=''),
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_oversized_filename(client, admin_token, tmp_path):
    response = client.post(
        '/api/add_product',
        data=product_data(filename='a' * 300 + '.png'),
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_oversized_request(client, admin_token, monkeypatch, tmp_path):
    monkeypatch.setitem(app_module.app.config, 'MAX_CONTENT_LENGTH', 256)
    response = client.post(
        '/api/add_product',
        data=product_data(content=b'x' * 1024),
        headers=admin_headers(admin_token),
    )
    assert response.status_code == 413
    assert list(tmp_path.iterdir()) == []


# --- CORS ---------------------------------------------------------------


def test_cors_does_not_reflect_arbitrary_origin(client):
    response = client.get(
        '/api/get_product_details', headers={'Origin': 'https://evil.example'}
    )
    allowed = response.headers.get('Access-Control-Allow-Origin')
    assert allowed != 'https://evil.example'
    assert allowed is None
