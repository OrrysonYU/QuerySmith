"""Package-level smoke tests."""

import querysmith


def test_package_imports() -> None:
    """The installable package exposes its version."""
    assert querysmith.__version__ == "0.1.0"
