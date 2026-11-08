import pytest

from app.normalization import InvalidIndicatorError, normalize


@pytest.mark.parametrize("raw", ["Suspicious.Example.", "SUSPICIOUS.EXAMPLE", "  suspicious.example  "])
def test_equivalent_domain_spellings_normalize_to_same_value(raw):
    assert normalize("domain", raw) == "suspicious.example"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("mail.evil-site.com", "mail.evil-site.com"),
        ("a.co", "a.co"),
        ("xn--caf-dma.com", "xn--caf-dma.com"),
    ],
)
def test_valid_domains_are_accepted(raw, expected):
    assert normalize("domain", raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        ".",
        "localhost",
        "evil..com",
        "evil.com..",
        "http://evil.com",
        "evil.com/login",
        "evil_site.com",
        "ev il.com",
        "-evil.com",
        "evil-.com",
        "café.com",
        "192.0.2.10",
        "a" * 64 + ".com",
        ("a" * 60 + ".") * 5 + "com",
    ],
)
def test_invalid_domains_are_rejected(raw):
    with pytest.raises(InvalidIndicatorError):
        normalize("domain", raw)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("192.0.2.10", "192.0.2.10"),
        ("  192.0.2.10  ", "192.0.2.10"),
        ("0.0.0.0", "0.0.0.0"),
        ("255.255.255.255", "255.255.255.255"),
    ],
)
def test_valid_ipv4_addresses_are_accepted(raw, expected):
    assert normalize("ipv4", raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "abc", "256.1.1.1", "1.2.3", "1.2.3.4.5", "1.2.3.-4", "192.0.2.010", "::1", "evil.com"],
)
def test_invalid_ipv4_addresses_are_rejected(raw):
    with pytest.raises(InvalidIndicatorError):
        normalize("ipv4", raw)


@pytest.mark.parametrize("indicator_type", ["email", "ipv6", "DOMAIN", ""])
def test_unsupported_types_are_rejected(indicator_type):
    with pytest.raises(InvalidIndicatorError):
        normalize(indicator_type, "evil.com")


def test_error_message_explains_the_problem():
    with pytest.raises(InvalidIndicatorError, match="at least two labels"):
        normalize("domain", "localhost")
