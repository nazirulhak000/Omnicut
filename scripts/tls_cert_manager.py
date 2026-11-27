"""
Pure-Python TLS certificate manager for the OmniCut Mobile HTTPS Bridge.

Generates and caches a local Root CA (`ca.crt` / `ca.key`) and a dynamic
SubjectAlternativeName (SAN) leaf certificate (`server.crt` / `server.key`)
under ``%APPDATA%\\OmniCut\\certs\\`` (or ``OMNICUT_CERT_DIR`` / explicit
``cert_dir`` argument). Never writes certificates into the repository.
"""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

CA_VALIDITY_DAYS = 3650
LEAF_VALIDITY_DAYS = 365
_RENEW_BUFFER_DAYS = 7


def get_cert_dir(cert_dir: Optional[Path | str] = None) -> Path:
    """Resolve and create the certificate storage directory outside the repo."""
    if cert_dir is not None:
        target = Path(cert_dir)
    else:
        env_dir = (os.environ.get("OMNICUT_CERT_DIR") or "").strip()
        if env_dir:
            target = Path(env_dir)
        else:
            appdata = (os.environ.get("APPDATA") or "").strip()
            if appdata:
                target = Path(appdata) / "OmniCut" / "certs"
            else:
                target = Path.home() / ".omnicut" / "certs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _generate_rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _write_key_and_cert(
    key_path: Path,
    crt_path: Path,
    private_key: rsa.RSAPrivateKey,
    cert: x509.Certificate,
) -> None:
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    crt_bytes = cert.public_bytes(serialization.Encoding.PEM)
    key_path.write_bytes(key_bytes)
    crt_path.write_bytes(crt_bytes)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass


def _load_ca(ca_crt_path: Path, ca_key_path: Path) -> Optional[Tuple[x509.Certificate, rsa.RSAPrivateKey]]:
    if not ca_crt_path.exists() or not ca_key_path.exists():
        return None
    try:
        cert = x509.load_pem_x509_certificate(ca_crt_path.read_bytes())
        key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            return None
        now = datetime.now(timezone.utc)
        if cert.not_valid_after_utc <= now + timedelta(days=_RENEW_BUFFER_DAYS):
            return None
        return cert, key
    except Exception:
        return None


def ensure_ca(cert_dir: Optional[Path | str] = None) -> Tuple[Path, Path]:
    """Ensure a valid Root CA exists in ``cert_dir`` and return ``(ca.crt, ca.key)``."""
    base = get_cert_dir(cert_dir)
    ca_crt_path = base / "ca.crt"
    ca_key_path = base / "ca.key"

    if _load_ca(ca_crt_path, ca_key_path) is not None:
        return ca_crt_path, ca_key_path

    ca_key = _generate_rsa_key()
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OmniCut Pro Studio"),
        x509.NameAttribute(NameOID.COMMON_NAME, "OmniCut Local Root CA"),
    ])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=CA_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    _write_key_and_cert(ca_key_path, ca_crt_path, ca_key, ca_cert)
    return ca_crt_path, ca_key_path


def _build_san_entries(lan_ip: str, extra_sans: Optional[Iterable[str]] = None) -> Tuple[list[x509.GeneralName], set[str], set[str]]:
    expected_ips: set[str] = {"127.0.0.1"}
    expected_dns: set[str] = {"localhost"}

    candidates = [lan_ip]
    if extra_sans:
        candidates.extend(extra_sans)

    for raw in candidates:
        item = (raw or "").strip()
        if not item:
            continue
        try:
            ip_obj = ipaddress.ip_address(item)
            expected_ips.add(str(ip_obj))
        except ValueError:
            expected_dns.add(item.lower())

    entries: list[x509.GeneralName] = []
    for ip_str in sorted(expected_ips):
        entries.append(x509.IPAddress(ipaddress.ip_address(ip_str)))
    for dns_str in sorted(expected_dns):
        entries.append(x509.DNSName(dns_str))
    return entries, expected_ips, expected_dns


def _leaf_matches_sans(
    server_crt_path: Path,
    server_key_path: Path,
    ca_cert: x509.Certificate,
    expected_ips: set[str],
    expected_dns: set[str],
) -> bool:
    if not server_crt_path.exists() or not server_key_path.exists():
        return False
    try:
        cert = x509.load_pem_x509_certificate(server_crt_path.read_bytes())
        serialization.load_pem_private_key(server_key_path.read_bytes(), password=None)
        if cert.issuer != ca_cert.subject:
            return False
        now = datetime.now(timezone.utc)
        if cert.not_valid_after_utc <= now + timedelta(days=_RENEW_BUFFER_DAYS):
            return False
        san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        actual_ips = {str(ip) for ip in san_ext.get_values_for_type(x509.IPAddress)}
        actual_dns = {d.lower() for d in san_ext.get_values_for_type(x509.DNSName)}
        return expected_ips.issubset(actual_ips) and expected_dns.issubset(actual_dns)
    except Exception:
        return False


def ensure_server_cert(
    lan_ip: str,
    cert_dir: Optional[Path | str] = None,
    extra_sans: Optional[Iterable[str]] = None,
) -> Tuple[Path, Path]:
    """Ensure a valid 365-day SAN leaf cert exists for ``lan_ip``, ``127.0.0.1``, and ``localhost``.

    Automatically regenerates the leaf cert whenever ``lan_ip`` changes or is missing from SANs.
    Returns ``(server.crt, server.key)``.
    """
    base = get_cert_dir(cert_dir)
    ca_crt_path, ca_key_path = ensure_ca(base)
    loaded_ca = _load_ca(ca_crt_path, ca_key_path)
    if loaded_ca is None:
        raise RuntimeError("Failed to load or initialize OmniCut Root CA")
    ca_cert, ca_key = loaded_ca

    server_crt_path = base / "server.crt"
    server_key_path = base / "server.key"

    san_entries, expected_ips, expected_dns = _build_san_entries(lan_ip, extra_sans)
    if _leaf_matches_sans(server_crt_path, server_key_path, ca_cert, expected_ips, expected_dns):
        return server_crt_path, server_key_path

    leaf_key = _generate_rsa_key()
    now = datetime.now(timezone.utc)
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OmniCut Pro Studio"),
        x509.NameAttribute(NameOID.COMMON_NAME, "OmniCut Mobile Bridge"),
    ])
    leaf_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=LEAF_VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(leaf_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    _write_key_and_cert(server_key_path, server_crt_path, leaf_key, leaf_cert)
    return server_crt_path, server_key_path


def get_cert_info(cert_dir: Optional[Path | str] = None) -> dict:
    """Return non-secret metadata about the cached Root CA and leaf certificate."""
    base = get_cert_dir(cert_dir)
    ca_crt_path = base / "ca.crt"
    server_crt_path = base / "server.crt"
    san_ips: list[str] = []
    san_dns: list[str] = []
    not_after: Optional[str] = None

    if server_crt_path.exists():
        try:
            cert = x509.load_pem_x509_certificate(server_crt_path.read_bytes())
            not_after = cert.not_valid_after_utc.isoformat()
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            san_ips = [str(ip) for ip in san_ext.get_values_for_type(x509.IPAddress)]
            san_dns = list(san_ext.get_values_for_type(x509.DNSName))
        except Exception:
            pass

    return {
        "cert_dir": str(base),
        "ca_exists": ca_crt_path.exists(),
        "server_exists": server_crt_path.exists(),
        "san_ips": san_ips,
        "san_dns": san_dns,
        "not_after": not_after,
    }
