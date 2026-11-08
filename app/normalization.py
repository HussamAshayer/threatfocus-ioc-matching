import ipaddress
import string

ALLOWED_CHARACTERS = set(string.ascii_lowercase + string.digits + "-")


class InvalidIndicatorError(ValueError):
    pass


def normalize_ipv4(raw: str) -> str:
    try:
        return str(ipaddress.IPv4Address(raw.strip()))
    except ipaddress.AddressValueError:
        raise InvalidIndicatorError(f"'{raw}' is not a valid IPv4 address") from None


def is_valid_label(label: str) -> bool:
    if not 1 <= len(label) <= 63:
        return False
    if not set(label) <= ALLOWED_CHARACTERS:
        return False
    if label.startswith("-") or label.endswith("-"):
        return False
    return True


def normalize_domain(raw: str) -> str:
    value = raw.strip().lower()
    if value.endswith("."):
        value = value[:-1]

    if not value or len(value) > 253:
        raise InvalidIndicatorError(f"'{raw}' is not a valid domain: length must be 1-253 characters")

    labels = value.split(".")
    if len(labels) < 2:
        raise InvalidIndicatorError(f"'{raw}' is not a valid domain: it needs at least two labels, e.g. example.com")

    for label in labels:
        if not is_valid_label(label):
            raise InvalidIndicatorError(f"'{raw}' is not a valid domain: invalid label '{label}'")

    if labels[-1].isdigit():
        raise InvalidIndicatorError(f"'{raw}' looks like an IP address; use type 'ipv4'")

    return value


def normalize(indicator_type: str, raw: str) -> str:
    if indicator_type == "ipv4":
        return normalize_ipv4(raw)
    if indicator_type == "domain":
        return normalize_domain(raw)
    raise InvalidIndicatorError(f"Unsupported type '{indicator_type}'; use 'ipv4' or 'domain'")
