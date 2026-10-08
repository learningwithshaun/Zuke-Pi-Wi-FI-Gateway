import json
import time
from backend.services.gateway_service import get_gateway_service


def test_status_unauthorized_device(client):
    response = client.get(
        '/api/captive-portal/status',
        environ_base={'REMOTE_ADDR': '192.168.50.99'}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["authenticated"] is False
    assert data["ip_address"] == "192.168.50.99"


def test_status_authorized_device(client, gateway):
    client_ip = "192.168.50.77"
    # Register device
    reg_response = client.post(
        '/api/captive-portal/register',
        data=json.dumps({"name": "Test User", "email": "test@example.com"}),
        content_type='application/json',
        environ_base={'REMOTE_ADDR': client_ip}
    )
    assert reg_response.status_code == 200

    # Query status
    status_response = client.get(
        '/api/captive-portal/status',
        environ_base={'REMOTE_ADDR': client_ip}
    )
    assert status_response.status_code == 200
    status_data = status_response.get_json()
    assert status_data["authenticated"] is True
    assert status_data["ip_address"] == client_ip
    assert "expires_at" in status_data


def test_mock_gateway_expiration(gateway):
    ip = "192.168.50.88"
    # Authorize for 1 second
    gateway.authorize_device(ip, duration_seconds=1)
    assert gateway.is_authorized(ip) is True

    # Sleep 1.1 seconds
    time.sleep(1.1)
    assert gateway.is_authorized(ip) is False


def test_mock_gateway_revocation(gateway):
    ip = "192.168.50.89"
    gateway.authorize_device(ip, duration_seconds=3600)
    assert gateway.is_authorized(ip) is True

    revoked = gateway.revoke_device(ip)
    assert revoked is True
    assert gateway.is_authorized(ip) is False


def test_captive_detection_when_unauthenticated(client):
    ip = "192.168.50.111"
    # Android check redirects
    res_android = client.get('/generate_204', environ_base={'REMOTE_ADDR': ip})
    assert res_android.status_code == 302

    # Apple check redirects
    res_apple = client.get('/hotspot-detect.html', environ_base={'REMOTE_ADDR': ip})
    assert res_apple.status_code == 302

    # Windows check redirects
    res_win = client.get('/ncsi.txt', environ_base={'REMOTE_ADDR': ip})
    assert res_win.status_code == 302

    # RFC 8908 reports captive: true
    res_rfc = client.get('/api/captive-portal/rfc8908', environ_base={'REMOTE_ADDR': ip})
    assert res_rfc.status_code == 200
    assert res_rfc.get_json()["captive"] is True


def test_captive_detection_when_authenticated(client, gateway):
    ip = "192.168.50.112"
    gateway.authorize_device(ip, duration_seconds=3600)

    # Android check returns 204
    res_android = client.get('/generate_204', environ_base={'REMOTE_ADDR': ip})
    assert res_android.status_code == 204

    # Apple check returns 200 Success
    res_apple = client.get('/hotspot-detect.html', environ_base={'REMOTE_ADDR': ip})
    assert res_apple.status_code == 200
    assert b"Success" in res_apple.data

    # Windows check returns 200 text
    res_win = client.get('/ncsi.txt', environ_base={'REMOTE_ADDR': ip})
    assert res_win.status_code == 200
    assert b"Microsoft Connect Test" in res_win.data

    # RFC 8908 reports captive: false
    res_rfc = client.get('/api/captive-portal/rfc8908', environ_base={'REMOTE_ADDR': ip})
    assert res_rfc.status_code == 200
    assert res_rfc.get_json()["captive"] is False
