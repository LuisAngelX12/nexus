from sqlalchemy import text

from backend.app.core.config import get_settings
from backend.app.core.database import engine
from backend.app.jobs.celery_app import celery_app


def test_database_connection():
    """Comprueba que la aplicación puede conectarse a PostgreSQL."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_redis_connection():
    """Comprueba que Celery puede conectarse a Redis."""
    connection = celery_app.connection_for_read()

    try:
        connection.ensure_connection(max_retries=1)
    finally:
        connection.release()


def test_configuration():
    """Comprueba que las variables necesarias están configuradas."""
    settings = get_settings()

    assert settings.database_url
    assert settings.test_database_url
    assert settings.jwt_secret
    assert settings.redis_url


def test_celery_configuration():
    """Comprueba que Celery está configurado con Redis."""
    settings = get_settings()

    assert celery_app.conf.broker_url == settings.redis_url
    assert celery_app.conf.result_backend == settings.redis_url
