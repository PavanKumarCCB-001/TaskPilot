import os
import subprocess
import sys
import time
from pathlib import Path
import site

from app.schemas.chat import Task
from app.services.results import OutputError, parse_output
from app.services.security import validate_public_url

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = BACKEND_ROOT / "cli" / "site_crawler.py"


def execute(task: Task, timeout: int = 45) -> dict:
    url = validate_public_url(task.url)
    command = [sys.executable, str(CLI_PATH), "--url", url, "--max-pages", str(task.max_pages), "--max-depth", str(task.max_depth), "--output-format", task.output_format]
    started = time.monotonic()
    try:
        # Python may be using the per-user package location on Windows. Pass only
        # that import directory, alongside the executable lookup essentials.
        child_env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""), "WINDIR": os.environ.get("WINDIR", ""), "PYTHONIOENCODING": "utf-8"}
        user_site = site.getusersitepackages()
        if user_site:
            child_env["PYTHONPATH"] = user_site
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, shell=False,
                              cwd=str(BACKEND_ROOT), env=child_env)
        duration = round(time.monotonic() - started, 3)
        try:
            result = parse_output(proc.stdout)
            parse_error = None
        except OutputError as exc:
            result, parse_error = None, str(exc)
        status = "success" if proc.returncode == 0 and result and result["success"] else ("partial" if result and result["pages"] else "failed")
        return {"status": status, "result": result, "stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode,
                "duration_seconds": duration, "tool": "site_crawler.py", "command": [sys.executable, "site_crawler.py", "--url", url, "--max-pages", str(task.max_pages), "--max-depth", str(task.max_depth), "--output-format", task.output_format], "parse_error": parse_error}
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {"status": "failed", "result": None, "stdout": stdout, "stderr": stderr + f"Crawler process exceeded the {timeout} second timeout.", "exit_code": None,
                "duration_seconds": round(time.monotonic() - started, 3), "tool": "site_crawler.py", "command": [sys.executable, "site_crawler.py", "--url", url], "parse_error": None}
