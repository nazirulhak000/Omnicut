"""Lifecycle regression tests for the self-hosted Vite parity fixture."""

from __future__ import annotations

import socket

import pytest

from tests.motion_capture.vite_fixture import serve_motion_capture_fixture


def test_vite_fixture_releases_its_loopback_port_after_exit():
    with serve_motion_capture_fixture() as server:
        port = server.port
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            pass

    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=0.5)
