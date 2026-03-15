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
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PORT = 3000
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


class WebhookHandler(BaseHTTPRequestHandler):
    """Handle incoming GitHub webhook events."""

    def do_POST(self) -> None:  # noqa: N802
        """Process POST requests from GitHub webhooks."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Verify signature if secret is configured
        if WEBHOOK_SECRET:
            signature = self.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(body, signature):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Invalid signature")
                print("❌ Invalid webhook signature")
                return

        # Parse event
        event_type = self.headers.get("X-GitHub-Event", "")
        payload = json.loads(body.decode("utf-8"))

        print(f"\n📥 Received event: {event_type}")

        # Handle PR events
        if event_type == "pull_request":
            action = payload.get("action", "")
            if action in ("opened", "synchronize", "reopened"):
                self._handle_pr_event(payload)

        # Handle comment trigger
        elif event_type == "issue_comment":
            action = payload.get("action", "")
            comment_body = payload.get("comment", {}).get("body", "").lower()
            is_pr = "pull_request" in payload.get("issue", {})

            if action == "created" and is_pr and "hey ai review" in comment_body:
                self._handle_comment_trigger(payload)

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
        repo_full_name = repo.get("full_name")
        action = payload.get("action")

        print(f"🔄 PR #{pr_number} {action} in {repo_full_name}")
        # Run review in background thread to respond to webhook quickly
        thread = threading.Thread(
            target=self._trigger_review,
            args=(repo_full_name, pr_number),
            daemon=True,
        )
        thread.start()

    def _handle_comment_trigger(self, payload: dict[str, Any]) -> None:
        """Handle comment-triggered reviews."""
        issue = payload.get("issue", {})
        repo = payload.get("repository", {})

        pr_number = issue.get("number")
        repo_full_name = repo.get("full_name")

        print(f"💬 Review triggered by comment on PR #{pr_number}")
        # Run review in background thread to respond to webhook quickly
        thread = threading.Thread(
            target=self._trigger_review,
            args=(repo_full_name, pr_number),
            daemon=True,
        )
        thread.start()

    def _trigger_review(self, repo: str, pr_number: int) -> None:
        """Trigger Claude Code to review the PR."""
        print(f"🚀 Starting review for {repo}#{pr_number}...")

        try:
            # Get Claude path
            claude_path = os.path.expanduser("~/.local/bin/claude")
            if not os.path.exists(claude_path):
                claude_path = "claude"  # Fallback to PATH

            # Run Claude Code with the pr-review skill
            # Use allowedTools to explicitly permit gh commands
            # Pass prompt via stdin for --print mode
            prompt = f"/pr-review {repo}#{pr_number}"
            cmd = [
                claude_path,
                "--print",
                "--allowedTools",
                "Bash(gh:*),Read,Grep,Glob",
            ]
            print(f"   Running: {' '.join(cmd)}")
            print(f"   Prompt: {prompt}")

            # Pass full environment including PATH for Docker access
            env = os.environ.copy()
            env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"

            # Remove API key to use Claude Max subscription/OAuth login instead
            if "ANTHROPIC_API_KEY" in env:
                del env["ANTHROPIC_API_KEY"]
                print("   Using Claude subscription (not API key)")

            result = subprocess.run(
                cmd,
                input=prompt,  # Pass prompt via stdin
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__)),  # Run in project dir
                check=False,
            )

            if result.returncode == 0:
                print(f"✅ Review completed for {repo}#{pr_number}")
                if result.stdout:
                    print(f"   Output: {result.stdout[:500]}...")
            else:
                print(f"❌ Review failed (exit code {result.returncode})")
                if result.stderr:
                    print(f"   Stderr: {result.stderr}")
                if result.stdout:
                    print(f"   Stdout: {result.stdout}")

        except subprocess.TimeoutExpired:
            print(f"⏰ Review timed out for {repo}#{pr_number}")
        except FileNotFoundError as e:
            print(f"❌ Claude Code CLI not found: {e}")
            print(f"   Tried: {claude_path}")
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")

    def log_message(self, _fmt: str, *_args: Any) -> None:
        """Suppress default HTTP logging."""


def main() -> None:
    """Start the webhook listener server."""
    print("=" * 50)
    print("🤖 AI PR Review - Local Webhook Listener")
    print("=" * 50)
    print(f"\n📡 Listening on http://localhost:{PORT}")
    print("\n📋 Setup instructions:")
    print("   1. Install smee-client: npm install -g smee-client")
    print("   2. Run smee: smee -u $SMEE_URL -t http://localhost:3000")
    print("   3. Configure GitHub webhook to point to your SMEE_URL")
    print("\n⏳ Waiting for webhook events...")
    print("-" * 50)

    server = HTTPServer(("localhost", PORT), WebhookHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
