#!/usr/bin/env python3
"""Bounded, robots-aware website crawler. JSON results go to stdout; diagnostics to stderr."""
import argparse
import ipaddress
import json
import re
import socket
import sys
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

UA = "TaskPilotDemoCrawler/1.0 (+local hackathon prototype; respectful crawling)"
TIMEOUT = (4, 8)
MAX_BYTES = 1_500_000


def safe_url(url):
    p = urlsplit(url)
    if p.scheme.lower() not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Only public HTTP/HTTPS URLs are allowed")
    host = p.hostname
    if host.lower() == "localhost" or host.lower().endswith(".localhost"):
        raise ValueError("Local destinations are not allowed")
    try:
        ips = [ipaddress.ip_address(host.strip("[]"))]
    except ValueError:
        try:
            ips = [ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except OSError as exc:
            raise ValueError("Hostname could not be resolved") from exc
    if not ips or any(not ip.is_global for ip in ips):
        raise ValueError("Local or internal network destinations are not allowed")
    netloc = p.netloc.lower()
    return urlunsplit((p.scheme.lower(), netloc, p.path or "/", p.query, ""))


def fetch(url, session):
    current = safe_url(url)
    for _ in range(6):
        response = session.get(current, timeout=TIMEOUT, allow_redirects=False, stream=True)
        if response.is_redirect or response.is_permanent_redirect:
            target = response.headers.get("Location")
            response.close()
            if not target:
                raise ValueError("Redirect did not include a destination")
            current = safe_url(urljoin(current, target))
            continue
        response.raise_for_status()
        body = bytearray()
        for chunk in response.iter_content(16384):
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                response.close()
                raise ValueError("Response exceeded the 1.5 MB page limit")
        return response, bytes(body), current
    raise ValueError("Too many redirects")


def robots_for(origin, session, cache):
    if origin in cache:
        return cache[origin]
    parser = RobotFileParser()
    robots_url = origin + "/robots.txt"
    try:
        _, body, final_url = fetch(robots_url, session)
        parser.set_url(final_url)
        parser.parse(body.decode("utf-8", errors="replace").splitlines())
        # Redirects to another origin are not used as authorization for this one.
        if urlsplit(final_url).netloc != urlsplit(origin).netloc:
            parser = RobotFileParser(); parser.parse([])
    except requests.HTTPError as exc:
        # 404 means no published restrictions; other server errors fail closed.
        if exc.response is not None and exc.response.status_code == 404:
            parser.parse(["User-agent: *", "Allow: /"])
        else:
            parser.parse(["User-agent: *", "Disallow: /"])
    except (requests.RequestException, ValueError):
        parser.parse(["User-agent: *", "Disallow: /"])
    cache[origin] = parser
    return parser


def extract_text(soup):
    for node in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        node.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    return re.sub(r"\s+", " ", root.get_text(" ", strip=True))[:5000]


def crawl(url, max_pages=5, max_depth=1, output_format="summary_and_json"):
    target = safe_url(url)
    host = urlsplit(target).netloc
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    queue = deque([(target, 0)])
    seen, pages, errors, robots_cache = set(), [], [], {}
    while queue and len(pages) < max_pages:
        candidate, depth = queue.popleft()
        try:
            normalized = safe_url(candidate)
            # Stay same-origin including port; this also restricts discovered links.
            if urlsplit(normalized).netloc != host or normalized in seen:
                continue
            seen.add(normalized)
            origin = f"{urlsplit(normalized).scheme}://{urlsplit(normalized).netloc}"
            robots = robots_for(origin, session, robots_cache)
            if not robots.can_fetch(UA, normalized):
                errors.append({"url": normalized, "error": "Robots.txt disallows crawling this URL."})
                print(f"robots.txt disallows {normalized}", file=sys.stderr)
                continue
            response, body, final_url = fetch(normalized, session)
            if urlsplit(final_url).netloc != host:
                response.close()
                raise ValueError("Cross-origin redirects are not followed")
            status = response.status_code
            content_type = response.headers.get("Content-Type", "")
            response.close()
            if "html" not in content_type.lower():
                errors.append({"url": final_url, "error": f"Skipped non-HTML content ({content_type or 'unknown content type'})."})
                continue
            soup = BeautifulSoup(body, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
            description = meta.get("content", "").strip() if meta else ""
            headings = [{"level": int(h.name[1]), "text": h.get_text(" ", strip=True)} for h in soup.find_all(re.compile(r"^h[1-3]$")) if h.get_text(strip=True)]
            content = extract_text(soup)
            links = []
            for a in soup.find_all("a", href=True):
                try:
                    link = safe_url(urljoin(final_url, a["href"]))
                    if urlsplit(link).netloc == host and link not in links:
                        links.append(link)
                except ValueError:
                    continue
            pages.append({"url": final_url, "title": title, "description": description, "headings": headings, "content": content, "internal_links": links[:100], "status_code": status})
            print(f"crawled {final_url} ({status})", file=sys.stderr)
            if depth < max_depth:
                for link in links:
                    if link not in seen:
                        queue.append((link, depth + 1))
        except (requests.RequestException, ValueError, UnicodeError) as exc:
            errors.append({"url": candidate, "error": str(exc)})
            print(f"failed {candidate}: {exc}", file=sys.stderr)
    descriptions = [p["description"] or p["content"] for p in pages]
    summary = " ".join(x for x in descriptions if x).strip()[:1400]
    if not summary:
        summary = "No readable page content was extracted." if pages else "No pages could be crawled."
    return {"success": bool(pages) and not errors, "target_url": target, "pages_crawled": len(pages), "summary": summary, "pages": pages, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="Crawl a public website and emit extracted JSON")
    parser.add_argument("--url", required=True)
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--max-depth", type=int, default=1)
    parser.add_argument("--output-format", choices=("summary", "json", "summary_and_json"), default="summary_and_json")
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 5 or not 0 <= args.max_depth <= 1:
        parser.error("max-pages must be 1..5 and max-depth must be 0..1")
    try:
        result = crawl(args.url, args.max_pages, args.max_depth, args.output_format)
    except (ValueError, requests.RequestException) as exc:
        result = {"success": False, "target_url": args.url, "pages_crawled": 0, "summary": "Crawl failed.", "pages": [], "errors": [{"url": args.url, "error": str(exc)}]}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
