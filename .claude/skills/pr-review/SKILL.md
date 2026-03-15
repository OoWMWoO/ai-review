---
name: pr-review
description: Review a GitHub pull request for code quality, security, and more
---

# AI PR Review Skill

You are an expert code reviewer. Analyze a GitHub pull request and provide actionable feedback.

## Step 1: Get PR Information

Use the **GitHub MCP** tools to fetch PR data. The user will provide the PR number or you can ask for it.

1. **Get PR metadata** using MCP tool `get_pull_request`:
   - owner: repository owner
   - repo: repository name
   - pull_number: PR number

2. **Get PR diff** using MCP tool `get_pull_request_diff`:
   - owner: repository owner
   - repo: repository name
   - pull_number: PR number

3. **Get changed files** using MCP tool `list_pull_request_files`:
   - owner: repository owner
   - repo: repository name
   - pull_number: PR number

## Step 2: Analyze the Code

Review the PR for these aspects:

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

## Step 3: Post Review Comment

Use the **GitHub MCP** tool `create_issue_comment` to post your review:
- owner: repository owner
- repo: repository name
- issue_number: PR number (PRs are issues in GitHub API)
- body: Your formatted review (see format below)

### Review Comment Format

```markdown
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
*Reviewed by Claude AI via `/pr-review` skill using GitHub MCP*
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

## Usage Examples

User says: `/pr-review OoWMWoO/ai-review#1`
→ Review PR #1 in OoWMWoO/ai-review repo

User says: `/pr-review 123`
→ Ask for repo owner/name, then review PR #123