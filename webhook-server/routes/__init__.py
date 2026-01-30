"""Route blueprints for the webhook server."""

from .github_webhook import github_bp

__all__ = ["github_bp"]