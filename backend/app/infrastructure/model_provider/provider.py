"""Narrow OQI5-local `ModelProvider` abstraction (CDD-043 §23; Artifact
Authorization §3 row 5). Not a generic CTEC AI runtime and not a Gate V
extension -- no second consumer exists to justify a shared platform.
Responsibilities are limited to exactly what CDD-043 §23 authorizes:
provider/model identity, structured-output invocation, timeout, typed
failure classification.

Credentials are owned by this module's own configuration reader
(`AnthropicMessagesProvider`'s constructor/`os.environ` read) only --
never a field on the global `app.core.config.Settings` (CDD-043 §23:
"owned by the adapter's configuration layer only"; that file is outside
OQI5-I2's Artifact Authorization). A credential is never logged, never
placed in a `ModelInvocationRequest`/`ModelInvocationResult`, and never
included in any exception/failure-detail message.

The real adapter (`AnthropicMessagesProvider`) uses only the Python
standard library (`urllib.request`) for its HTTP call, so importing this
module never requires a new runtime dependency to be added to
`pyproject.toml`, which this Artifact Authorization does not authorize
touching. `FakeModelProvider` is the deterministic test double behind the
identical interface that normal CI exercises (CDD-043 §25: "no live
network dependency in normal CI")."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

_DEFAULT_TIMEOUT_SECONDS = 30
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
_ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_API_VERSION = "2023-06-01"


class ProviderFailureKind(StrEnum):
    """Closed classification of a provider-layer failure -- distinct from,
    and always upstream of, `AgentRecommendationValidator`'s own
    content-level `REJECTED_OUTPUT` classification (CDD-043 §18). A
    provider-layer failure always maps to `AgentRun.result_state ==
    FAILED`; it never itself produces `REJECTED_OUTPUT`."""

    TIMEOUT = "TIMEOUT"
    AUTH_FAILURE = "AUTH_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_ERROR = "NETWORK_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True, slots=True)
class ModelInvocationRequest:
    """The exact, bounded input handed to a provider adapter. `input_payload`
    is always the deterministically-canonicalized evidence packet (or the
    validated aggregate, for the synthesizer role) -- never an arbitrary or
    caller-supplied blob, and never contains credential material."""

    role_id: str
    role_version: int
    system_instructions: str
    input_payload: dict[str, Any]
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class ModelInvocationResult:
    """`raw_text` is present only when `succeeded` is True. `failure_detail`
    is a bounded, human-readable classification string -- it must never
    contain the provider API key or any other credential material."""

    succeeded: bool
    provider: str
    model: str
    raw_text: str | None
    failure_kind: ProviderFailureKind | None
    failure_detail: str


class ModelProvider(Protocol):
    """CDD-043 §23: the narrow OQI5-owned invocation interface every
    concrete adapter (real or fake) implements identically."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult: ...


class AnthropicMessagesProvider:
    """CDD-043 §23's one initial concrete adapter: a real production HTTP
    call to Anthropic's Messages API. Never invoked by normal CI (CDD-043
    §25) -- CI exercises `FakeModelProvider` behind the identical
    interface. Absence of a configured API key is a normal, fail-safe
    `NOT_CONFIGURED` result, never an exception and never a fabricated
    success."""

    def __init__(self, *, model: str | None = None) -> None:
        resolved_model = model
        if not resolved_model:
            resolved_model = os.environ.get("CTEC_MODEL_PROVIDER_MODEL", _DEFAULT_MODEL)
        self._model: str = resolved_model

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        api_key = os.environ.get("CTEC_MODEL_PROVIDER_API_KEY", "")
        if not api_key:
            return ModelInvocationResult(
                succeeded=False,
                provider=self.provider_name,
                model=self._model,
                raw_text=None,
                failure_kind=ProviderFailureKind.NOT_CONFIGURED,
                failure_detail="no provider API key configured",
            )
        body = json.dumps(
            {
                "model": self._model,
                "max_tokens": 2048,
                "system": request.system_instructions,
                "messages": [
                    {
                        "role": "user",
                        "content": json.dumps(request.input_payload, sort_keys=True),
                    }
                ],
            }
        ).encode("utf-8")
        http_request = urllib.request.Request(
            _ANTHROPIC_ENDPOINT,
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": _ANTHROPIC_API_VERSION,
            },
        )
        try:
            with urllib.request.urlopen(http_request, timeout=request.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                kind = ProviderFailureKind.AUTH_FAILURE
            elif exc.code == 429:
                kind = ProviderFailureKind.RATE_LIMITED
            else:
                kind = ProviderFailureKind.NETWORK_ERROR
            return ModelInvocationResult(
                succeeded=False,
                provider=self.provider_name,
                model=self._model,
                raw_text=None,
                failure_kind=kind,
                failure_detail=f"HTTP {exc.code}",
            )
        except TimeoutError:
            return ModelInvocationResult(
                succeeded=False,
                provider=self.provider_name,
                model=self._model,
                raw_text=None,
                failure_kind=ProviderFailureKind.TIMEOUT,
                failure_detail="provider invocation timed out",
            )
        except urllib.error.URLError as exc:
            return ModelInvocationResult(
                succeeded=False,
                provider=self.provider_name,
                model=self._model,
                raw_text=None,
                failure_kind=ProviderFailureKind.NETWORK_ERROR,
                failure_detail=str(exc.reason),
            )
        try:
            parsed = json.loads(response_body)
            text = "".join(
                block.get("text", "")
                for block in parsed.get("content", [])
                if isinstance(block, dict)
            )
        except (json.JSONDecodeError, AttributeError, TypeError):
            return ModelInvocationResult(
                succeeded=False,
                provider=self.provider_name,
                model=self._model,
                raw_text=None,
                failure_kind=ProviderFailureKind.MALFORMED_RESPONSE,
                failure_detail="provider response envelope was not well-formed",
            )
        return ModelInvocationResult(
            succeeded=True,
            provider=self.provider_name,
            model=self._model,
            raw_text=text,
            failure_kind=None,
            failure_detail="",
        )


@dataclass(slots=True)
class FakeModelProvider:
    """Deterministic test double behind the identical `ModelProvider`
    interface (CDD-043 §25: "no live network dependency in normal CI").
    Scripted via an ordered queue of `ModelInvocationResult` values, or a
    callable for input-dependent scripting -- never performs network I/O,
    so normal CI never requires live model credentials or network access."""

    responses: (
        Sequence[ModelInvocationResult] | Callable[[ModelInvocationRequest], ModelInvocationResult]
    )
    provider: str = "fake"
    model: str = "fake-model-v1"
    _call_count: int = field(default=0, init=False)

    @property
    def provider_name(self) -> str:
        return self.provider

    @property
    def model_name(self) -> str:
        return self.model

    def invoke(self, request: ModelInvocationRequest) -> ModelInvocationResult:
        if callable(self.responses):
            return self.responses(request)
        result = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        return result
