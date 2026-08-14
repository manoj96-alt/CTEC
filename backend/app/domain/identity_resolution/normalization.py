"""Deterministic, side-effect-free normalization helpers for identity
resolution evidence. Every function here is pure and safe to unit test in
isolation from the engine's classification logic."""

import hashlib
import re

# Common legal-form suffixes stripped when comparing organization names.
# Deliberately conservative: only unambiguous corporate-form tokens.
LEGAL_SUFFIXES: tuple[str, ...] = (
    "incorporated",
    "inc",
    "corporation",
    "corp",
    "company",
    "co",
    "limited",
    "ltd",
    "llc",
    "l l c",
    "plc",
    "gmbh",
    "s a",
    "sa",
    "s p a",
    "spa",
    "pte ltd",
    "pte",
    "ag",
    "nv",
    "bv",
    "kk",
    "co ltd",
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_whitespace_and_case(value: str) -> str:
    return _WHITESPACE.sub(" ", value.strip().casefold())


def normalize_name(value: str) -> str:
    """Case/whitespace/punctuation-normalized name, legal suffix retained."""
    return _WHITESPACE.sub(" ", _NON_ALNUM.sub(" ", value.casefold()).strip()).strip()


def strip_legal_suffix(normalized_value: str) -> str:
    """Remove a single trailing governed legal-form suffix, if present."""
    tokens = normalized_value.split()
    for suffix in sorted(LEGAL_SUFFIXES, key=lambda s: -len(s.split())):
        suffix_tokens = suffix.split()
        n = len(suffix_tokens)
        if n and tokens[-n:] == suffix_tokens:
            return " ".join(tokens[:-n]).strip()
    return normalized_value


def canonical_name(value: str) -> str:
    """Fully normalized name with legal suffix removed, for equality checks."""
    return strip_legal_suffix(normalize_name(value))


def derive_acronym(value: str) -> str:
    """Deterministic acronym derived from the first letter of each
    significant word (legal suffix excluded)."""
    stripped = strip_legal_suffix(normalize_name(value))
    words = [w for w in stripped.split() if w]
    return "".join(word[0] for word in words).upper()


def normalize_acronym(value: str) -> str:
    return _NON_ALNUM.sub("", value.upper())


def normalize_domain(value: str) -> str:
    """Lowercase, protocol/www/path-stripped registrable domain."""
    lowered = value.strip().casefold()
    lowered = re.sub(r"^[a-z]+://", "", lowered)
    lowered = lowered.split("/")[0]
    lowered = lowered.removeprefix("www.")
    return lowered


def normalize_country(value: str) -> str:
    """Best-effort normalized country label: ISO2 codes are upper-cased and
    passed through; free-text names are case/whitespace normalized. This
    intentionally does not perform full ISO lookup translation (no country
    reference table is part of this increment's scope)."""
    cleaned = normalize_whitespace_and_case(value)
    if len(cleaned) == 2:
        return cleaned.upper()
    return cleaned


def normalize_address(value: str) -> str:
    """Case/whitespace/punctuation-normalized registered address. Feasible
    normalization only: no geocoding or address-validation service."""
    return normalize_whitespace_and_case(_NON_ALNUM.sub(" ", value.casefold()))


def normalize_postal_code(value: str) -> str:
    return _NON_ALNUM.sub("", value.upper())


def fingerprint(value: str) -> str:
    """Non-reversible, comparable fingerprint for a sensitive identifier
    (e.g. tax/business registration numbers). Equal raw values always
    produce equal fingerprints, so conflicts remain detectable without ever
    persisting or displaying the raw value."""
    return f"fp:{hashlib.sha256(value.strip().casefold().encode()).hexdigest()[:12]}"
