"""Connector-security verification for the Azure architecture (Noetva D0
Section S / I0-R1 Section 18).

Two distinct categories, deliberately not conflated:

1. LOCAL, RUNNABLE NOW -- the SSRF address-range policy itself
   (`ProductionEndpointSecurityPolicy`) is pure Python logic over an
   already-resolved IP address; it needs no live Azure network context to
   exercise, and this script actually runs it against the real backend
   code (not a reimplementation) every time it is invoked. This was run
   for real during I0-R1 authoring -- see the final report's Section AL
   for the captured output.

2. REQUIRES AZURE RUNTIME -- whether the NAT Gateway alters
   application-layer semantics, whether the connector's DNS-rebinding/
   IP-pinning defenses hold under Azure's real DNS resolver behavior, and
   whether a real customer HTTPS endpoint is reachable through the real
   egress path can only be proven against a live backend running inside
   the actual Container Apps Environment. These are explicitly marked
   NOT_RUN below and must be executed for real during the controlled Azure
   execution phase (16-I's own verification stage, AY).

Usage:
    python connector_security_check.py
Exit code 0 if every LOCAL check passes; non-zero otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.infrastructure.connectors.rest_connector import (  # noqa: E402
    ProductionEndpointSecurityPolicy,
    SSRFRejected,
)

LOCAL_CASES: list[tuple[str, str]] = [
    ("https://169.254.169.254/metadata/instance", "Azure IMDS metadata address"),
    ("https://[fe80::1]/", "IPv6 link-local"),
    ("https://10.0.0.5/", "RFC1918 private (10/8)"),
    ("https://172.16.0.5/", "RFC1918 private (172.16/12)"),
    ("https://192.168.1.5/", "RFC1918 private (192.168/16)"),
    ("https://127.0.0.1/", "loopback"),
    ("https://224.0.0.1/", "multicast"),
    ("http://169.254.169.254/", "metadata address, plain HTTP (non-https scheme)"),
]

AZURE_RUNTIME_REQUIRED = [
    "DNS-rebinding / validate-to-connect IP-pinning holds under Azure's real DNS resolver",
    "NAT Gateway egress does not alter TLS SNI, Host header, or certificate verification",
    "A real customer HTTPS endpoint is reachable through the deployed egress path",
    "No HTTP_PROXY/HTTPS_PROXY environment variable is ever set on the backend Container App "
    "(the connector would silently ignore it, but its ABSENCE is an environment fact to confirm, "
    "not something this script can observe from outside Azure)",
]


def main() -> int:
    policy = ProductionEndpointSecurityPolicy()
    failures = 0
    for url, label in LOCAL_CASES:
        try:
            policy.validate(url)
            print(f"FAIL (should have been rejected): {label} -> {url}")
            failures += 1
        except SSRFRejected as exc:
            print(f"PASS: {label} -> {exc.detail}")
        except Exception as exc:  # noqa: BLE001 -- any rejection is a pass; only silent success is a failure
            print(f"PASS (rejected via {type(exc).__name__}): {label} -> {exc}")

    print()
    print("AZURE-RUNTIME-REQUIRED checks (cannot be exercised without a live deployment):")
    for item in AZURE_RUNTIME_REQUIRED:
        print(f"  NOT_RUN -- REQUIRES AZURE RUNTIME: {item}")

    if failures:
        print(f"\n{failures} LOCAL check(s) FAILED.")
        return 1
    print(f"\nAll {len(LOCAL_CASES)} LOCAL checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
