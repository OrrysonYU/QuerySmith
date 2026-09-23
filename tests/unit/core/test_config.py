import pytest
from pydantic import SecretStr, ValidationError

from querysmith.core.config import Settings


def test_defaults_and_secret_masking() -> None:
    settings = Settings()
    assert settings.policy.max_rows == 1000
    assert str(SecretStr("secret")) == "**********"


def test_invalid_deadline_fails() -> None:
    with pytest.raises(ValidationError):
        Settings(core={"request_deadline_seconds": 0})
