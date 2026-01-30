"""GitHub service for fetching PR data and posting comments."""

import logging
import subprocess
from typing import Optional

import httpx

from models.review import PRInfo

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for GitHub API operations using gh CLI and REST API."""

    def __init__(self, token: str):
        self.token = token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_pr_info(
        self, repo_owner: str, repo_name: str, pr_number: int
    ) -> PRInfo:
        """Fetch PR information including diff content."""
        async with httpx.AsyncClient() as client:
            # Get PR metadata
            pr_url = f"{self.api_base}/repos/{repo_owner}/{repo_name}/pulls/{pr_number}"
            pr_response = await client.get(pr_url, headers=self.headers)
            pr_response.raise_for_status()
            pr_data = pr_response.json()

            # Get PR diff
            diff_headers = {**self.headers, "Accept": "application/vnd.github.diff"}
            diff_response = await client.get(pr_url, headers=diff_headers)
            diff_response.raise_for_status()
            diff_content = diff_response.text

            # Get list of changed files
            files_url = f"{pr_url}/files"
            files_response = await client.get(files_url, headers=self.headers)
            files_response.raise_for_status()
            files_data = files_response.json()

            files_changed = [f["filename"] for f in files_data]
            additions = sum(f.get("additions", 0) for f in files_data)
            deletions = sum(f.get("deletions", 0) for f in files_data)

            return PRInfo(
                repo_owner=repo_owner,
                repo_name=repo_name,
                pr_number=pr_number,
                pr_title=pr_data["title"],
                pr_url=pr_data["html_url"],
                author=pr_data["user"]["login"],
                base_branch=pr_data["base"]["ref"],
                head_branch=pr_data["head"]["ref"],
                diff_content=diff_content,
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
            )

    async def post_pr_comment(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        comment_body: str,
    ) -> dict:
        """Post a comment on a PR."""
        async with httpx.AsyncClient() as client:
            # PR comments go to the issues endpoint
            url = f"{self.api_base}/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"
            response = await client.post(
                url,
                headers=self.headers,
                json={"body": comment_body},
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Posted comment to {repo_owner}/{repo_name}#{pr_number}")
            return result

    async def add_reaction_to_comment(
        self,
        repo_owner: str,
        repo_name: str,
        comment_id: int,
        reaction: str = "eyes",
    ) -> None:
        """Add a reaction to a comment to acknowledge receipt."""
        async with httpx.AsyncClient() as client:
            url = f"{self.api_base}/repos/{repo_owner}/{repo_name}/issues/comments/{comment_id}/reactions"
            response = await client.post(
                url,
                headers={**self.headers, "Accept": "application/vnd.github+json"},
                json={"content": reaction},
            )
            if response.status_code == 201:
                logger.info(f"Added '{reaction}' reaction to comment {comment_id}")
            else:
                logger.warning(f"Failed to add reaction: {response.status_code}")

    def get_pr_diff_via_cli(
        self, repo_owner: str, repo_name: str, pr_number: int
    ) -> Optional[str]:
        """
        Fallback: Get PR diff using gh CLI.
        Useful when API rate limits are hit.
        """
        try:
            result = subprocess.run(
                ["gh", "pr", "diff", str(pr_number), "-R", f"{repo_owner}/{repo_name}"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return result.stdout
            logger.error(f"gh CLI error: {result.stderr}")
            return None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"gh CLI failed: {e}")
            return None