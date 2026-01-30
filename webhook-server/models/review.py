"""Review data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ReviewLevel(str, Enum):
    """Review depth levels."""

    LIGHT = "light"
    DEEP = "deep"
    AUTO = "auto"


class PRInfo(BaseModel):
    """Pull request information."""

    repo_owner: str
    repo_name: str
    pr_number: int
    pr_title: str
    pr_url: str
    author: str
    base_branch: str
    head_branch: str
    diff_content: str
    files_changed: list[str] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0


class ReviewFinding(BaseModel):
    """A single review finding."""

    category: str  # code-quality, security, test-coverage, style, breaking-changes
    severity: str  # critical, high, medium, low, info
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    title: str
    description: str
    suggestion: Optional[str] = None


class ReviewRequest(BaseModel):
    """Review request from webhook."""

    pr_info: PRInfo
    review_level: ReviewLevel = ReviewLevel.AUTO
    triggered_by: str  # GitHub username who triggered the review
    comment_id: int  # The comment ID that triggered the review


class ReviewResult(BaseModel):
    """Complete review result."""

    request_id: str
    pr_info: PRInfo
    review_level: ReviewLevel
    triggered_by: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    summary: str
    recommendation: str  # approve, request-changes, comment
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    # Scores (0-100)
    code_quality_score: Optional[int] = None
    security_score: Optional[int] = None
    test_coverage_score: Optional[int] = None
    style_score: Optional[int] = None

    # Metadata
    model_used: str = ""
    tokens_used: int = 0