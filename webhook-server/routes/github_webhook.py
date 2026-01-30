"""GitHub webhook endpoint."""

import hashlib
import hmac
import logging
import re
from typing import Optional

from sanic import Blueprint, Request, json
from sanic.exceptions import Forbidden, BadRequest

from config import get_settings

logger = logging.getLogger(__name__)

github_bp = Blueprint("github", url_prefix="/webhook")

# Trigger pattern: "hey ai review" optionally followed by level
TRIGGER_PATTERN = re.compile(
    r"hey\s+ai\s+review(?:\s+(light|deep))?",
    re.IGNORECASE
)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature.startswith("sha256="):
        return False

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def parse_trigger_comment(comment_body: str) -> Optional[dict]:
    """
    Parse comment for trigger phrase.
    Returns dict with review_level if triggered, None otherwise.
    """
    match = TRIGGER_PATTERN.search(comment_body)
    if not match:
        return None

    level = match.group(1)
    return {
        "review_level": level.lower() if level else "auto"
    }


@github_bp.post("/github")
async def handle_github_webhook(request: Request):
    """Handle incoming GitHub webhook events."""
    settings = get_settings()

    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(request.body, signature, settings.github_webhook_secret):
        logger.warning("Invalid webhook signature")
        raise Forbidden("Invalid signature")

    # Get event type
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    logger.info(f"Received GitHub event: {event_type} (delivery: {delivery_id})")

    # Only process issue_comment events (PR comments are also issue_comments)
    if event_type != "issue_comment":
        return json({"status": "ignored", "reason": f"Event type '{event_type}' not handled"})

    payload = request.json
    action = payload.get("action", "")

    # Only process newly created comments
    if action != "created":
        return json({"status": "ignored", "reason": f"Action '{action}' not handled"})

    # Check if this is a PR comment (not a regular issue comment)
    issue = payload.get("issue", {})
    if "pull_request" not in issue:
        return json({"status": "ignored", "reason": "Not a pull request comment"})

    # Check for trigger phrase
    comment = payload.get("comment", {})
    comment_body = comment.get("body", "")
    trigger = parse_trigger_comment(comment_body)

    if not trigger:
        return json({"status": "ignored", "reason": "No trigger phrase found"})

    # Extract PR information
    repo = payload.get("repository", {})
    pr_number = issue.get("number")
    repo_owner = repo.get("owner", {}).get("login")
    repo_name = repo.get("name")
    triggered_by = comment.get("user", {}).get("login")
    comment_id = comment.get("id")

    logger.info(
        f"Review triggered by {triggered_by} on {repo_owner}/{repo_name}#{pr_number} "
        f"(level: {trigger['review_level']})"
    )

    # Queue the review (will be implemented in review_service)
    # For now, acknowledge the request
    review_request = {
        "repo_owner": repo_owner,
        "repo_name": repo_name,
        "pr_number": pr_number,
        "review_level": trigger["review_level"],
        "triggered_by": triggered_by,
        "comment_id": comment_id,
        "delivery_id": delivery_id,
    }

    # Import here to avoid circular imports
    from services.review_service import queue_review

    await queue_review(request.app, review_request)

    return json({
        "status": "queued",
        "pr": f"{repo_owner}/{repo_name}#{pr_number}",
        "review_level": trigger["review_level"],
        "triggered_by": triggered_by,
    })


@github_bp.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    return json({"status": "healthy"})