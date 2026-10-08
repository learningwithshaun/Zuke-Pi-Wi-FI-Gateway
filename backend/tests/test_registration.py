import json
from backend.database.db import get_db
from backend.services.gateway_service import get_gateway_service


def test_valid_registration(client, app, gateway):
    payload = {
        "name": "Amanda",
        "email": "amanda@example.com",
        "marketing_consent": True
    }
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json',
        environ_base={'REMOTE_ADDR': '192.168.50.45'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["message"] == "Internet access granted"
    assert "session" in data
    assert data["session"]["ip_address"] == "192.168.50.45"
    assert data["session"]["authenticated"] is True
    assert "token" in data["session"]

    # Verify database persistence
    with app.app_context():
        db = get_db()
        customer = db.execute("SELECT * FROM customers WHERE email = ?", ("amanda@example.com",)).fetchone()
        assert customer is not None
        assert customer["name"] == "Amanda"
        assert customer["marketing_consent"] == 1

        session = db.execute("SELECT * FROM access_sessions WHERE ip_address = ?", ("192.168.50.45",)).fetchone()
        assert session is not None
        assert session["authenticated"] == 1

        # Verify gateway authorization
        gw = get_gateway_service()
        assert gw.is_authorized("192.168.50.45") is True


def test_missing_name(client):
    payload = {"email": "amanda@example.com"}
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "Please enter your name."


def test_empty_whitespace_name(client):
    payload = {"name": "   ", "email": "amanda@example.com"}
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "Please enter your name."


def test_missing_email(client):
    payload = {"name": "Amanda"}
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "Please enter your email address."


def test_invalid_email_format(client):
    payload = {"name": "Amanda", "email": "hello"}
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "Please enter a valid email address."


def test_invalid_email_missing_domain(client):
    payload = {"name": "Amanda", "email": "amanda@"}
    response = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert data["error"] == "Please enter a valid email address."


def test_duplicate_email_returning_customer(client, app):
    payload1 = {"name": "Amanda", "email": "amanda@example.com"}
    res1 = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload1),
        content_type='application/json',
        environ_base={'REMOTE_ADDR': '192.168.50.10'}
    )
    assert res1.status_code == 200

    # Returning customer with updated name or second device IP
    payload2 = {"name": "Amanda Smith", "email": "amanda@example.com"}
    res2 = client.post(
        '/api/captive-portal/register',
        data=json.dumps(payload2),
        content_type='application/json',
        environ_base={'REMOTE_ADDR': '192.168.50.20'}
    )
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["success"] is True

    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(*) as c FROM customers WHERE email = ?", ("amanda@example.com",)).fetchone()["c"]
        assert count == 1  # No duplicate row created

        customer = db.execute("SELECT name FROM customers WHERE email = ?", ("amanda@example.com",)).fetchone()
        assert customer["name"] == "Amanda Smith"


def test_malformed_json_request(client):
    response = client.post(
        '/api/captive-portal/register',
        data="not json",
        content_type='application/json'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
