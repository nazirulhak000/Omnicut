"""Offline tests for scripts/tls_cert_manager.py using tmp_path only."""

from __future__ import annotations

import ipaddress
from datetime import timedelta

from cryptography import x509

from scripts.tls_cert_manager import (
    LEAF_VALIDITY_DAYS,
    ensure_ca,
    ensure_server_cert,
    get_cert_dir,
    get_cert_info,
)


def test_cert_dir_respects_env_and_arg(tmp_path, monkeypatch):
    env_dir = tmp_path / "env_certs"
    monkeypatch.setenv("OMNICUT_CERT_DIR", str(env_dir))
    assert get_cert_dir() == env_dir
    assert env_dir.is_dir()

    arg_dir = tmp_path / "arg_certs"
    assert get_cert_dir(arg_dir) == arg_dir
    assert arg_dir.is_dir()


def test_ensure_ca_creates_and_reuses_root_ca(tmp_path):
    ca_crt, ca_key = ensure_ca(tmp_path)
    assert ca_crt.exists()
    assert ca_key.exists()

    cert1 = x509.load_pem_x509_certificate(ca_crt.read_bytes())
    bc = cert1.extensions.get_extension_for_class(x509.BasicConstraints).value
    assert bc.ca is True

    ca_crt2, _ = ensure_ca(tmp_path)
    cert2 = x509.load_pem_x509_certificate(ca_crt2.read_bytes())
    assert cert1.serial_number == cert2.serial_number


def test_ensure_server_cert_san_and_ip_change_regeneration(tmp_path):
    crt_path, key_path = ensure_server_cert("192.168.1.42", cert_dir=tmp_path)
    assert crt_path.exists()
    assert key_path.exists()

    cert1 = x509.load_pem_x509_certificate(crt_path.read_bytes())
    ca_cert = x509.load_pem_x509_certificate((tmp_path / "ca.crt").read_bytes())
    assert cert1.issuer == ca_cert.subject
    assert (cert1.not_valid_after_utc - cert1.not_valid_before_utc) >= timedelta(days=LEAF_VALIDITY_DAYS)

    san1 = cert1.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    ips1 = {str(ip) for ip in san1.get_values_for_type(x509.IPAddress)}
    dns1 = set(san1.get_values_for_type(x509.DNSName))
    assert ipaddress.ip_address("192.168.1.42") in san1.get_values_for_type(x509.IPAddress)
    assert {"192.168.1.42", "127.0.0.1"}.issubset(ips1)
    assert "localhost" in dns1

    # Same IP -> reused without regeneration
    crt_path_same, _ = ensure_server_cert("192.168.1.42", cert_dir=tmp_path)
    cert_same = x509.load_pem_x509_certificate(crt_path_same.read_bytes())
    assert cert_same.serial_number == cert1.serial_number

    # Different LAN IP -> auto-regenerated with new SAN IP
    crt_path_new, _ = ensure_server_cert("10.0.0.77", cert_dir=tmp_path)
    cert2 = x509.load_pem_x509_certificate(crt_path_new.read_bytes())
    assert cert2.serial_number != cert1.serial_number

    san2 = cert2.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    ips2 = {str(ip) for ip in san2.get_values_for_type(x509.IPAddress)}
    assert "10.0.0.77" in ips2
    assert "127.0.0.1" in ips2

    info = get_cert_info(tmp_path)
    assert info["ca_exists"] is True
    assert info["server_exists"] is True
    assert "10.0.0.77" in info["san_ips"]
