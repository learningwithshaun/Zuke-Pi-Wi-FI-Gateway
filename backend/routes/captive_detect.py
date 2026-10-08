import logging
from flask import Blueprint, request, redirect, current_app, Response, jsonify
from backend.services.gateway_service import get_gateway_service

logger = logging.getLogger(__name__)

captive_detect_bp = Blueprint('captive_detect', __name__)


def _is_client_authenticated() -> bool:
    forwarded = request.headers.get('X-Forwarded-For')
    ip = forwarded.split(',')[0].strip() if forwarded else (request.remote_addr or '127.0.0.1')
    gateway = get_gateway_service()
    return gateway.is_authorized(ip)


def _get_portal_url() -> str:
    return current_app.config.get('PORTAL_URL', '/')


@captive_detect_bp.route('/generate_204')
@captive_detect_bp.route('/gen_204')
def android_check():
    """Android / Chrome captive portal check."""
    if _is_client_authenticated():
        return ('', 204)
    return redirect(_get_portal_url(), code=302)


@captive_detect_bp.route('/hotspot-detect.html')
@captive_detect_bp.route('/canonical.html')
def apple_check():
    """Apple Captive Network Assistant check."""
    if _is_client_authenticated():
        return Response(
            '<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>',
            mimetype='text/html',
            status=200
        )
    return redirect(_get_portal_url(), code=302)


@captive_detect_bp.route('/ncsi.txt')
@captive_detect_bp.route('/connecttest.txt')
def windows_check():
    """Windows NCSI check."""
    if _is_client_authenticated():
        return Response('Microsoft Connect Test', mimetype='text/plain', status=200)
    return redirect(_get_portal_url(), code=302)


@captive_detect_bp.route('/api/captive-portal/rfc8908')
def rfc8908():
    """RFC 8908 Captive Portal JSON API."""
    authenticated = _is_client_authenticated()
    portal_url = _get_portal_url()
    return jsonify({
        "captive": not authenticated,
        "user-portal-url": portal_url,
        "venue-info-url": portal_url
    }), 200
