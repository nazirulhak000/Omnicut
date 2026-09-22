"""Shared live-fixture lifecycle for motion parity tests."""

from __future__ import annotations

import pytest

from tests.motion_capture.vite_fixture import serve_motion_capture_fixture


@pytest.fixture(scope="session")
def motion_fixture_url() -> str:
    """Serve the real Vite/React SequencePlayer fixture for this test session."""

    with serve_motion_capture_fixture() as server:
        yield server.url
