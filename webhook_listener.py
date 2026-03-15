#!/usr/bin/env python3
"""Local webhook listener for automatic PR reviews.

Receives GitHub webhooks via smee.io and triggers Claude Code.

Usage:
    1. Start smee client: smee -u YOUR_SMEE_URL -t http://localhost:3000
    2. Run this script: uv run python webhook_listener.py
    3. Create/update a PR - review will trigger automatically
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from dotenv import load_dotenv

load_dotenv()

PORT = 3000
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

# ── ANSI helpers ───────────────────────────────────────────────────────────────
_R = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_TAGS: dict[str, str] = {
    "ready":   f"\033[32m ready  {_R}",  # green
    "event":   f"\033[34m event  {_R}",  # blue
    "start":   f"\033[36m start  {_R}",  # cyan
    "done":    f"\033[32m done   {_R}",  # green
    "error":   f"\033[31m error  {_R}",  # red
    "auth":    f"\033[31m auth   {_R}",  # red
    "wait":    f"\033[33m wait   {_R}",  # yellow
    "timeout": f"\033[33m timeout{_R}",  # yellow
}


def _log(level: str, message: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    tag = _TAGS.get(level, f" {level:<7}")
    print(f"  {_DIM}{ts}{_R}  {tag}  {message}", flush=True)


# ── Webhook handler ────────────────────────────────────────────────────────────


class WebhookHandler(BaseHTTPRequestHandler):
    """Handle incoming GitHub webhook events."""

    def do_POST(self) -> None:  # noqa: N802
        """Process POST requests from GitHub webhooks."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        event_type = self.headers.get("X-GitHub-Event", "unknown")
        _log("event", f"received  {event_type}")

        if WEBHOOK_SECRET:
            signature = self.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(body, signature):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Invalid signature")
                _log("auth", "rejected — invalid webhook signature")
                return
            _log("auth", "signature ok")
        else:
            _log("auth", "no secret configured — skipping verification")

        payload = json.loads(body.decode("utf-8"))

        if event_type == "pull_request":
            action = payload.get("action", "")
            _log("event", f"pull_request action={action!r}")
            if action in ("opened", "synchronize", "reopened"):
                self._handle_pr_event(payload)
            else:
                _log("event", f"ignored — action {action!r} not in (opened, synchronize, reopened)")

        elif event_type == "issue_comment":
            action = payload.get("action", "")
            comment_body = payload.get("comment", {}).get("body", "")
            is_pr = "pull_request" in payload.get("issue", {})
            has_trigger = "hey ai review" in comment_body.lower()
            _log("event", f"issue_comment  action={action!r}  is_pr={is_pr}  has_trigger={has_trigger}  body={comment_body[:60]!r}")
            if action == "created" and is_pr and has_trigger:
                self._handle_comment_trigger(payload)
            else:
                reasons = []
                if action != "created":
                    reasons.append(f"action={action!r} (need 'created')")
                if not is_pr:
                    reasons.append("not a PR comment")
                if not has_trigger:
                    reasons.append(f"trigger phrase 'hey ai review' not found in {comment_body[:40]!r}")
                _log("event", f"ignored — {', '.join(reasons)}")

        else:
            _log("event", f"ignored — unhandled event type {event_type!r}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def _verify_signature(self, body: bytes, signature: str) -> bool:
        """Verify GitHub webhook signature."""
        if not signature.startswith("sha256="):
            return False
        expected = (
            "sha256="
            + hmac.new(
                WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        return hmac.compare_digest(signature, expected)

    def _handle_pr_event(self, payload: dict[str, Any]) -> None:
        """Handle pull request events."""
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        pr_number = pr.get("number")
        repo_full = repo.get("full_name")
        action = payload.get("action")

        _log("event", f"pull_request:{action}  ·  {repo_full}#{pr_number}")
        thread = threading.Thread(
            target=self._trigger_review,
            args=(repo_full, pr_number),
            daemon=True,
        )
        thread.start()

    def _handle_comment_trigger(self, payload: dict[str, Any]) -> None:
        """Handle comment-triggered reviews."""
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})
        pr_number = issue.get("number")
        repo_full = repo.get("full_name")

        _log("event", f"issue_comment:triggered  ·  {repo_full}#{pr_number}")
        thread = threading.Thread(
            target=self._trigger_review,
            args=(repo_full, pr_number),
            daemon=True,
        )
        thread.start()

    def _trigger_review(self, repo: str, pr_number: int) -> None:
        """Trigger Claude Code to review the PR."""
        ref = f"{repo}#{pr_number}"
        _log("start", ref)
        started = time.monotonic()
        stop_ticker = threading.Event()

        def _ticker() -> None:
            """Log a heartbeat every 60 s while the review is running."""
            while not stop_ticker.wait(timeout=60):
                elapsed = time.monotonic() - started
                _log("wait", f"{ref}  still running  ({elapsed / 60:.0f}m elapsed)")

        ticker_thread = threading.Thread(target=_ticker, daemon=True)
        ticker_thread.start()

        try:
            claude_path = os.path.expanduser("~/.local/bin/claude")
            if not os.path.exists(claude_path):
                claude_path = "claude"
            _log("start", f"claude={claude_path}  api_key={'set (will remove)' if 'ANTHROPIC_API_KEY' in os.environ else 'not set'}")

            cmd = [
                claude_path,
                "--print",
                "--allowedTools",
                "Agent,Bash(gh:*),Bash(ruff:*),Bash(mypy:*),Bash(bandit:*),Bash(safety:*),Read,Write,Grep,Glob",
            ]

            env = os.environ.copy()
            env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
            if "ANTHROPIC_API_KEY" in env:
                del env["ANTHROPIC_API_KEY"]

            result = subprocess.run(
                cmd,
                input=f"/pr-review {ref}",
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout (multi-agent: lint + security + synthesis)
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                check=False,
            )

            elapsed = time.monotonic() - started
            duration = f"{elapsed:.0f}s" if elapsed < 60 else f"{elapsed / 60:.1f}m"

            if result.returncode == 0:
                _log("done", f"{ref}  ({duration})")
            else:
                _log("error", f"{ref}  exit={result.returncode}  ({duration})")

        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - started
            _log("timeout", f"{ref}  exceeded {elapsed / 60:.0f}m limit")
        except FileNotFoundError:
            _log("error", f"{ref}  claude CLI not found — is it installed?")
        except Exception as e:
            _log("error", f"{ref}  {type(e).__name__}: {e}")
        finally:
            stop_ticker.set()

    def log_message(self, _fmt: str, *_args: Any) -> None:
        """Suppress default HTTP server access logs."""


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Start the webhook listener server."""
    print()
    print(f"  {_BOLD}ai-review{_R}  webhook listener  ·  http://localhost:{PORT}")
    print()
    print(f"  {_DIM}forward events:  smee -u $SMEE_URL -t http://localhost:{PORT}{_R}")
    print()

    server = HTTPServer(("localhost", PORT), WebhookHandler)
    _log("ready", f"listening on :{PORT}")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print(f"  {_DIM}shutting down{_R}")
        server.shutdown()


if __name__ == "__main__":
    main()
