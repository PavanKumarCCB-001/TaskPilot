import re
from urllib.parse import urlsplit

from app.schemas.chat import Task
from app.services.security import validate_public_url

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class IntentError(ValueError):
    pass


def interpret(message: str) -> Task:
    urls = URL_RE.findall(message)
    if not urls:
        raise IntentError("Include a website URL beginning with http:// or https://.")
    url = urls[0].rstrip(".,!?;:)]}")
    try:
        parsed = urlsplit(url)
    except ValueError as exc:
        raise IntentError("The URL is invalid.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise IntentError("Only complete HTTP or HTTPS website URLs are supported.")
    if not any(word in message.lower() for word in ("crawl", "website", "webpage", "site", "extract", "summar")):
        raise IntentError("I can crawl a website. Ask me to crawl, summarize, or extract information from a URL.")
    if len(urls) > 1:
        raise IntentError("Please provide one website URL per request.")
    try:
        validate_public_url(url)
    except ValueError as exc:
        raise IntentError(str(exc)) from exc
    output = "summary_and_json"
    if "json" in message.lower() and not any(w in message.lower() for w in ("summary", "summar", "important information")):
        output = "json"
    elif any(w in message.lower() for w in ("summary", "summar", "important information")) and "json" not in message.lower():
        output = "summary"
    return Task(url=url, output_format=output)
