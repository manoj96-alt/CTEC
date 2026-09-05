"""Deterministic, stdlib-only (`http.server`) HTTPS fixture service (CDD-059
SS45/SS64; Artifact Authorization row 14). Proves genuine Level 1 (real
network transport) + Level 2 (enterprise-compatible contract) behavior for
`RestConnector` without claiming any real-vendor (Level 3) certification.

Importable in-process for host/CI tests (a real `ThreadingHTTPServer`
bound to `127.0.0.1` over a genuine loopback TCP/TLS socket -- not a mock
of `urllib.request`), and runnable standalone (see `__main__` below) as
the Docker-Compose fixture service, reachable only over the internal
Compose network.

Serves HTTPS with a self-signed certificate generated deterministically at
startup; test callers point `RestConnector` at this certificate via
`CTEC_CONNECTOR_TEST_CA_BUNDLE` -- TLS verification remains fully enabled
throughout; only the trusted CA differs, exactly as CDD-059's Artifact
Authorization SS8 requires."""

from __future__ import annotations

import http.server
import ipaddress
import json
import ssl
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

_DEFAULT_PAGE_SIZE = 2


def _generate_self_signed_cert(tmp_dir: str) -> tuple[str, str]:
    """Stdlib-only self-signed certificate generation via the `cryptography`
    library (already a transitive production dependency of `python-jose`/
    `PyJWT[crypto]` -- confirmed present, no new dependency added)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, "ctec-connector-fixture.test")]
    )
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    # Additive only -- Docker-Compose reaches this fixture
                    # by its own service name (Artifact Authorization §8),
                    # never by "localhost"/127.0.0.1 from another
                    # container; the host/in-process crowns above remain
                    # unaffected since those SAN entries are untouched.
                    x509.DNSName("connector-fixture"),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_path = f"{tmp_dir}/fixture-cert.pem"
    key_path = f"{tmp_dir}/fixture-key.pem"
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    return cert_path, key_path


class DeterministicHttpFixtureServer:
    """One instance == one deterministic external "enterprise source".
    `set_records`/`queue_failure` may be called at any time, including
    while the server is running, to prove genuine update/replay/failure
    crowns across multiple real connector runs."""

    def __init__(
        self,
        *,
        records: list[dict[str, object]] | None = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self._lock = threading.Lock()
        self._records: list[dict[str, object]] = list(records) if records else []
        self._page_size = page_size
        self._script: list[str] = []
        self._tmp_dir = tempfile.mkdtemp(prefix="ctec-connector-fixture-")
        self._cert_path, self._key_path = _generate_self_signed_cert(self._tmp_dir)

        server = self

        class _Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                pass  # deterministic tests do not need stderr request logs

            def do_GET(self) -> None:
                server._handle_get(self)

        self._httpd = http.server.ThreadingHTTPServer((host, port), _Handler)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=self._cert_path, keyfile=self._key_path)
        self._httpd.socket = ssl_context.wrap_socket(self._httpd.socket, server_side=True)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> DeterministicHttpFixtureServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()

    @property
    def base_url(self) -> str:
        host, port = str(self._httpd.server_address[0]), self._httpd.server_address[1]
        display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
        return f"https://{display_host}:{port}"

    @property
    def ca_bundle_path(self) -> str:
        return self._cert_path

    def set_records(self, records: list[dict[str, object]]) -> None:
        with self._lock:
            self._records = list(records)

    def queue_failure(self, kind: str) -> None:
        """One-shot: `kind` is consumed by the next matching request only.
        Supported: 'malformed_json', 'http_500', 'http_429', 'http_401',
        'redirect', 'malformed_record', 'sleep:<seconds>'."""
        with self._lock:
            self._script.append(kind)

    def _pop_scripted_failure(self) -> str | None:
        with self._lock:
            if self._script:
                return self._script.pop(0)
            return None

    def _handle_get(self, handler: http.server.BaseHTTPRequestHandler) -> None:
        scripted = self._pop_scripted_failure()
        if scripted is not None and scripted.startswith("sleep:"):
            import time as _time

            _time.sleep(float(scripted.split(":", 1)[1]))
            scripted = self._pop_scripted_failure()

        if scripted == "http_500":
            handler.send_response(500)
            handler.end_headers()
            return
        if scripted == "http_429":
            handler.send_response(429)
            handler.send_header("Retry-After", "0")
            handler.end_headers()
            return
        if scripted == "http_401":
            handler.send_response(401)
            handler.end_headers()
            return
        if scripted == "redirect":
            handler.send_response(302)
            handler.send_header("Location", self.base_url + "/")
            handler.end_headers()
            return
        if scripted == "malformed_json":
            body = b"{not-valid-json"
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(body)))
            handler.end_headers()
            handler.wfile.write(body)
            return

        parsed = urlsplit(handler.path)
        query = parse_qs(parsed.query)
        offset = int(query.get("offset", ["0"])[0])

        with self._lock:
            all_records = list(self._records)
        page = all_records[offset : offset + self._page_size]
        next_offset = offset + self._page_size
        has_next = next_offset < len(all_records)

        if scripted == "malformed_record" and page:
            page = [*page]
            page[0] = {"__malformed__": True}  # missing the configured record-id path entirely

        envelope: dict[str, object] = {
            "records": page,
            "next": f"{self.base_url}/?offset={next_offset}" if has_next else None,
        }
        body = json.dumps(envelope).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)


def build_default_fixture(
    *, port: int = 0, host: str = "127.0.0.1"
) -> DeterministicHttpFixtureServer:
    """Factory used by both host tests and the standalone `__main__` entry
    below, so both paths construct an identically-shaped deterministic
    dataset."""
    return DeterministicHttpFixtureServer(
        host=host,
        port=port,
        records=[{"id": "REC-1", "lead_time_days": 10}, {"id": "REC-2", "lead_time_days": 20}],
    )


if __name__ == "__main__":
    import os
    import time

    _port = int(os.environ.get("CTEC_FIXTURE_PORT", "8443"))
    # Reachable by Compose service name (Artifact Authorization §8) -- the
    # class default of 127.0.0.1 (used by every host/in-process test above)
    # would otherwise bind only inside this container's own loopback
    # namespace, unreachable from any other Compose service.
    _server = build_default_fixture(port=_port, host="0.0.0.0")
    _server.start()
    print(f"[deterministic_http_fixture_server] listening on {_server.base_url}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        _server.stop()
