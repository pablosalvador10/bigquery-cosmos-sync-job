"""Pytest configuration — async mode and a quiet root logger."""

import logging

import pytest


@pytest.fixture(autouse=True)
def _silence_logs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.CRITICAL, logger="azure")
    caplog.set_level(logging.CRITICAL, logger="google")
