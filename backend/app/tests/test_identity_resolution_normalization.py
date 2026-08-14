from app.domain.identity_resolution import normalization as norm


def test_normalize_whitespace_and_case() -> None:
    assert norm.normalize_whitespace_and_case("  ACME   Corp  ") == "acme corp"


def test_normalize_name_strips_punctuation() -> None:
    assert norm.normalize_name("Acme, Inc.") == "acme inc"
    assert norm.normalize_name("O'Brien & Sons, LLC.") == "o brien sons llc"


def test_strip_legal_suffix_removes_trailing_suffix_only() -> None:
    assert norm.strip_legal_suffix("acme inc") == "acme"
    assert norm.strip_legal_suffix("acme holdings limited") == "acme holdings"
    assert norm.strip_legal_suffix("acme corp of texas") == "acme corp of texas"  # not trailing


def test_strip_legal_suffix_prefers_longest_multi_word_suffix() -> None:
    assert norm.strip_legal_suffix("acme pte ltd") == "acme"


def test_strip_legal_suffix_is_a_no_op_without_a_recognized_suffix() -> None:
    assert norm.strip_legal_suffix("acme holdings") == "acme holdings"


def test_canonical_name_combines_normalization_and_suffix_stripping() -> None:
    assert norm.canonical_name("Acme, Inc.") == "acme"
    assert norm.canonical_name("ACME INC") == "acme"
    assert norm.canonical_name("Acme, Incorporated.") == "acme"


def test_derive_acronym_uses_significant_words_excluding_suffix() -> None:
    assert norm.derive_acronym("Taiwan Semiconductor Manufacturing Company Limited") == "TSMC"
    assert norm.derive_acronym("TSMC") == "T"
    # "Co Ltd" is itself a two-word governed legal suffix (both words
    # stripped), leaving only three significant words -- "TSM", not "TSMC".
    assert norm.derive_acronym("Taiwan Semiconductor Manufacturing Co Ltd") == "TSM"


def test_normalize_acronym_strips_punctuation_and_uppercases() -> None:
    assert norm.normalize_acronym("t.s.m.c.") == "TSMC"
    assert norm.normalize_acronym("tsmc") == "TSMC"


def test_normalize_domain_strips_protocol_www_and_path() -> None:
    assert norm.normalize_domain("https://www.tsmc.com/investor") == "tsmc.com"
    assert norm.normalize_domain("TSMC.com") == "tsmc.com"
    assert norm.normalize_domain("tsmc.com") == "tsmc.com"


def test_normalize_country_passes_through_iso2_uppercased() -> None:
    assert norm.normalize_country("tw") == "TW"
    assert norm.normalize_country("TW") == "TW"


def test_normalize_country_normalizes_free_text() -> None:
    assert norm.normalize_country("  Taiwan ") == "taiwan"
    assert norm.normalize_country("TAIWAN") == "taiwan"


def test_normalize_address_strips_punctuation_and_case() -> None:
    assert (
        norm.normalize_address("No. 8, Li-Hsin Rd. 6, Hsinchu Science Park")
        == "no 8 li hsin rd 6 hsinchu science park"
    )


def test_normalize_postal_code_strips_punctuation_and_uppercases() -> None:
    assert norm.normalize_postal_code("300-78") == "30078"
    assert norm.normalize_postal_code("sw1a 1aa") == "SW1A1AA"


def test_fingerprint_is_deterministic_and_case_insensitive() -> None:
    a = norm.fingerprint("12345678900")
    b = norm.fingerprint(" 12345678900 ")
    c = norm.fingerprint("12345678900".upper())
    assert a == b == c
    assert a.startswith("fp:")


def test_fingerprint_never_reveals_the_raw_value() -> None:
    raw = "SECRET-TAX-ID-98765"
    fp = norm.fingerprint(raw)
    assert raw not in fp
    assert raw.lower() not in fp.lower()


def test_fingerprint_distinguishes_different_values() -> None:
    assert norm.fingerprint("111111111") != norm.fingerprint("222222222")
