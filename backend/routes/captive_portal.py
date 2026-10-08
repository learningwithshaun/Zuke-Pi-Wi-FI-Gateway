import logging
from flask import Blueprint, request, jsonify, current_app
from backend.services.customer_service import CustomerService

logger = logging.getLogger(__name__)

captive_portal_bp = Blueprint('captive_portal', __name__, url_prefix='/api/captive-portal')


def get_client_ip() -> str:
    """Extract real client IP, respecting proxy forwarding headers if present."""
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # First IP in comma-separated list is the client IP
        client_ip = forwarded_for.split(',')[0].strip()
        if client_ip:
            return client_ip
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or '127.0.0.1'


@captive_portal_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/captive-portal/register
    Payload:
    {
        "name": "Amanda",
        "email": "customer@example.com",
        "marketing_consent": false
    }
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid request format. Expected JSON body."
        }), 400

    name = data.get('name')
    email = data.get('email')
    marketing_consent = bool(data.get('marketing_consent', False))

    client_ip = get_client_ip()
    duration_hours = current_app.config.get('SESSION_DURATION_HOURS', 8)

    success, response_body, status_code = CustomerService.register_customer(
        name=name,
        email=email,
        ip_address=client_ip,
        marketing_consent=marketing_consent,
        session_duration_hours=duration_hours
    )

    return jsonify(response_body), status_code


@captive_portal_bp.route('/status', methods=['GET'])
def status():
    """
    GET /api/captive-portal/status
    Query params:
        token (optional): session_token
    """
    client_ip = get_client_ip()
    session_token = request.args.get('token')
    if not session_token and 'Authorization' in request.headers:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            session_token = auth_header[7:].strip()

    status_data = CustomerService.get_status(
        ip_address=client_ip,
        session_token=session_token
    )

    return jsonify(status_data), 200
