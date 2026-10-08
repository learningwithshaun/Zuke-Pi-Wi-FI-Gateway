import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import get_config
from backend.database.db import init_app as init_db_app, init_db
from backend.routes.captive_portal import captive_portal_bp
from backend.routes.captive_detect import captive_detect_bp


def configure_logging(app: Flask):
    log_level = logging.DEBUG if app.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)

    if config_object is None:
        config_object = get_config()

    app.config.from_object(config_object)
    configure_logging(app)

    # Enable CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', '*'))

    # Setup database
    init_db_app(app)
    init_db(app)

    # Register blueprints
    app.register_blueprint(captive_portal_bp)
    app.register_blueprint(captive_detect_bp)

    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "healthy",
            "service": "zuke-wifi-gateway",
            "gateway_type": app.config.get('GATEWAY_TYPE', 'mock')
        }), 200

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    app.run(host=host, port=port)
