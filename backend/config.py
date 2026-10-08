import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'zuke-gateway-dev-secret-key-replace-in-prod')
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(Path(__file__).resolve().parent / 'data' / 'zuke.db'))
    GATEWAY_TYPE = os.getenv('GATEWAY_TYPE', 'mock')
    SESSION_DURATION_HOURS = int(os.getenv('SESSION_DURATION_HOURS', '8'))
    PORTAL_URL = os.getenv('PORTAL_URL', 'http://192.168.50.1/')
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    TESTING = False


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    GATEWAY_TYPE = os.getenv('GATEWAY_TYPE', 'mock')


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ':memory:'
    GATEWAY_TYPE = 'mock'
    SECRET_KEY = 'test-secret-key'


class ProductionConfig(Config):
    """Production configuration for Raspberry Pi."""
    DEBUG = False
    GATEWAY_TYPE = os.getenv('GATEWAY_TYPE', 'nftables')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


def get_config():
    env = os.getenv('FLASK_ENV', 'development').lower()
    return config_by_name.get(env, DevelopmentConfig)
