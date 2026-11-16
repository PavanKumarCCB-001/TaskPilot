import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit


def validate_public_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError("The URL is malformed.") from exc
    if parts.scheme.lower() not in {"http", "https"} or not host or parts.username or parts.password:
        raise ValueError("Only public HTTP and HTTPS URLs without embedded credentials are allowed.")
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("The URL port is invalid.")
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
        addresses = [literal]
    except ValueError:
        if host.lower() == "localhost" or host.lower().endswith(".localhost"):
            raise ValueError("Local and internal network destinations are not allowed.")
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except (OSError, ValueError):
            raise ValueError("The website hostname could not be resolved.")
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Local and internal network destinations are not allowed.")
    # Normalize away fragments; retain path, query, and explicit port.
    return urlunsplit((parts.scheme.lower(), parts.netloc, parts.path or "/", parts.query, ""))
