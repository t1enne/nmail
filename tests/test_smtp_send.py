"""Minimal CLI smoke tests for nmail send — no subprocess mocking."""

from __future__ import annotations

import sys

import pytest
from click.testing import CliRunner

import nmail.cli.send  # force-load the module

_send_mod = sys.modules["nmail.cli.send"]
_send_fn = _send_mod.send  # the Click Command


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_send_empty_queue() -> None:
    result = CliRunner().invoke(_send_fn, [])
    assert result.exit_code == 0
    assert "No messages to send." in result.output
