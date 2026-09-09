from unittest.mock import MagicMock

from backend.app.core.rate_limit_handler import rate_limit_exceeded_handler


def test_rate_limit_exceeded_handler() -> None:
    request = MagicMock()
    exc = MagicMock()

    response = rate_limit_exceeded_handler(
        request,
        exc,
    )

    assert response.status_code == 429
    assert response.body == (b'{"detail":"Rate limit exceeded. Try again later."}')
