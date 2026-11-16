import json


class OutputError(ValueError):
    pass


def parse_output(stdout: str) -> dict:
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise OutputError("Crawler returned invalid JSON.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("success"), bool):
        raise OutputError("Crawler JSON is missing a valid success field.")
    for key in ("target_url", "pages_crawled", "pages", "summary", "errors"):
        if key not in data:
            raise OutputError(f"Crawler JSON is missing required field: {key}.")
    if not isinstance(data["pages"], list) or not isinstance(data["errors"], list):
        raise OutputError("Crawler JSON has invalid pages or errors fields.")
    if not isinstance(data["pages_crawled"], int) or data["pages_crawled"] != len(data["pages"]):
        raise OutputError("Crawler page count does not match its page results.")
    return data
