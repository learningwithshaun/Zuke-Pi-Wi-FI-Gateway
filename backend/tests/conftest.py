import pytest
from backend.app import create_app
from backend.config import TestingConfig
from backend.database.db import get_db, init_db
from backend.services.gateway_service import get_gateway_service, reset_gateway_service_instance


@pytest.fixture
def app(tmp_path):
    reset_gateway_service_instance()
    
    db_file = tmp_path / "test_zuke.db"
    
    class CustomTestingConfig(TestingConfig):
        DATABASE_PATH = str(db_file)
    
    app = create_app(CustomTestingConfig)

    with app.app_context():
        init_db()

    yield app

    reset_gateway_service_instance()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def gateway(app):
    with app.app_context():
        gw = get_gateway_service()
        gw.clear_all()
        return gw
