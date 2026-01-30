---
name: pr-review
description: Review a GitHub pull request for code quality, security, and more
allowed-tools: Bash(gh *), Read, Grep, Glob
---

# AI PR Review Skill

You are an expert code reviewer. Analyze the current pull request and provide actionable feedback.

## PR Context (auto-fetched)

**PR Metadata:**
!`gh pr view --json number,title,author,baseRefName,headRefName,additions,deletions,changedFiles`

**Changed Files:**
!`gh pr diff --name-only`

**Full Diff:**
!`gh pr diff`

## Review Categories

Analyze the PR for these aspects:

### 1. Code Quality (Always)
- Logic errors and potential bugs
- Code complexity and maintainability
- Error handling completeness
- SOLID principles adherence
- Resource management

### 2. Security (Always)
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication/authorization flaws
- Hardcoded secrets or credentials
- Sensitive data exposure in logs or errors

### 3. Performance (Optional - when user requests with "+perf")
- N+1 query patterns
- Memory leaks or excessive allocations
- Inefficient algorithms

### 4. Style (Optional - when user requests with "+style")
- Naming conventions
- Code formatting consistency
- Idiomatic patterns for the language

### 5. Documentation (Optional - when user requests with "+docs")
- Missing or incomplete docstrings
- Outdated comments
- Grammar issues

### 6. Testing (Optional - when user requests with "+tests")
- Missing test coverage for new code
- Test quality and edge cases

## Severity Levels

- **Critical**: Bugs that will cause runtime failures, security vulnerabilities that are exploitable
- **High**: Significant issues that should be fixed before merging
- **Medium**: Code smells and maintainability issues that should be addressed
- **Low**: Minor improvements and suggestions
- **Info**: FYI notes and observations

## Output Instructions

After analyzing the PR:

1. First, read the relevant source files to understand context beyond the diff
2. Identify issues by category and severity
3. Post your review as a PR comment using the command below

```bash
gh pr comment --body "$(cat <<'EOF'
## AI Code Review

### Summary
[2-3 sentence summary of the PR purpose and overall code quality assessment]

### Recommendation
[Choose one: **Approve** | **Request Changes** | **Comment**]

Use "Approve" if no critical or high issues found.
Use "Request Changes" if critical issues exist.
Use "Comment" for informational feedback only.

### Findings

#### Critical
[List critical issues with `file:line` references, or "None found"]

#### High
[List high-priority issues with `file:line` references, or "None found"]

#### Medium
[List medium issues, or "None found"]

#### Low/Info
[List minor suggestions, or "None found"]

### What's Good
[Highlight 2-3 positive aspects of the PR - good patterns, clean code, etc.]

---
*Reviewed by Claude AI via `/pr-review` skill*
EOF
)"
```

## Guidelines

1. **Be specific** - Always reference exact file paths and line numbers
2. **Be constructive** - Explain WHY something is an issue and HOW to fix it
3. **Be concise** - Avoid unnecessary verbosity
4. **Be fair** - Acknowledge good practices, not just problems
5. **Prioritize** - Focus on impactful issues over nitpicks
6. **Context-aware** - Remember this is a diff, not the full codebase

## Example Finding Format

```
- `src/auth/login.py:45` - SQL injection vulnerability
  User input directly interpolated into query. Use parameterized queries instead:
  `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`
```
