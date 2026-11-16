import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.intent import IntentError, interpret
from app.services import orchestrator
from app.services.results import OutputError, parse_output
from app.schemas.chat import Task


def test_interpret_demo_request(monkeypatch):
    monkeypatch.setattr("app.services.intent.validate_public_url", lambda url: url)
    task = interpret("Crawl https://example.com, summarize and return JSON")
    assert task.url == "https://example.com"
    assert task.output_format == "summary_and_json"
    assert task.max_pages == 5


def test_reject_missing_url():
    with pytest.raises(IntentError):
        interpret("Please crawl the website and summarize it")


def test_reject_unsupported_task(monkeypatch):
    monkeypatch.setattr("app.services.intent.validate_public_url", lambda url: url)
    with pytest.raises(IntentError):
        interpret("Open https://example.com and do something")


def test_parse_output_checks_shape():
    good = {"success": True, "target_url": "https://example.com", "pages_crawled": 1, "summary": "real", "pages": [{}], "errors": []}
    assert parse_output(json.dumps(good)) == good
    with pytest.raises(OutputError):
        parse_output("not json")
    with pytest.raises(OutputError):
        parse_output(json.dumps({"success": True}))


def test_orchestrator_invokes_fixed_cli_and_captures_output(monkeypatch):
    monkeypatch.setattr(orchestrator, "validate_public_url", lambda url: url)
    payload = {"success": True, "target_url": "https://public.test/", "pages_crawled": 1, "summary": "live text", "pages": [{}], "errors": []}
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return orchestrator.subprocess.CompletedProcess(command, 0, json.dumps(payload), "crawler diagnostic")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    task = Task(url="https://public.test/")
    response = orchestrator.execute(task)
    assert response["status"] == "success"
    assert response["result"]["summary"] == "live text"
    assert response["stderr"] == "crawler diagnostic"
    assert captured["shell"] is False
    assert captured["command"][0] == sys.executable
    assert captured["command"][1].endswith("site_crawler.py")
