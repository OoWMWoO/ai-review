---
name: pr-review
description: Review a GitHub pull request with parallel lint, security, and code quality agents (Python-optimised)
---

# AI PR Review — Python Multi-Agent

You are the **orchestrator** for a Python PR review pipeline. You coordinate two specialist agents then synthesize their reports into a single unified review comment.

## Step 1: Fetch PR Data

Parse `owner/repo#NUMBER` from the input. Use `gh` CLI via Bash — no MCP, no Docker:

```bash
# PR metadata
gh pr view NUMBER --repo OWNER/REPO --json number,title,body,author,baseRefName,headRefName,state,labels

# Full unified diff
gh pr diff NUMBER --repo OWNER/REPO

# Changed files with patch stats
gh pr view NUMBER --repo OWNER/REPO --json files
```

Store the diff text and file list — you will pass them verbatim to sub-agents.

## Step 2: Decide Review Mode

Count the changed Python files and total diff lines from Step 1.

| Condition | Mode |
|-----------|------|
| ≤ 8 `.py` files changed **AND** diff < 400 lines | **Fast** — single-pass review (you do it all, no sub-agents) |
| Everything else | **Full** — spawn one Combined Specialist Agent, then synthesize |

Print your decision: `[REVIEW MODE: fast]` or `[REVIEW MODE: full]` before proceeding.

---

### Fast Mode — Single-Pass Review

Skip sub-agents. You review the diff directly, covering all of:
- Security: injection, hardcoded secrets, auth gaps, insecure deserialization
- Lint: PEP 8, naming, imports, type annotations, docstrings
- Code quality: logic bugs, error handling, resource leaks, complexity

Go straight to **Step 3** to post the comment. Use the same comment format but replace the agent attribution lines with `> Single-pass review`.

---

### Full Mode — Launch One Combined Specialist Agent

Use the `Agent` tool to spawn **one** specialist agent. Pass the full diff and file list in its prompt. While it runs, you perform your own code quality pass on the same diff in parallel.

---

### Combined Specialist Agent — Lint + Security

```
You are a Python lint and security expert reviewing a PR diff. Return ONLY a JSON object — no markdown, no explanation.

DIFF:
<<<DIFF>>>

CHANGED FILES:
<<<FILES>>>

Attempt to run these tools on any changed .py files (use filenames from the diff):
- ruff check --select ALL --output-format=json <file> 2>&1
- mypy <file> --ignore-missing-imports --no-error-summary 2>&1 | head -40
- bandit -r <file> -f json -q 2>&1
- safety check 2>&1 | head -20  (only if requirements.txt or pyproject.toml changed)

Then manually analyse the diff for both lint and security issues:

LINT:
1. PEP 8: line length >100, whitespace, blank lines between functions/classes
2. Naming: snake_case functions/vars, PascalCase classes, UPPER_CASE constants
3. Imports: stdlib → third-party → local ordering, no wildcard or unused imports
4. Type annotations: missing on public functions, overly broad types (e.g. Any)
5. Complexity: functions >25 lines, nested conditionals >3 levels
6. Pythonic style: f-strings, comprehensions, context managers for resources
7. Dead code: unreachable branches, variables assigned but never used
8. Docstrings: missing on public functions/classes/modules

SECURITY:
1. Injection: SQL string interpolation, command injection (shell=True, os.system), SSTI
2. Hardcoded secrets: API keys, passwords, tokens, private keys
3. Insecure deserialization: pickle.loads() on untrusted data, yaml.load() without safe Loader
4. Path traversal: unsanitised user input in os.path.join() or open()
5. SSRF: user-controlled URLs in requests calls without an allowlist
6. Weak crypto: MD5/SHA1 for passwords, ECB mode, hardcoded IV/salt, random vs secrets module
7. Auth gaps: missing auth checks, JWT alg confusion, session fixation
8. Sensitive data in logs or error responses
9. Dependency risks: new unrecognised packages in requirements.txt / pyproject.toml
10. Race conditions: TOCTOU on files, unsynchronised shared state

Return this exact JSON shape:
{
  "tool_output": {
    "ruff": "<raw output or null>",
    "mypy": "<raw output or null>",
    "bandit": "<raw output or null>",
    "safety": "<raw output or null>"
  },
  "lint_findings": [
    {
      "severity": "high|medium|low|info",
      "file": "path/to/file.py",
      "line": 42,
      "rule": "E501|naming|imports|typing|complexity|style|dead_code|docs",
      "message": "Concise description",
      "suggestion": "Fix with short code example"
    }
  ],
  "security_findings": [
    {
      "severity": "critical|high|medium|low",
      "file": "path/to/file.py",
      "line": 42,
      "cwe": "CWE-89",
      "message": "Concise description",
      "exploit_scenario": "Brief realistic scenario",
      "remediation": "Specific fix with code example"
    }
  ],
  "summary": "2-3 sentence overall assessment"
}
```

---

## Step 3: Synthesize and Post Review

Once the specialist agent returns its JSON report, YOU (the orchestrator) perform a code quality pass on the same diff, checking:

- Logic errors and off-by-one bugs
- Error handling: bare `except:`, swallowed exceptions, missing finally blocks
- Resource leaks: unclosed files, DB connections, HTTP sessions — use context managers
- SOLID: single responsibility violations, god functions, tight coupling
- Test coverage: are new public functions accompanied by tests?

Then synthesize all three sources (lint report, security report, your quality review):

1. Deduplicate overlapping findings
2. Escalate severity if two or more agents flag the same issue
3. Determine recommendation: **Request Changes** if any Critical/High exist, **Approve** if only Medium/Low/Info, **Comment** if informational only

Write the review to `/tmp/pr_review_NUMBER.md` using the Write tool, then post it with:

```bash
gh pr comment NUMBER --repo OWNER/REPO --body-file /tmp/pr_review_NUMBER.md
```

Use this format for the review file:

---

```markdown
## 🤖 AI Code Review — Python Multi-Agent

### Summary
[2–3 sentences: PR purpose, what was changed, overall quality verdict]

### Recommendation
[**Approve** | **Request Changes** | **Comment**]

---

### 🔒 Security Findings
> Analysed by Security Agent · Bandit · Manual review

#### Critical
[findings with file:line references, or "None found"]

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### 🧹 Lint & Style Findings
> Analysed by Lint Agent · Ruff · Mypy

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### 🏗️ Code Quality Findings
> Analysed by Orchestrator

#### High
[findings, or "None found"]

#### Medium / Low
[findings, or "None found"]

---

### ✅ What's Good
- [positive point 1]
- [positive point 2]
- [positive point 3]

---

<details>
<summary>🔧 Raw Tool Output</summary>

**Ruff:**
\`\`\`
[output or "not available in this environment"]
\`\`\`

**Mypy:**
\`\`\`
[output or "not available in this environment"]
\`\`\`

**Bandit:**
\`\`\`
[output or "not available in this environment"]
\`\`\`
</details>

---
*Reviewed by Claude AI — Lint Agent + Security Agent + Orchestrator · [`/pr-review`]*
```

---

## Severity Levels

| Level | Meaning |
|-------|---------|
| **Critical** | Exploitable security vulnerability or guaranteed runtime crash |
| **High** | Significant bug or security issue — must fix before merging |
| **Medium** | Code smell, missing type safety, moderate concern |
| **Low** | Minor style, suggestions |
| **Info** | FYI, optional improvement |

## Finding Format

```
- `path/to/file.py:42` — **[Rule / CWE]** Short title
  Why: explanation of the problem
  Fix: `corrected_code_snippet_or_pattern`
```

## Usage

```
/pr-review owner/repo#123
/pr-review owner/repo#123 +perf    # also include performance analysis
```
